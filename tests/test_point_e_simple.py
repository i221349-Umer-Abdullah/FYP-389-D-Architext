"""
Simple Point-E Test Script
Tests if Point-E can generate 3D models from text
"""
import torch
import numpy as np
from point_e.diffusion.configs import DIFFUSION_CONFIGS, diffusion_from_config
from point_e.diffusion.sampler import PointCloudSampler
from point_e.models.download import load_checkpoint
from point_e.models.configs import MODEL_CONFIGS, model_from_config
from point_e.util.plotting import plot_point_cloud
import trimesh

print("="*60)
print("POINT-E SIMPLE TEST")
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
    base_name = 'base40M-textvec'  # Use text-conditioned model
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

    # Create sampler
    sampler = PointCloudSampler(
        device=device,
        models=[base_model, upsampler_model],
        diffusions=[base_diffusion, upsampler_diffusion],
        num_points=[1024, 4096 - 1024],
        aux_channels=['R', 'G', 'B'],
        guidance_scale=[3.0, 3.0],
    )

    print("[SUCCESS] Sampler created")

    # Generate from text prompt
    print("\n" + "="*60)
    print("GENERATING POINT CLOUD")
    print("="*60)

    prompt = "a modern two-story house"
    print(f"\nPrompt: '{prompt}'")
    print("Generating point cloud... (this may take 2-3 minutes)")

    # Generate samples
    samples = None
    for x in sampler.sample_batch_progressive(batch_size=1, model_kwargs=dict(texts=[prompt])):
        samples = x

    print("\n[SUCCESS] Point cloud generated!")

    # Extract point cloud
    pc = sampler.output_to_point_clouds(samples)[0]
    print(f"Point cloud size: {pc.coords.shape[0]} points")

    # Convert to mesh using marching cubes or alpha shapes
    print("\nConverting point cloud to mesh...")

    # Simple method: Create mesh from point cloud
    coords = pc.coords
    colors = np.stack([pc.channels['R'], pc.channels['G'], pc.channels['B']], axis=-1)

    # Create a simple mesh using convex hull
    mesh = trimesh.convex.convex_hull(coords)

    # Try to add colors to vertices
    if colors.shape[0] == mesh.vertices.shape[0]:
        vertex_colors = (colors * 255).astype(np.uint8)
        mesh.visual.vertex_colors = vertex_colors

    print(f"[SUCCESS] Mesh created:")
    print(f"  Vertices: {len(mesh.vertices):,}")
    print(f"  Faces: {len(mesh.faces):,}")

    # Save mesh
    output_path = "D:/Work/Uni/FYP/architext/outputs/point_e_test_house.ply"
    mesh.export(output_path)
    print(f"\n[SUCCESS] Saved to: {output_path}")

    print("\n" + "="*60)
    print("TEST COMPLETE!")
    print("="*60)
    print("\nPoint-E is working! You can now:")
    print("1. Open the .ply file in Blender or MeshLab")
    print("2. Integrate Point-E into the main app")

except Exception as e:
    print(f"\n[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
