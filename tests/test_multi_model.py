"""
Test script for multi-model architecture
Tests the new model registry and model wrappers
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import get_global_registry
from app.models.shap_e_model import ShapEModel
from app.models.triposr_model import TripoSRModel


def test_registry():
    """Test the model registry"""
    print("="*70)
    print("Testing Model Registry")
    print("="*70)

    registry = get_global_registry()

    # List all registered models
    models = registry.list_models()
    print(f"\n[Registry] Registered models: {models}")

    # Get metadata for each model
    for model_name in models:
        metadata = registry.get_metadata(model_name)
        print(f"\n[Model: {metadata.display_name}]")
        print(f"  Name: {metadata.name}")
        print(f"  Version: {metadata.version}")
        print(f"  Source: {metadata.source}")
        print(f"  Description: {metadata.description}")
        print(f"  Capabilities: {', '.join(metadata.capabilities)}")

    print("\n" + "="*70)
    print("[SUCCESS] Registry test passed!")
    print("="*70)


def test_shap_e_model():
    """Test Shap-E model with new architecture"""
    print("\n" + "="*70)
    print("Testing Shap-E Model")
    print("="*70)

    registry = get_global_registry()

    try:
        # Get Shap-E model
        print("\n[Test] Getting Shap-E model from registry...")
        model = registry.get_model("shap-e", device="cuda")

        print(f"[Test] Model loaded: {model.is_loaded()}")

        # Test generation
        print("\n[Test] Generating house from prompt...")
        prompt = "a modern house"
        mesh = model.generate(prompt, num_steps=32, guidance_scale=15.0, frame_size=128)

        print(f"[Test] Generated mesh: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")

        # Get stats
        stats = model.get_generation_stats(mesh)
        print(f"[Test] Mesh stats:")
        print(f"  - Vertices: {stats['vertices']}")
        print(f"  - Faces: {stats['faces']}")
        print(f"  - Watertight: {stats['is_watertight']}")
        print(f"  - Surface area: {stats['area']:.2f} m²")

        # Export mesh
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "multi_model_test")
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"shap_e_{timestamp}.obj")
        mesh.export(output_path)

        print(f"[Test] Exported to: {output_path}")

        print("\n" + "="*70)
        print("[SUCCESS] Shap-E test passed!")
        print("="*70)

    except Exception as e:
        print(f"\n[ERROR] Shap-E test failed: {e}")
        import traceback
        traceback.print_exc()


def test_triposr_model():
    """Test TripoSR model with new architecture"""
    print("\n" + "="*70)
    print("Testing TripoSR Model")
    print("="*70)

    registry = get_global_registry()

    try:
        # Get TripoSR model
        print("\n[Test] Getting TripoSR model from registry...")
        model = registry.get_model("triposr", device="cuda")

        print(f"[Test] Model loaded: {model.is_loaded()}")

        # Test generation (text -> image -> 3D pipeline)
        print("\n[Test] Generating house from prompt (text->image->3D)...")
        prompt = "a simple modern house, white background"
        mesh = model.generate(prompt, num_steps=20, guidance_scale=7.5, mc_resolution=64)

        print(f"[Test] Generated mesh: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")

        # Get stats
        stats = model.get_generation_stats(mesh)
        print(f"[Test] Mesh stats:")
        print(f"  - Vertices: {stats['vertices']}")
        print(f"  - Faces: {stats['faces']}")
        print(f"  - Watertight: {stats['is_watertight']}")

        # Export mesh
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "multi_model_test")
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"triposr_{timestamp}.obj")
        mesh.export(output_path)

        print(f"[Test] Exported to: {output_path}")

        print("\n" + "="*70)
        print("[SUCCESS] TripoSR test passed!")
        print("="*70)

    except Exception as e:
        print(f"\n[ERROR] TripoSR test failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main test function"""
    print("\n")
    print("="*70)
    print("MULTI-MODEL ARCHITECTURE TEST SUITE")
    print("="*70)

    # Test 1: Registry
    test_registry()

    # Test 2: Shap-E Model
    test_shap_e_model()

    # Test 3: TripoSR Model
    print("\n[Note] TripoSR test uses Stable Diffusion + simple 3D reconstruction")
    print("[Note] This is a simplified version. Full TripoSR requires manual installation.")
    test_triposr_model()

    print("\n")
    print("="*70)
    print("ALL TESTS COMPLETE!")
    print("="*70)


if __name__ == "__main__":
    main()
