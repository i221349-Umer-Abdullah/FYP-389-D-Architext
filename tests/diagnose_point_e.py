"""
Diagnose Point-E output files
"""
import trimesh
import numpy as np

print("="*60)
print("POINT-E OUTPUT DIAGNOSTICS")
print("="*60)

files = [
    "D:/Work/Uni/FYP/architext/outputs/point_e_improved_house.ply",
    "D:/Work/Uni/FYP/architext/outputs/point_e_point_cloud.ply",
    "D:/Work/Uni/FYP/architext/outputs/point_e_test_house.ply"
]

for filepath in files:
    print(f"\n{'-'*60}")
    print(f"File: {filepath.split('/')[-1]}")
    print(f"{'-'*60}")

    try:
        mesh = trimesh.load(filepath)

        if isinstance(mesh, trimesh.PointCloud):
            print(f"Type: Point Cloud")
            print(f"Points: {len(mesh.vertices):,}")
            print(f"Has colors: {hasattr(mesh, 'colors') and mesh.colors is not None}")
            if hasattr(mesh, 'bounds'):
                try:
                    bounds = mesh.bounds
                    print(f"Bounds: min={bounds[0]}, max={bounds[1]}")
                except:
                    print("Bounds: Could not compute")
        elif isinstance(mesh, trimesh.Trimesh):
            print(f"Type: Mesh")
            print(f"Vertices: {len(mesh.vertices):,}")
            print(f"Faces: {len(mesh.faces):,}")
            print(f"Has vertex colors: {hasattr(mesh.visual, 'vertex_colors')}")

            if len(mesh.faces) == 0:
                print("[ERROR] Mesh has NO FACES - will appear empty in Blender")
            else:
                try:
                    bounds = mesh.bounds
                    print(f"Bounds: min={bounds[0]}, max={bounds[1]}")
                except:
                    print("Bounds: Could not compute")
        else:
            print(f"Type: {type(mesh)}")
            print(f"Unknown type")

    except FileNotFoundError:
        print("[ERROR] File not found")
    except Exception as e:
        print(f"[ERROR] Failed to load: {e}")

print("\n" + "="*60)
print("DIAGNOSIS COMPLETE")
print("="*60)
print("\nConclusion:")
print("If meshes have 0 faces, they will appear empty in Blender.")
print("Point clouds should be visible if they have points.")
