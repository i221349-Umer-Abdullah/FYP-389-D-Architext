"""
Quick test of layout optimizer integration with BIM generator.
"""
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from generate_bim import BIMGenerator

def test_layout_optimizer():
    """Test the integrated layout optimizer."""
    print("=" * 80)
    print("TESTING LAYOUT OPTIMIZER INTEGRATION")
    print("=" * 80)

    # Sample specification
    spec = {
        "bedrooms": 3,
        "bathrooms": 2,
        "kitchen": True,
        "living_room": True,
        "dining_room": False,
        "study": False,
        "total_area_sqm": 120
    }

    print("\nInput specification:")
    print(f"  Bedrooms: {spec['bedrooms']}")
    print(f"  Bathrooms: {spec['bathrooms']}")
    print(f"  Kitchen: {spec['kitchen']}")
    print(f"  Living Room: {spec['living_room']}")
    print(f"  Total Area: {spec['total_area_sqm']} sqm")

    # Generate BIM
    print("\n" + "=" * 80)
    print("GENERATING BIM WITH OPTIMIZED LAYOUT...")
    print("=" * 80)

    generator = BIMGenerator()
    output_file = "output/test_optimized_layout.ifc"
    generator.generate_from_spec(spec, output_path=output_file)

    print("\n" + "=" * 80)
    print("SUCCESS!")
    print("=" * 80)
    print(f"\nIFC file saved to: {output_file}")
    print("\nYou can now open this file in Blender with BlenderBIM addon")
    print("to verify that rooms are placed intelligently without overlaps.")

if __name__ == "__main__":
    test_layout_optimizer()
