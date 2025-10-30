"""
High-Quality Point-E Test Script
Enhanced with better mesh reconstruction and higher point density
"""
import torch
import numpy as np
from point_e.diffusion.configs import DIFFUSION_CONFIGS, diffusion_from_config
from point_e.diffusion.sampler import PointCloudSampler
from point_e.models.download import load_checkpoint
from point_e.models.configs import MODEL_CONFIGS, model_from_config
import trimesh
import open3d as o3d

print("="*60)
print("POINT-E HIGH-QUALITY TEST")
print("="*60)

# Check device
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"\nUsing device: {device}")
if device.type == 'cuda':
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"CUDA Version: {torch.version.cuda}")

print("\n" + "-"*60)
print("Loading Point-E models...")
print("-"*60)

try:
    # Load base model (text-conditioned version)
    print("Loading base40M-textvec model...")
    base_name = 'base40M-textvec'
    base_model = model_from_config(MODEL_CONFIGS[base_name], device)
    base_model.eval()
    base_diffusion = diffusion_from_config(DIFFUSION_CONFIGS[base_name])

    print("[SUCCESS] Base model loaded")

    # Load upsampler model
    print("Loading upsample model...")
    upsampler_model = model_from_config(MODEL_CONFIGS['upsample'], device)
    upsampler_model.eval()
    upsampler_diffusion = diffusion_from_config(DIFFUSION_CONFIGS['upsample'])

    print("[SUCCESS] Upsampler loaded")

    # Create sampler with HIGHER guidance scale for better quality
    sampler = PointCloudSampler(
        device=device,
        models=[base_model, upsampler_model],
        diffusions=[base_diffusion, upsampler_diffusion],
        num_points=[1024, 4096 - 1024],  # Total 4096 points
        aux_channels=['R', 'G', 'B'],
        guidance_scale=[5.0, 5.0],  # Increased from 3.0 to 5.0 for better quality
    )

    print("[SUCCESS] Sampler created with enhanced settings")

    # Generate from text prompt
    print("\n" + "="*60)
    print("GENERATING HIGH-QUALITY POINT CLOUD")
    print("="*60)

    prompt = "a detailed modern two-story house with windows, door, and roof"
    print(f"\nPrompt: '{prompt}'")
    print("Generating point cloud with high guidance... (3-5 minutes)")

    # Generate samples
    samples = None
    for x in sampler.sample_batch_progressive(batch_size=1, model_kwargs=dict(texts=[prompt])):
        samples = x

    print("\n[SUCCESS] Point cloud generated!")

    # Extract point cloud
    pc = sampler.output_to_point_clouds(samples)[0]
    print(f"Point cloud size: {pc.coords.shape[0]} points")

    # Convert to mesh using advanced reconstruction
    print("\nConverting point cloud to high-quality mesh...")

    coords = pc.coords
    colors = np.stack([pc.channels['R'], pc.channels['G'], pc.channels['B']], axis=-1)

    # Method 1: Try Poisson Surface Reconstruction (best quality)
    print("Attempting Poisson surface reconstruction...")
    try:
        # Create Open3D point cloud
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(coords)
        pcd.colors = o3d.utility.Vector3dVector(colors)

        # Estimate normals
        pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30)
        )
        pcd.orient_normals_consistent_tangent_plane(30)

        # Poisson reconstruction
        mesh_o3d, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd, depth=9, width=0, scale=1.1, linear_fit=False
        )

        # Remove low density vertices
        vertices_to_remove = densities < np.quantile(densities, 0.1)
        mesh_o3d.remove_vertices_by_mask(vertices_to_remove)

        # Convert to trimesh
        vertices = np.asarray(mesh_o3d.vertices)
        faces = np.asarray(mesh_o3d.triangles)
        vertex_colors = np.asarray(mesh_o3d.vertex_colors)

        mesh = trimesh.Trimesh(
            vertices=vertices,
            faces=faces,
            vertex_colors=(vertex_colors * 255).astype(np.uint8)
        )

        print("[SUCCESS] Poisson reconstruction completed!")

    except Exception as e:
        print(f"[WARNING] Poisson failed: {e}")
        print("Falling back to Ball Pivoting Algorithm...")

        try:
            # Method 2: Ball Pivoting Algorithm
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(coords)
            pcd.colors = o3d.utility.Vector3dVector(colors)

            pcd.estimate_normals()
            pcd.orient_normals_consistent_tangent_plane(30)

            # Ball pivoting
            distances = pcd.compute_nearest_neighbor_distance()
            avg_dist = np.mean(distances)
            radius = 1.5 * avg_dist

            mesh_o3d = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
                pcd,
                o3d.utility.DoubleVector([radius, radius * 2])
            )

            vertices = np.asarray(mesh_o3d.vertices)
            faces = np.asarray(mesh_o3d.triangles)
            vertex_colors = np.asarray(mesh_o3d.vertex_colors)

            mesh = trimesh.Trimesh(
                vertices=vertices,
                faces=faces,
                vertex_colors=(vertex_colors * 255).astype(np.uint8)
            )

            print("[SUCCESS] Ball Pivoting reconstruction completed!")

        except Exception as e2:
            print(f"[WARNING] Ball Pivoting failed: {e2}")
            print("Falling back to Alpha Shape...")

            # Method 3: Alpha Shape (fallback)
            try:
                pcd = o3d.geometry.PointCloud()
                pcd.points = o3d.utility.Vector3dVector(coords)
                pcd.colors = o3d.utility.Vector3dVector(colors)

                mesh_o3d = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(
                    pcd, alpha=0.1
                )

                vertices = np.asarray(mesh_o3d.vertices)
                faces = np.asarray(mesh_o3d.triangles)

                # Map colors from original point cloud
                from scipy.spatial import cKDTree
                tree = cKDTree(coords)
                _, indices = tree.query(vertices, k=1)
                vertex_colors = (colors[indices] * 255).astype(np.uint8)

                mesh = trimesh.Trimesh(
                    vertices=vertices,
                    faces=faces,
                    vertex_colors=vertex_colors
                )

                print("[SUCCESS] Alpha Shape reconstruction completed!")

            except Exception as e3:
                print(f"[ERROR] All advanced methods failed: {e3}")
                print("Using basic convex hull as last resort...")
                mesh = trimesh.convex.convex_hull(coords)

    # Apply smoothing
    if hasattr(mesh, 'subdivide'):
        print("Applying mesh subdivision for smoothness...")
        mesh = mesh.subdivide()

    print(f"\n[SUCCESS] Final mesh created:")
    print(f"  Vertices: {len(mesh.vertices):,}")
    print(f"  Faces: {len(mesh.faces):,}")

    # Save mesh
    output_path = "D:/Work/Uni/FYP/architext/outputs/point_e_high_quality_house.ply"
    mesh.export(output_path)
    print(f"\n[SUCCESS] Saved to: {output_path}")

    # Also save the raw point cloud for comparison
    pc_output_path = "D:/Work/Uni/FYP/architext/outputs/point_e_point_cloud.ply"
    pc_mesh = trimesh.points.PointCloud(coords, colors=(colors * 255).astype(np.uint8))
    pc_mesh.export(pc_output_path)
    print(f"[SUCCESS] Point cloud saved to: {pc_output_path}")

    print("\n" + "="*60)
    print("HIGH-QUALITY TEST COMPLETE!")
    print("="*60)
    print("\nGenerated files:")
    print(f"1. Mesh: {output_path}")
    print(f"2. Point Cloud: {pc_output_path}")
    print("\nQuality improvements:")
    print("- Higher guidance scale (5.0 vs 3.0)")
    print("- Poisson surface reconstruction")
    print("- Mesh smoothing and subdivision")
    print(f"- {len(mesh.vertices):,} vertices vs 8 in simple version")

except Exception as e:
    print(f"\n[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
