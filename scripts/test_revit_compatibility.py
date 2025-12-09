"""
Test IFC generation for Revit compatibility.

This script tests if the generated IFC files can be opened in Revit.
Key requirements for Revit:
1. IFC2X3 schema (better compatibility than IFC4)
2. Proper unit definitions (IfcUnitAssignment)
3. Complete spatial hierarchy (Project > Site > Building > Storey)
4. Valid geometry representations
"""

import os
import sys

# Setup paths
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

import ifcopenshell
from generate_bim import BIMGenerator
from graph_layout_optimizer import GraphLayoutOptimizer


def verify_ifc_structure(ifc_path: str) -> dict:
    """
    Verify the IFC file structure for Revit compatibility.

    Returns dict with verification results.
    """
    results = {
        "path": ifc_path,
        "valid": True,
        "issues": [],
        "info": {}
    }

    try:
        ifc = ifcopenshell.open(ifc_path)
    except Exception as e:
        results["valid"] = False
        results["issues"].append(f"Failed to open IFC file: {e}")
        return results

    # Check schema
    results["info"]["schema"] = ifc.schema
    if ifc.schema not in ["IFC2X3", "IFC4"]:
        results["issues"].append(f"Unusual schema: {ifc.schema}")

    # Check for required entities
    required_entities = [
        ("IfcProject", 1),
        ("IfcSite", 1),
        ("IfcBuilding", 1),
        ("IfcBuildingStorey", 1),
        ("IfcUnitAssignment", 1),
        ("IfcGeometricRepresentationContext", 1),
    ]

    for entity_type, min_count in required_entities:
        entities = ifc.by_type(entity_type)
        count = len(entities) if entities else 0
        results["info"][entity_type] = count

        if count < min_count:
            results["valid"] = False
            results["issues"].append(f"Missing {entity_type} (found {count}, need {min_count})")

    # Check units
    units = ifc.by_type("IfcUnitAssignment")
    if units:
        unit_types = []
        for unit_assignment in units:
            for unit in unit_assignment.Units:
                if hasattr(unit, "UnitType"):
                    unit_types.append(unit.UnitType)
        results["info"]["unit_types"] = unit_types

        required_units = ["LENGTHUNIT", "AREAUNIT", "VOLUMEUNIT"]
        for req_unit in required_units:
            if req_unit not in unit_types:
                results["issues"].append(f"Missing unit type: {req_unit}")

    # Check spatial hierarchy
    project = ifc.by_type("IfcProject")
    if project:
        project = project[0]
        results["info"]["project_name"] = project.Name

        # Check if project has representation contexts
        if hasattr(project, "RepresentationContexts") and project.RepresentationContexts:
            results["info"]["has_context"] = True
        else:
            results["issues"].append("Project missing RepresentationContexts")

        # Check if project has units
        if hasattr(project, "UnitsInContext") and project.UnitsInContext:
            results["info"]["has_units"] = True
        else:
            results["valid"] = False
            results["issues"].append("Project missing UnitsInContext")

    # Count elements
    walls = ifc.by_type("IfcWall") or []
    wall_std = ifc.by_type("IfcWallStandardCase") or []
    spaces = ifc.by_type("IfcSpace") or []

    results["info"]["walls"] = len(walls) + len(wall_std)
    results["info"]["spaces"] = len(spaces)

    # Check if walls have geometry
    for wall in (walls + wall_std)[:1]:  # Check first wall
        if wall.Representation:
            results["info"]["walls_have_geometry"] = True
        else:
            results["issues"].append("Walls missing geometry")
            break

    return results


def create_test_files():
    """Create test IFC files for Revit compatibility testing."""
    output_dir = os.path.join(os.path.dirname(script_dir), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Test cases using GraphLayoutOptimizer for proper non-overlapping layouts
    test_cases = [
        {
            "name": "revit_simple",
            "description": "Simple 2-room layout",
            "spec": {
                "bedrooms": 1,
                "bathrooms": 1,
                "kitchen": True,
                "living_room": True,
            }
        },
        {
            "name": "revit_3bed",
            "description": "3 bedroom house",
            "spec": {
                "bedrooms": 3,
                "bathrooms": 2,
                "kitchen": True,
                "living_room": True,
                "dining_room": True,
            }
        },
        {
            "name": "revit_4bed_study",
            "description": "4 bedroom house with study",
            "spec": {
                "bedrooms": 4,
                "bathrooms": 3,
                "kitchen": True,
                "living_room": True,
                "dining_room": True,
                "study": True,
            }
        },
    ]

    results = []

    for test in test_cases:
        print(f"\n{'=' * 60}")
        print(f"Creating: {test['name']}")
        print(f"Description: {test['description']}")
        print(f"Spec: {test['spec']}")
        print("=" * 60)

        # Use GraphLayoutOptimizer for proper room placement
        optimizer = GraphLayoutOptimizer()
        graph, rooms = optimizer.optimize_layout(test['spec'])
        info = optimizer.get_layout_info()

        print(f"\nGenerated {info['num_rooms']} rooms with {info['num_connections']} connections")

        # Create BIM
        generator = BIMGenerator()
        generator.create_project_structure(f"Revit Test - {test['description']}")

        for room in rooms:
            room_name = room.id.replace('_', ' ').title()
            generator.create_simple_room(
                room_name,
                room.width,
                room.height,
                2.7,
                room.x,
                room.y
            )
            print(f"  Created: {room_name} ({room.width:.1f}x{room.height:.1f}m) at ({room.x:.1f}, {room.y:.1f})")

        output_path = os.path.join(output_dir, f"{test['name']}.ifc")
        generator.ifc.write(output_path)

        # Verify
        verify_result = verify_ifc_structure(output_path)
        results.append(verify_result)

        # Print verification
        print(f"\nVerification:")
        print(f"  Schema: {verify_result['info'].get('schema', 'N/A')}")
        print(f"  Walls: {verify_result['info'].get('walls', 0)}")
        print(f"  Spaces: {verify_result['info'].get('spaces', 0)}")
        print(f"  Has Units: {verify_result['info'].get('has_units', False)}")
        print(f"  Has Context: {verify_result['info'].get('has_context', False)}")

        if verify_result["issues"]:
            print(f"\n  Issues:")
            for issue in verify_result["issues"]:
                print(f"    - {issue}")
        else:
            print(f"\n  [OK] No issues found")

        file_size = os.path.getsize(output_path) / 1024
        print(f"\n  Output: {output_path} ({file_size:.1f} KB)")

    return results


def main():
    """Run Revit compatibility tests."""
    print("=" * 70)
    print("IFC REVIT COMPATIBILITY TEST")
    print("=" * 70)

    results = create_test_files()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    all_valid = True
    for result in results:
        status = "[OK]" if not result["issues"] else "[!!]"
        if result["issues"]:
            all_valid = False
        name = os.path.basename(result["path"])
        print(f"{status} {name}")

    print("\n" + "-" * 70)
    if all_valid:
        print("[OK] All files should be Revit-compatible!")
    else:
        print("[!!] Some files may have compatibility issues")

    print("\nTest files created in output/ folder:")
    print("  - revit_simple.ifc     (1 bed, 1 bath)")
    print("  - revit_3bed.ifc       (3 bed, 2 bath)")
    print("  - revit_4bed_study.ifc (4 bed, 3 bath, study)")
    print("\nTo view in 3D in Revit:")
    print("  - View tab > 3D View > Default 3D View")
    print("  - Or press the house icon in Quick Access Toolbar")
    print("=" * 70)


if __name__ == "__main__":
    main()
