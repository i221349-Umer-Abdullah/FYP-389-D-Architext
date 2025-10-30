"""
Test script for Shap-E model
Generates 3D house meshes from text prompts using OpenAI's Shap-E
"""

import torch
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_shap_e():
    """Test Shap-E text-to-3D generation with house prompts"""
    print("="*60)
    print("SHAP-E MODEL TEST")
    print("="*60)

    # Check device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\nUsing device: {device}")
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"CUDA Version: {torch.version.cuda}")

    try:
        from diffusers import ShapEPipeline
        import trimesh
    except ImportError as e:
        print(f"\n[ERROR] Import Error: {e}")
        print("\nPlease install required packages:")
        print("pip install diffusers transformers accelerate trimesh")
        return False

    print("\n" + "-"*60)
    print("Loading Shap-E model...")
    print("-"*60)

    try:
        # Load model (don't use variant parameter, it's not supported)
        dtype = torch.float16 if device == "cuda" else torch.float32
        pipe = ShapEPipeline.from_pretrained(
            "openai/shap-e",
            torch_dtype=dtype
        )
        pipe = pipe.to(device)
        print("[SUCCESS] Model loaded successfully!")

    except Exception as e:
        print(f"[ERROR] Error loading model: {e}")
        return False

    # Test prompts specifically for houses
    test_prompts = [
        "a modern two-story house",
        "a small cottage with a chimney",
        "a simple residential building",
        "a contemporary house with large windows",
        "a traditional suburban home"
    ]

    # Create outputs directory
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "shap_e_tests")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nOutput directory: {output_dir}")
    print("\n" + "="*60)
    print("GENERATION TESTS")
    print("="*60)

    results = []

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n[{i}/{len(test_prompts)}] Generating: '{prompt}'")
        print("-"*60)

        try:
            start_time = datetime.now()

            # Generate with different parameters
            print("Running inference... (this may take 1-2 minutes)")
            output = pipe(
                prompt,
                num_inference_steps=64,
                frame_size=256,
                output_type="mesh"
            )

            generation_time = (datetime.now() - start_time).total_seconds()

            # Extract mesh from Shap-E output
            # The output.images contains MeshDecoderOutput objects with verts and faces
            mesh_output = output.images[0]

            # Convert tensors to numpy and create trimesh object
            import numpy as np
            vertices = mesh_output.verts.cpu().numpy()
            faces = mesh_output.faces.cpu().numpy()

            # Get vertex colors if available (RGB channels)
            vertex_colors = None
            if hasattr(mesh_output, 'vertex_channels') and mesh_output.vertex_channels:
                r = mesh_output.vertex_channels['R'].cpu().numpy()
                g = mesh_output.vertex_channels['G'].cpu().numpy()
                b = mesh_output.vertex_channels['B'].cpu().numpy()
                # Stack RGB and add alpha channel (fully opaque)
                vertex_colors = np.stack([r, g, b, np.ones_like(r)], axis=1)
                # Scale to 0-255 range
                vertex_colors = (vertex_colors * 255).astype(np.uint8)

            # Create trimesh object
            mesh = trimesh.Trimesh(vertices=vertices, faces=faces, vertex_colors=vertex_colors)

            # Save in multiple formats
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"{i:02d}_{prompt.replace(' ', '_').replace(',', '')[:30]}_{timestamp}"

            # Save as PLY (preserves color/texture if any)
            ply_path = os.path.join(output_dir, f"{base_filename}.ply")
            mesh.export(ply_path)

            # Save as OBJ (widely compatible)
            obj_path = os.path.join(output_dir, f"{base_filename}.obj")
            mesh.export(obj_path)

            # Get mesh statistics
            num_vertices = len(mesh.vertices)
            num_faces = len(mesh.faces)
            bounds = mesh.bounds
            size = bounds[1] - bounds[0]

            print(f"[SUCCESS] Generation successful!")
            print(f"   Time: {generation_time:.2f}s")
            print(f"   Vertices: {num_vertices:,}")
            print(f"   Faces: {num_faces:,}")
            print(f"   Size: [{size[0]:.2f}, {size[1]:.2f}, {size[2]:.2f}]")
            print(f"   Saved: {base_filename}.[ply|obj]")

            results.append({
                "prompt": prompt,
                "success": True,
                "time": generation_time,
                "vertices": num_vertices,
                "faces": num_faces,
                "files": [ply_path, obj_path]
            })

        except Exception as e:
            print(f"[ERROR] Error generating: {e}")
            results.append({
                "prompt": prompt,
                "success": False,
                "error": str(e)
            })

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    successful = sum(1 for r in results if r.get("success", False))
    print(f"\nSuccessful generations: {successful}/{len(test_prompts)}")

    if successful > 0:
        avg_time = sum(r["time"] for r in results if r.get("success")) / successful
        avg_vertices = sum(r["vertices"] for r in results if r.get("success")) / successful
        avg_faces = sum(r["faces"] for r in results if r.get("success")) / successful

        print(f"\nAverage generation time: {avg_time:.2f}s")
        print(f"Average vertices: {avg_vertices:,.0f}")
        print(f"Average faces: {avg_faces:,.0f}")

    print(f"\nAll outputs saved to: {output_dir}")
    print("\nNext steps:")
    print("1. Open the generated .obj files in Blender or MeshLab to view")
    print("2. Evaluate the quality of house generation")
    print("3. Try different prompts to test model capabilities")
    print("4. Compare with Point-E results (run test_point_e.py)")

    return successful > 0

if __name__ == "__main__":
    success = test_shap_e()
    sys.exit(0 if success else 1)
