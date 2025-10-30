"""
Point-E with Proper Mesh Reconstruction
Uses volumetric reconstruction instead of convex hull
"""
import torch
import numpy as np
from point_e.diffusion.configs import DIFFUSION_CONFIGS, diffusion_from_config
from point_e.diffusion.sampler import PointCloudSampler
from point_e.models.configs import MODEL_CONFIGS, model_from_config
import trimesh
from scipy.interpolate import griddata
from skimage import measure

print("="*60)
print("POINT-E WITH VOLUMETRIC RECONSTRUCTION")
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

    # Create sampler with HIGH guidance
    sampler = PointCloudSampler(
        device=device,
        models=[base_model, upsampler_model],
        diffusions=[base_diffusion, upsampler_diffusion],
        num_points=[1024, 4096 - 1024],
        aux_channels=['R', 'G', 'B'],
        guidance_scale=[10.0, 10.0],  # VERY high guidance
    )
    print("[SUCCESS] Sampler created with guidance=10.0")

    # Generate from text prompt
    print("\n" + "="*60)
    print("GENERATING HIGH-QUALITY POINT CLOUD")
    print("="*60)

    prompt = "a detailed modern two-story residential house with windows, door, sloped roof, and chimney"
    print(f"\nPrompt: '{prompt}'")
    print("Generating with maximum guidance...")

    # Generate samples
    samples = None
    for x in sampler.sample_batch_progressive(batch_size=1, model_kwargs=dict(texts=[prompt])):
        samples = x

    print("\n[SUCCESS] Point cloud generated!")

    # Extract point cloud
    pc = sampler.output_to_point_clouds(samples)[0]
    coords = pc.coords
    colors = np.stack([pc.channels['R'], pc.channels['G'], pc.channels['B']], axis=-1)

    print(f"Point cloud size: {len(coords):,} points")

    # Save point cloud
    pc_output = "D:/Work/Uni/FYP/architext/outputs/point_e_raw_points.ply"
    pc_mesh = trimesh.points.PointCloud(coords, colors=(colors * 255).astype(np.uint8))
    pc_mesh.export(pc_output)
    print(f"[SUCCESS] Raw point cloud saved: {pc_output}")

    print("\n" + "-"*60)
    print("METHOD 1: Volumetric Reconstruction (Marching Cubes)")
    print("-"*60)

    try:
        # Create 3D grid
        resolution = 64  # Grid resolution

        # Normalize coordinates to [0, 1]
        coords_min = coords.min(axis=0)
        coords_max = coords.max(axis=0)
        coords_norm = (coords - coords_min) / (coords_max - coords_min + 1e-8)

        # Create volume grid
        print(f"Creating {resolution}x{resolution}x{resolution} volume grid...")
        x = np.linspace(0, 1, resolution)
        y = np.linspace(0, 1, resolution)
        z = np.linspace(0, 1, resolution)
        grid_x, grid_y, grid_z = np.meshgrid(x, y, z, indexing='ij')

        # Create occupancy field using distance to nearest point
        from scipy.spatial import cKDTree
        tree = cKDTree(coords_norm)

        # Flatten grid for query
        grid_points = np.stack([grid_x.ravel(), grid_y.ravel(), grid_z.ravel()], axis=1)

        # Query distances
        print("Computing occupancy field...")
        distances, _ = tree.query(grid_points, k=1)

        # Create occupancy grid (inside = distance < threshold)
        threshold = 0.05  # Adjust this for mesh tightness
        occupancy = (distances < threshold).astype(float)
        occupancy = occupancy.reshape((resolution, resolution, resolution))

        # Apply marching cubes
        print("Applying Marching Cubes algorithm...")
        verts, faces, normals, values = measure.marching_cubes(occupancy, level=0.5)

        # Scale back to original coordinates
        verts = verts / resolution  # Back to [0, 1]
        verts = verts * (coords_max - coords_min) + coords_min

        # Create mesh
        mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_normals=normals)

        # Map colors from point cloud
        print("Mapping colors to mesh vertices...")
        tree_orig = cKDTree(coords)
        _, indices = tree_orig.query(mesh.vertices, k=5)
        neighbor_colors = colors[indices]
        vertex_colors = neighbor_colors.mean(axis=1)
        mesh.visual.vertex_colors = (vertex_colors * 255).astype(np.uint8)

        # Clean mesh
        mesh.remove_duplicate_faces()
        mesh.remove_unreferenced_vertices()

        print(f"[SUCCESS] Volumetric mesh created:")
        print(f"  Vertices: {len(mesh.vertices):,}")
        print(f"  Faces: {len(mesh.faces):,}")

        # Save mesh
        output_path = "D:/Work/Uni/FYP/architext/outputs/point_e_volumetric.ply"
        mesh.export(output_path)
        print(f"[SUCCESS] Saved to: {output_path}")

        # Also save OBJ
        obj_path = "D:/Work/Uni/FYP/architext/outputs/point_e_volumetric.obj"
        mesh.export(obj_path)
        print(f"[SUCCESS] Saved OBJ: {obj_path}")

    except Exception as e:
        print(f"[ERROR] Volumetric reconstruction failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "-"*60)
    print("METHOD 2: High-Quality Subdivided Hull (Fallback)")
    print("-"*60)

    try:
        # Create convex hull
        mesh2 = trimesh.convex.convex_hull(coords)

        # Subdivide multiple times
        for i in range(3):
            mesh2 = mesh2.subdivide()
            print(f"  Subdivision {i+1}: {len(mesh2.vertices):,} vertices")

        # Map colors
        tree = cKDTree(coords)
        _, indices = tree.query(mesh2.vertices, k=5)
        neighbor_colors = colors[indices]
        vertex_colors = neighbor_colors.mean(axis=1)
        mesh2.visual.vertex_colors = (vertex_colors * 255).astype(np.uint8)

        print(f"[SUCCESS] Subdivided hull created:")
        print(f"  Vertices: {len(mesh2.vertices):,}")
        print(f"  Faces: {len(mesh2.faces):,}")

        # Save
        output_path2 = "D:/Work/Uni/FYP/architext/outputs/point_e_subdivided.ply"
        mesh2.export(output_path2)
        print(f"[SUCCESS] Saved to: {output_path2}")

        obj_path2 = "D:/Work/Uni/FYP/architext/outputs/point_e_subdivided.obj"
        mesh2.export(obj_path2)
        print(f"[SUCCESS] Saved OBJ: {obj_path2}")

    except Exception as e:
        print(f"[ERROR] Subdivision failed: {e}")

    print("\n" + "="*60)
    print("RECONSTRUCTION COMPLETE!")
    print("="*60)
    print("\nGenerated 3 versions:")
    print("1. point_e_raw_points.ply - Raw 4,096 point cloud")
    print("2. point_e_volumetric.ply - Volumetric reconstruction (BEST)")
    print("3. point_e_subdivided.ply - Subdivided convex hull (fallback)")
    print("\nTest in Blender:")
    print("File -> Import -> Stanford (.ply) or Wavefront (.obj)")
    print("\nThe volumetric version should show a solid 3D house!")

except Exception as e:
    print(f"\n[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
