"""
Test layout optimizer with complex building specifications.
"""
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from generate_bim import BIMGenerator

def test_complex_layouts():
    """Test multiple building configurations."""
    print("=" * 80)
    print("TESTING LAYOUT OPTIMIZER WITH COMPLEX BUILDINGS")
    print("=" * 80)

    test_cases = [
        {
            "name": "Small Apartment",
            "spec": {
                "bedrooms": 2,
                "bathrooms": 1,
                "kitchen": True,
                "living_room": True,
                "dining_room": False,
                "study": False,
            },
            "output": "output/test_small_apartment.ifc"
        },
        {
            "name": "Family Home",
            "spec": {
                "bedrooms": 4,
                "bathrooms": 3,
                "kitchen": True,
                "living_room": True,
                "dining_room": True,
                "study": True,
            },
            "output": "output/test_family_home.ifc"
        },
        {
            "name": "Luxury Villa",
            "spec": {
                "bedrooms": 5,
                "bathrooms": 4,
                "kitchen": True,
                "living_room": True,
                "dining_room": True,
                "study": True,
                "total_area_sqm": 300
            },
            "output": "output/test_luxury_villa.ifc"
        }
    ]

    for test in test_cases:
        print("\n" + "=" * 80)
        print(f"TEST: {test['name']}")
        print("=" * 80)

        spec = test['spec']
        print(f"\nSpecification:")
        print(f"  Bedrooms: {spec['bedrooms']}")
        print(f"  Bathrooms: {spec['bathrooms']}")
        print(f"  Kitchen: {spec.get('kitchen', False)}")
        print(f"  Living Room: {spec.get('living_room', False)}")
        print(f"  Dining Room: {spec.get('dining_room', False)}")
        print(f"  Study: {spec.get('study', False)}")
        if 'total_area_sqm' in spec:
            print(f"  Total Area: {spec['total_area_sqm']} sqm")

        print(f"\nGenerating BIM...")
        generator = BIMGenerator()
        generator.generate_from_spec(spec, output_path=test['output'])

        print(f"✓ IFC file saved: {test['output']}")

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print("\nGenerated IFC files:")
    for test in test_cases:
        print(f"  - {test['output']}")
    print("\nOpen these files in Blender with BlenderBIM addon to visualize the layouts.")

if __name__ == "__main__":
    test_complex_layouts()
