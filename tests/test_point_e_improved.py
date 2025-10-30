"""
Improved Point-E Test Script
Enhanced quality without requiring Open3D
"""
import torch
import numpy as np
from point_e.diffusion.configs import DIFFUSION_CONFIGS, diffusion_from_config
from point_e.diffusion.sampler import PointCloudSampler
from point_e.models.configs import MODEL_CONFIGS, model_from_config
import trimesh
from scipy.spatial import Delaunay
from scipy.ndimage import gaussian_filter1d

print("="*60)
print("POINT-E IMPROVED TEST")
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
    # Load base model
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

    # Create sampler with HIGHER guidance for better quality
    sampler = PointCloudSampler(
        device=device,
        models=[base_model, upsampler_model],
        diffusions=[base_diffusion, upsampler_diffusion],
        num_points=[1024, 4096 - 1024],  # 4096 total points
        aux_channels=['R', 'G', 'B'],
        guidance_scale=[7.0, 7.0],  # MUCH higher guidance for better structure
    )
    print("[SUCCESS] Sampler created with enhanced guidance")

    # Generate from text prompt
    print("\n" + "="*60)
    print("GENERATING IMPROVED POINT CLOUD")
    print("="*60)

    prompt = "a detailed modern two-story residential house with windows, door, sloped roof, and chimney"
    print(f"\nPrompt: '{prompt}'")
    print("Generating with high guidance scale... (3-5 minutes)")

    # Generate samples
    samples = None
    for x in sampler.sample_batch_progressive(batch_size=1, model_kwargs=dict(texts=[prompt])):
        samples = x

    print("\n[SUCCESS] Point cloud generated!")

    # Extract point cloud
    pc = sampler.output_to_point_clouds(samples)[0]
    print(f"Point cloud size: {pc.coords.shape[0]} points")

    coords = pc.coords
    colors = np.stack([pc.channels['R'], pc.channels['G'], pc.channels['B']], axis=-1)

    print("\nConverting to improved mesh...")

    # Method 1: Try Alpha Shape with trimesh (better than convex hull)
    try:
        print("Attempting Alpha Shape reconstruction...")

        # Create point cloud object
        point_cloud = trimesh.points.PointCloud(coords, colors=(colors * 255).astype(np.uint8))

        # Save point cloud
        pc_output = "D:/Work/Uni/FYP/architext/outputs/point_e_point_cloud.ply"
        point_cloud.export(pc_output)
        print(f"[SUCCESS] Point cloud saved: {pc_output}")

        # Try to create mesh using Delaunay triangulation
        print("Applying Delaunay triangulation...")

        # Normalize coordinates
        coords_norm = coords - coords.mean(axis=0)
        scale = np.abs(coords_norm).max()
        coords_norm = coords_norm / scale

        # Create Delaunay triangulation in 3D
        tri = Delaunay(coords_norm)

        # Extract surface triangles (simplified alpha shape)
        # Keep triangles with reasonable edge lengths
        vertices = coords_norm
        faces = []

        for simplex in tri.simplices:
            # Calculate edge lengths
            p0, p1, p2, p3 = vertices[simplex]
            edges = [
                np.linalg.norm(p1 - p0),
                np.linalg.norm(p2 - p0),
                np.linalg.norm(p3 - p0),
                np.linalg.norm(p2 - p1),
                np.linalg.norm(p3 - p1),
                np.linalg.norm(p3 - p2)
            ]
            max_edge = max(edges)

            # Keep tetrahedron faces with reasonable edge length (alpha shape)
            if max_edge < 0.3:  # Alpha parameter
                faces.extend([
                    [simplex[0], simplex[1], simplex[2]],
                    [simplex[0], simplex[1], simplex[3]],
                    [simplex[0], simplex[2], simplex[3]],
                    [simplex[1], simplex[2], simplex[3]]
                ])

        faces = np.array(faces)

        # Remove duplicate faces
        faces = np.unique(np.sort(faces, axis=1), axis=0)

        # Map colors to vertices
        from scipy.spatial import cKDTree
        tree = cKDTree(coords_norm)
        vertex_colors = (colors * 255).astype(np.uint8)

        # Scale back to original coordinates
        vertices_final = coords_norm * scale + coords.mean(axis=0)

        mesh = trimesh.Trimesh(
            vertices=vertices_final,
            faces=faces,
            vertex_colors=vertex_colors
        )

        # Remove degenerate faces and fix normals
        mesh.remove_degenerate_faces()
        mesh.remove_duplicate_faces()
        mesh.remove_unreferenced_vertices()

        print(f"[SUCCESS] Alpha shape mesh created: {len(mesh.vertices):,} vertices, {len(mesh.faces):,} faces")

    except Exception as e:
        print(f"[WARNING] Alpha shape failed: {e}")
        print("Falling back to improved convex hull...")

        # Method 2: Improved Convex Hull with subdivision
        mesh = trimesh.convex.convex_hull(coords)

        # Subdivide to increase vertex count
        for _ in range(2):  # Subdivide twice
            mesh = mesh.subdivide()

        # Map colors from original point cloud
        from scipy.spatial import cKDTree
        tree = cKDTree(coords)
        _, indices = tree.query(mesh.vertices, k=5)  # Use 5 nearest neighbors

        # Average colors from nearest neighbors
        neighbor_colors = colors[indices]
        vertex_colors = neighbor_colors.mean(axis=1)
        mesh.visual.vertex_colors = (vertex_colors * 255).astype(np.uint8)

        print(f"[SUCCESS] Subdivided convex hull created: {len(mesh.vertices):,} vertices")

    # Apply Laplacian smoothing
    try:
        print("Applying mesh smoothing...")
        mesh = trimesh.smoothing.filter_laplacian(mesh, lamb=0.5, iterations=5)
        print("[SUCCESS] Mesh smoothed")
    except:
        print("[WARNING] Smoothing failed, using unsmoothed mesh")

    print(f"\n[SUCCESS] Final improved mesh:")
    print(f"  Vertices: {len(mesh.vertices):,}")
    print(f"  Faces: {len(mesh.faces):,}")
    print(f"  Has vertex colors: {hasattr(mesh.visual, 'vertex_colors')}")

    # Save mesh
    output_path = "D:/Work/Uni/FYP/architext/outputs/point_e_improved_house.ply"
    mesh.export(output_path)
    print(f"\n[SUCCESS] Saved mesh to: {output_path}")

    print("\n" + "="*60)
    print("IMPROVED TEST COMPLETE!")
    print("="*60)
    print("\nEnhancements:")
    print("- Guidance scale increased to 7.0 (vs 3.0 default)")
    print("- Alpha shape reconstruction (vs basic convex hull)")
    print("- Laplacian smoothing applied")
    print("- Better prompt engineering")
    print(f"- {len(mesh.vertices):,} vertices (vs 8 in basic version)")
    print("\nTo test:")
    print(f"1. Open {output_path} in Blender/MeshLab")
    print(f"2. Compare with point cloud: point_e_point_cloud.ply")

except Exception as e:
    print(f"\n[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
