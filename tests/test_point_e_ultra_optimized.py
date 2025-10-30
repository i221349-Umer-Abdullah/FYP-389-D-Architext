"""
Ultra-Optimized Point-E for House Generation
Uses maximum settings for best accuracy
"""
import torch
import numpy as np
from point_e.diffusion.configs import DIFFUSION_CONFIGS, diffusion_from_config
from point_e.diffusion.sampler import PointCloudSampler
from point_e.models.configs import MODEL_CONFIGS, model_from_config
import trimesh
from skimage import measure
from scipy.spatial import cKDTree

print("="*60)
print("ULTRA-OPTIMIZED POINT-E FOR HOUSES")
print("="*60)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"\nDevice: {device}")
if device.type == 'cuda':
    print(f"GPU: {torch.cuda.get_device_name(0)}")

print("\n" + "-"*60)
print("Loading models...")
print("-"*60)

# Load models
base_model = model_from_config(MODEL_CONFIGS['base40M-textvec'], device)
base_model.eval()
base_diffusion = diffusion_from_config(DIFFUSION_CONFIGS['base40M-textvec'])
print("[SUCCESS] Base model loaded")

upsampler_model = model_from_config(MODEL_CONFIGS['upsample'], device)
upsampler_model.eval()
upsampler_diffusion = diffusion_from_config(DIFFUSION_CONFIGS['upsample'])
print("[SUCCESS] Upsampler loaded")

# ULTRA HIGH GUIDANCE for maximum structure
sampler = PointCloudSampler(
    device=device,
    models=[base_model, upsampler_model],
    diffusions=[base_diffusion, upsampler_diffusion],
    num_points=[1024, 4096 - 1024],
    aux_channels=['R', 'G', 'B'],
    guidance_scale=[15.0, 15.0],  # MAXIMUM guidance
)
print("[SUCCESS] Sampler created with ULTRA-HIGH guidance (15.0)")

# OPTIMIZED PROMPTS - Multiple variations
prompts = [
    "a simple rectangular house building with a triangular roof",
    "a box-shaped house with a pointed roof on top",
    "a cubic residential building with a pyramid roof",
]

print("\n" + "="*60)
print("GENERATING OPTIMIZED HOUSES")
print("="*60)

for idx, prompt in enumerate(prompts, 1):
    print(f"\n[{idx}/{len(prompts)}] Prompt: '{prompt}'")
    print("Generating with ultra-high guidance...")

    try:
        # Generate
        samples = None
        for x in sampler.sample_batch_progressive(batch_size=1, model_kwargs=dict(texts=[prompt])):
            samples = x

        print("[SUCCESS] Point cloud generated!")

        # Extract
        pc = sampler.output_to_point_clouds(samples)[0]
        coords = pc.coords
        colors = np.stack([pc.channels['R'], pc.channels['G'], pc.channels['B']], axis=-1)

        # Save raw point cloud
        pc_path = f"D:/Work/Uni/FYP/architext/outputs/optimized_pc_{idx}.ply"
        pc_mesh = trimesh.points.PointCloud(coords, colors=(colors * 255).astype(np.uint8))
        pc_mesh.export(pc_path)
        print(f"[SUCCESS] Point cloud saved: optimized_pc_{idx}.ply")

        # HIGHER RESOLUTION volumetric reconstruction
        print("Creating HIGH-RESOLUTION volume (128x128x128)...")
        resolution = 128  # DOUBLED resolution

        # Normalize
        coords_min = coords.min(axis=0)
        coords_max = coords.max(axis=0)
        coords_norm = (coords - coords_min) / (coords_max - coords_min + 1e-8)

        # Create fine grid
        x = np.linspace(0, 1, resolution)
        y = np.linspace(0, 1, resolution)
        z = np.linspace(0, 1, resolution)
        grid_x, grid_y, grid_z = np.meshgrid(x, y, z, indexing='ij')

        # Build KD-tree
        tree = cKDTree(coords_norm)
        grid_points = np.stack([grid_x.ravel(), grid_y.ravel(), grid_z.ravel()], axis=1)

        # Query distances
        print("Computing occupancy field...")
        distances, _ = tree.query(grid_points, k=1)

        # TIGHTER threshold for better detail
        threshold = 0.03  # Reduced from 0.05
        occupancy = (distances < threshold).astype(float)
        occupancy = occupancy.reshape((resolution, resolution, resolution))

        # Marching cubes
        print("Applying Marching Cubes...")
        verts, faces, normals, values = measure.marching_cubes(occupancy, level=0.5)

        # Scale back
        verts = verts / resolution
        verts = verts * (coords_max - coords_min) + coords_min

        # Create mesh
        mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_normals=normals)

        # Map colors
        print("Mapping colors...")
        tree_orig = cKDTree(coords)
        _, indices = tree_orig.query(mesh.vertices, k=5)
        neighbor_colors = colors[indices]
        vertex_colors = neighbor_colors.mean(axis=1)
        mesh.visual.vertex_colors = (vertex_colors * 255).astype(np.uint8)

        # Clean
        mesh.remove_duplicate_faces()
        mesh.remove_unreferenced_vertices()

        print(f"[SUCCESS] Mesh created: {len(mesh.vertices):,} vertices, {len(mesh.faces):,} faces")

        # Save
        mesh_path = f"D:/Work/Uni/FYP/architext/outputs/optimized_house_{idx}.ply"
        mesh.export(mesh_path)
        print(f"[SUCCESS] Saved: optimized_house_{idx}.ply")

        obj_path = f"D:/Work/Uni/FYP/architext/outputs/optimized_house_{idx}.obj"
        mesh.export(obj_path)
        print(f"[SUCCESS] Saved: optimized_house_{idx}.obj")

    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
print("ULTRA-OPTIMIZATION COMPLETE!")
print("="*60)
print(f"\nGenerated {len(prompts)} optimized house variations")
print("\nOptimizations applied:")
print("- Guidance scale: 15.0 (maximum)")
print("- Grid resolution: 128x128x128 (double)")
print("- Occupancy threshold: 0.03 (tighter)")
print("- Simplified prompts (better for Point-E)")
print("\nFiles to test in Blender:")
for i in range(1, len(prompts) + 1):
    print(f"  - optimized_house_{i}.ply")
print("\nTIP: Compare these with Shap-E output for quality check!")
