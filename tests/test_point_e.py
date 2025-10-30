"""
Test script for Point-E model
Generates 3D point clouds from text prompts using OpenAI's Point-E
Point clouds can be converted to meshes
"""

import torch
import os
import sys
from datetime import datetime
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_point_e():
    """Test Point-E text-to-3D generation with house prompts"""
    print("="*60)
    print("POINT-E MODEL TEST")
    print("="*60)

    # Check device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\nUsing device: {device}")
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"CUDA Version: {torch.version.cuda}")

    try:
        from diffusers import DiffusionPipeline
        import trimesh
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("\nPlease install required packages:")
        print("pip install diffusers transformers accelerate trimesh")
        return False

    print("\n" + "-"*60)
    print("Loading Point-E model...")
    print("-"*60)

    try:
        # Load model - Point-E uses a different pipeline
        dtype = torch.float16 if device == "cuda" else torch.float32

        # Point-E has a text-to-point model
        pipe = DiffusionPipeline.from_pretrained(
            "openai/point-e-base",
            torch_dtype=dtype,
        )
        pipe = pipe.to(device)
        print("✅ Model loaded successfully!")

    except Exception as e:
        print(f"❌ Error loading model: {e}")
        print("\nNote: Point-E might require manual installation:")
        print("git clone https://github.com/openai/point-e.git")
        print("cd point-e && pip install -e .")
        return False

    # Test prompts specifically for houses
    test_prompts = [
        "a two story house with windows",
        "a small cottage",
        "a modern residential building",
        "a house with a garage",
        "a simple home structure"
    ]

    # Create outputs directory
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "point_e_tests")
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

            # Generate point cloud
            print("Running inference... (this may take 30-60 seconds)")
            output = pipe(
                prompt,
                num_inference_steps=40,
            )

            generation_time = (datetime.now() - start_time).total_seconds()

            # Get point cloud data
            if hasattr(output, 'point_clouds'):
                point_cloud = output.point_clouds[0]
            elif hasattr(output, 'images'):
                # Some versions return images that need to be decoded
                point_cloud = output.images[0]
            else:
                point_cloud = output[0]

            # Convert point cloud to mesh using ball pivoting or poisson reconstruction
            # For now, save as point cloud
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"{i:02d}_{prompt.replace(' ', '_').replace(',', '')[:30]}_{timestamp}"

            # Try to convert to mesh if possible
            try:
                # If point_cloud is a numpy array
                if isinstance(point_cloud, np.ndarray):
                    points = point_cloud
                else:
                    points = np.array(point_cloud)

                # Create a simple point cloud mesh
                cloud = trimesh.points.PointCloud(points)

                # Save point cloud
                ply_path = os.path.join(output_dir, f"{base_filename}_pointcloud.ply")
                cloud.export(ply_path)

                # Try to create mesh from points using alpha shape or convex hull
                try:
                    # Convex hull as simple mesh conversion
                    mesh = trimesh.convex.convex_hull(points)
                    mesh_path = os.path.join(output_dir, f"{base_filename}_mesh.obj")
                    mesh.export(mesh_path)

                    num_vertices = len(mesh.vertices)
                    num_faces = len(mesh.faces)

                    print(f"✅ Generation successful!")
                    print(f"   Time: {generation_time:.2f}s")
                    print(f"   Points: {len(points):,}")
                    print(f"   Mesh Vertices: {num_vertices:,}")
                    print(f"   Mesh Faces: {num_faces:,}")
                    print(f"   Saved: {base_filename}_[pointcloud.ply|mesh.obj]")

                    results.append({
                        "prompt": prompt,
                        "success": True,
                        "time": generation_time,
                        "points": len(points),
                        "vertices": num_vertices,
                        "faces": num_faces,
                        "files": [ply_path, mesh_path]
                    })

                except Exception as mesh_error:
                    print(f"✅ Point cloud generated (mesh conversion failed)")
                    print(f"   Time: {generation_time:.2f}s")
                    print(f"   Points: {len(points):,}")
                    print(f"   Saved: {base_filename}_pointcloud.ply")
                    print(f"   Note: {mesh_error}")

                    results.append({
                        "prompt": prompt,
                        "success": True,
                        "time": generation_time,
                        "points": len(points),
                        "files": [ply_path]
                    })

            except Exception as save_error:
                print(f"❌ Error saving output: {save_error}")
                results.append({
                    "prompt": prompt,
                    "success": False,
                    "error": str(save_error)
                })

        except Exception as e:
            print(f"❌ Error generating: {e}")
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
        print(f"\nAverage generation time: {avg_time:.2f}s")

    print(f"\nAll outputs saved to: {output_dir}")
    print("\nNext steps:")
    print("1. Open the generated files in MeshLab or CloudCompare")
    print("2. Compare point cloud quality with Shap-E meshes")
    print("3. Evaluate which model works better for houses")
    print("4. Consider if point clouds are sufficient or if meshes are needed")

    return successful > 0

if __name__ == "__main__":
    success = test_point_e()
    sys.exit(0 if success else 1)
