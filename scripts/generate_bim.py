"""
=============================================================================
ArchiText: BIM Generation Engine
=============================================================================

This module implements the IFC (Industry Foundation Classes) generation engine
for the ArchiText system. It converts JSON building specifications into valid
IFC files that can be opened in professional BIM software.

Key Components:
---------------
1. BIMGenerator: Main class for IFC file creation
2. Rule-Based Layout Optimizer: Enhances model output with architectural rules

IFC Generation Process:
-----------------------
    1. Create IFC project hierarchy (Project → Site → Building → Storey)
    2. Apply layout optimization using rule-based engine
    3. Generate rooms with proper dimensions and placements
    4. Create walls with accurate geometry (extruded profiles)
    5. Establish spatial relationships between elements

Output Compatibility:
---------------------
    - Autodesk Revit (IFC2X3 import)
    - BlenderBIM / Bonsai
    - FreeCAD
    - ArchiCAD
    - Any IFC-compliant viewer

Technical Notes:
----------------
    - Uses IFC2X3 schema for maximum compatibility (especially Revit)
    - Includes proper unit definitions (SI - meters)
    - Creates IfcWallStandardCase for walls (better viewer support)
    - Generates IfcSpace entities for room volumes

Dependencies:
-------------
    - ifcopenshell: IFC file manipulation library
    - layout_optimizer_rules: Rule-based layout optimization

Author: ArchiText Team
Version: 1.0.0
=============================================================================
"""

import json
import datetime
import uuid
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.geom

from layout_optimizer_rules import RuleBasedLayoutOptimizer


# =============================================================================
# BIM GENERATOR CLASS
# =============================================================================

class BIMGenerator:
    """
    IFC BIM Generation Engine.

    This class creates IFC (Industry Foundation Classes) files from building
    specifications. It works in conjunction with the rule-based layout optimizer
    to produce architecturally valid floor plans.

    The generator handles:
        - IFC project structure creation
        - Spatial hierarchy (Project → Site → Building → Storey)
        - Wall geometry generation
        - Space/room definitions
        - Unit assignments for proper scaling

    Attributes:
        ifc: The IfcOpenShell file object
        project: The IfcProject entity
        site: The IfcSite entity
        building: The IfcBuilding entity
        storey: The IfcBuildingStorey entity
        owner_history: History information for IFC entities
        geom_context: Geometric representation context

    Example:
        >>> generator = BIMGenerator()
        >>> generator.create_project_structure("My House")
        >>> generator.create_simple_room("Living Room", 5.0, 4.0, 2.7, 0, 0)
        >>> generator.ifc.write("output.ifc")
    """

    def __init__(self):
        """
        Initialize the BIM generator.

        Sets up instance variables for IFC entities. The actual IFC file
        is created when create_project_structure() is called.
        """
        self.ifc = None
        self.project = None
        self.site = None
        self.building = None
        self.storey = None
        self.owner_history = None
        self.geom_context = None  # Geometric representation context
    
    def create_project_structure(self, project_name: str = "AI Generated Building"):
        """
        Create the basic IFC project structure.

        Args:
            project_name: Name of the building project
        """
        # Create a new IFC file (IFC2X3 for better Revit compatibility)
        self.ifc = ifcopenshell.file(schema="IFC2X3")

        # Create basic IFC entities manually for compatibility
        create_guid = lambda: ifcopenshell.guid.compress(uuid.uuid4().hex)

        # Create OwnerHistory
        person = self.ifc.createIfcPerson(
            None,  # Id
            "Generator",  # FamilyName
            "AI",  # GivenName
            None, None, None, None, None
        )

        org = self.ifc.createIfcOrganization(
            None,  # Id
            "AI BIM System",  # Name
            None, None, None
        )

        person_org = self.ifc.createIfcPersonAndOrganization(person, org, None)

        application = self.ifc.createIfcApplication(
            org,
            "1.0",
            "Text-to-BIM AI",
            "TextToBIM"
        )

        timestamp = int(datetime.datetime.now().timestamp())

        self.owner_history = self.ifc.createIfcOwnerHistory(
            person_org,
            application,
            None,  # State
            "ADDED",  # ChangeAction (IFC2X3 enum)
            None,  # LastModifiedDate
            None,  # LastModifyingUser
            None,  # LastModifyingApplication
            timestamp  # CreationDate
        )

        # Create units (REQUIRED for Revit compatibility)
        units = self._create_units()

        # Create geometric representation context FIRST
        world_coord = self.create_axis2placement_3d([0., 0., 0.])
        self.geom_context = self.ifc.createIfcGeometricRepresentationContext(
            None,  # ContextIdentifier
            "Model",  # ContextType
            3,  # CoordinateSpaceDimension
            1.0e-5,  # Precision
            world_coord,  # WorldCoordinateSystem
            None  # TrueNorth
        )

        # Create subcontext for body representation (required by some viewers)
        self.body_context = self.ifc.createIfcGeometricRepresentationSubContext(
            "Body",  # ContextIdentifier
            "Model",  # ContextType
            None, None, None, None,  # Inherited from parent
            self.geom_context,  # ParentContext
            None,  # TargetScale
            "MODEL_VIEW",  # TargetView
            None  # UserDefinedTargetView
        )

        # Create project with units
        self.project = self.ifc.createIfcProject(
            create_guid(),
            self.owner_history,
            project_name,
            None,  # Description
            None,  # ObjectType
            None,  # LongName
            None,  # Phase
            [self.geom_context],  # RepresentationContexts
            units  # UnitsInContext
        )

        # Create site placement
        site_placement = self.ifc.createIfcLocalPlacement(
            None,
            self.create_axis2placement_3d([0., 0., 0.])
        )

        # Create site
        self.site = self.ifc.createIfcSite(
            create_guid(),
            self.owner_history,
            "Site",
            None,  # Description
            None,  # ObjectType
            site_placement,
            None,  # Representation
            None,  # LongName
            "ELEMENT",  # CompositionType
            None, None, None, None, None  # RefLatitude, RefLongitude, etc.
        )

        # Create building placement
        building_placement = self.ifc.createIfcLocalPlacement(
            site_placement,
            self.create_axis2placement_3d([0., 0., 0.])
        )

        # Create building
        self.building = self.ifc.createIfcBuilding(
            create_guid(),
            self.owner_history,
            "Building",
            None,  # Description
            None,  # ObjectType
            building_placement,
            None,  # Representation
            None,  # LongName
            "ELEMENT",  # CompositionType
            None, None, None  # ElevationOfRefHeight, ElevationOfTerrain, BuildingAddress
        )

        # Create storey placement
        storey_placement_rel = self.create_axis2placement_3d([0., 0., 0.])
        storey_local_placement = self.ifc.createIfcLocalPlacement(
            building_placement,
            storey_placement_rel
        )

        # Create storey
        self.storey = self.ifc.createIfcBuildingStorey(
            create_guid(),
            self.owner_history,
            "Ground Floor",
            None,  # Description
            None,  # ObjectType
            storey_local_placement,
            None,  # Representation
            None,  # LongName
            "ELEMENT",  # CompositionType
            0.0  # Elevation
        )

        # Create spatial relationships
        self.ifc.createIfcRelAggregates(
            create_guid(),
            self.owner_history,
            "ProjectContainer",
            None,
            self.project,
            [self.site]
        )

        self.ifc.createIfcRelAggregates(
            create_guid(),
            self.owner_history,
            "SiteContainer",
            None,
            self.site,
            [self.building]
        )

        self.ifc.createIfcRelAggregates(
            create_guid(),
            self.owner_history,
            "BuildingContainer",
            None,
            self.building,
            [self.storey]
        )

    def _create_units(self):
        """Create SI units for the IFC file (required for Revit)."""
        # Length unit: meters
        length_unit = self.ifc.createIfcSIUnit(
            None,  # Dimensions
            "LENGTHUNIT",
            None,  # Prefix (None = base unit, i.e., meters)
            "METRE"
        )

        # Area unit: square meters
        area_unit = self.ifc.createIfcSIUnit(
            None,
            "AREAUNIT",
            None,
            "SQUARE_METRE"
        )

        # Volume unit: cubic meters
        volume_unit = self.ifc.createIfcSIUnit(
            None,
            "VOLUMEUNIT",
            None,
            "CUBIC_METRE"
        )

        # Plane angle unit: radians
        plane_angle_unit = self.ifc.createIfcSIUnit(
            None,
            "PLANEANGLEUNIT",
            None,
            "RADIAN"
        )

        # Create unit assignment
        units = self.ifc.createIfcUnitAssignment([
            length_unit,
            area_unit,
            volume_unit,
            plane_angle_unit
        ])

        return units

    def create_simple_room(self, name: str, length: float, width: float, height: float = 2.7,
                          x_offset: float = 0.0, y_offset: float = 0.0):
        """
        Create a simple rectangular room with walls.

        Args:
            name: Name of the room (e.g., "Bedroom 1")
            length: Length of the room in meters
            width: Width of the room in meters
            height: Height of the room in meters (default 2.7m)
            x_offset: X position offset in meters
            y_offset: Y position offset in meters

        Returns:
            The created IfcSpace object
        """
        create_guid = lambda: ifcopenshell.guid.compress(uuid.uuid4().hex)

        # Create space placement
        space_placement = self.ifc.createIfcLocalPlacement(
            self.storey.ObjectPlacement,
            self.create_axis2placement_3d([x_offset, y_offset, 0.0])
        )

        # Create space object (IFC2X3 compatible)
        space = self.ifc.createIfcSpace(
            create_guid(),
            self.owner_history,
            name,
            None,  # Description
            None,  # ObjectType
            space_placement,
            None,  # Representation
            None,  # LongName
            "ELEMENT",  # CompositionType
            "INTERNAL"  # InteriorOrExteriorSpace (IFC2X3)
        )

        # Assign space to storey
        self.ifc.createIfcRelContainedInSpatialStructure(
            create_guid(),
            self.owner_history,
            f"SpaceContainer_{name}",
            None,
            [space],
            self.storey
        )

        # Wall thickness
        wall_thickness = 0.2  # 20cm

        # Create four walls for the room
        walls = []

        # Wall data: (name, start_x, start_y, end_x, end_y)
        wall_coords = [
            (f"{name} - South Wall", x_offset, y_offset, x_offset + length, y_offset),
            (f"{name} - East Wall", x_offset + length, y_offset, x_offset + length, y_offset + width),
            (f"{name} - North Wall", x_offset + length, y_offset + width, x_offset, y_offset + width),
            (f"{name} - West Wall", x_offset, y_offset + width, x_offset, y_offset)
        ]

        for wall_name, x1, y1, x2, y2 in wall_coords:
            wall = self.create_wall(wall_name, x1, y1, x2, y2, height, wall_thickness)
            walls.append(wall)

        return space
    
    def create_wall(self, name: str, x1: float, y1: float, x2: float, y2: float,
                   height: float = 2.7, thickness: float = 0.2):
        """
        Create a wall between two points using proper IFC conventions.

        Args:
            name: Wall name
            x1, y1: Start coordinates (wall centerline)
            x2, y2: End coordinates (wall centerline)
            height: Wall height in meters
            thickness: Wall thickness in meters

        Returns:
            The created IfcWall object
        """
        create_guid = lambda: ifcopenshell.guid.compress(uuid.uuid4().hex)

        # Calculate wall geometry
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx**2 + dy**2)

        if length < 1e-6:
            length = 1e-6
            dx, dy = 1.0, 0.0
        else:
            dx, dy = dx / length, dy / length

        # Wall placement - position at start point, rotated to wall direction
        wall_placement_3d = self.create_axis2placement_3d(
            [x1, y1, 0.0],       # Location at wall start
            [0.0, 0.0, 1.0],     # Z axis up
            [dx, dy, 0.0]        # X axis along wall direction
        )
        wall_local_placement = self.ifc.createIfcLocalPlacement(
            self.storey.ObjectPlacement,
            wall_placement_3d
        )

        # Create wall element (IFC2X3 compatible)
        wall = self.ifc.createIfcWallStandardCase(
            create_guid(),
            self.owner_history,
            name,
            None,  # Description
            None,  # ObjectType
            wall_local_placement,
            None,  # Representation (set below)
            None   # Tag
        )

        # Perpendicular direction (for thickness)
        half_t = thickness / 2.0

        # Create polygon profile points (wall cross-section in XY plane at origin)
        points = [
            self.ifc.createIfcCartesianPoint((0.0, -half_t)),
            self.ifc.createIfcCartesianPoint((length, -half_t)),
            self.ifc.createIfcCartesianPoint((length, half_t)),
            self.ifc.createIfcCartesianPoint((0.0, half_t)),
        ]

        # Create closed polyline
        polyline = self.ifc.createIfcPolyline(points + [points[0]])

        # Create arbitrary closed profile
        profile = self.ifc.createIfcArbitraryClosedProfileDef(
            "AREA",
            f"{name}_Profile",
            polyline
        )

        # Extrusion placement at origin
        extrusion_placement = self.create_axis2placement_3d(
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 0.0]
        )

        # Create extruded solid
        dir_vec = self.ifc.createIfcDirection((0.0, 0.0, 1.0))
        extruded_solid = self.ifc.createIfcExtrudedAreaSolid(
            profile,
            extrusion_placement,
            dir_vec,
            height
        )

        # Create shape representation using the body subcontext
        context = self.body_context if hasattr(self, 'body_context') else self.geom_context
        shape_rep = self.ifc.createIfcShapeRepresentation(
            context,
            "Body",
            "SweptSolid",
            [extruded_solid]
        )

        # Create product definition shape
        product_shape = self.ifc.createIfcProductDefinitionShape(
            None,
            None,
            [shape_rep]
        )
        wall.Representation = product_shape

        # Assign wall to storey
        self.ifc.createIfcRelContainedInSpatialStructure(
            create_guid(),
            self.owner_history,
            f"WallContainer_{name}",
            None,
            [wall],
            self.storey
        )

        return wall

    def get_geometric_context(self):
        """
        Get or create the geometric representation context.

        Returns:
            IfcGeometricRepresentationContext
        """
        if self.geom_context is None:
            raise RuntimeError(
                "Geometric context not initialized. "
                "Call create_project_structure() first."
            )
        return self.geom_context

    def create_axis2placement_3d(self, location, axis=None, ref_direction=None):
        """
        Create a 3D coordinate system (IfcAxis2Placement3D).

        Args:
            location: [x, y, z] coordinates
            axis: [x, y, z] Z-axis direction (default [0, 0, 1])
            ref_direction: [x, y, z] X-axis direction (default [1, 0, 0])

        Returns:
            IfcAxis2Placement3D
        """
        point = self.ifc.createIfcCartesianPoint([float(x) for x in location])
        axis_default = [0., 0., 1.]
        ref_default = [1., 0., 0.]
        z_axis = self.ifc.createIfcDirection([float(x) for x in (axis or axis_default)])
        x_axis = self.ifc.createIfcDirection([float(x) for x in (ref_direction or ref_default)])
        return self.ifc.createIfcAxis2Placement3D(point, z_axis, x_axis)

    def create_axis2placement_2d(self, location, ref_direction=None):
        """
        Create a 2D coordinate system (IfcAxis2Placement2D).

        Args:
            location: [x, y] coordinates
            ref_direction: [x, y] X-axis direction (default [1, 0])

        Returns:
            IfcAxis2Placement2D
        """
        point = self.ifc.createIfcCartesianPoint([float(x) for x in location])
        if ref_direction:
            direction = self.ifc.createIfcDirection([float(x) for x in ref_direction])
            return self.ifc.createIfcAxis2Placement2D(point, direction)
        else:
            return self.ifc.createIfcAxis2Placement2D(point)

    def create_rectangle_profile(self, width, height, name="RectangleProfile"):
        """
        Create a rectangular profile for extrusion.

        Args:
            width: Profile width (X dimension)
            height: Profile height (Y dimension)
            name: Profile name

        Returns:
            IfcRectangleProfileDef
        """
        position = self.create_axis2placement_2d([0., 0.])
        return self.ifc.createIfcRectangleProfileDef(
            "AREA",
            name,
            position,
            width,
            height
        )

    def create_extruded_solid(self, profile, position, direction, depth):
        """
        Create a 3D solid by extruding a profile.

        Args:
            profile: IfcProfileDef to extrude
            position: IfcAxis2Placement3D for extrusion origin
            direction: [x, y, z] extrusion direction
            depth: Extrusion depth

        Returns:
            IfcExtrudedAreaSolid
        """
        dir_vec = self.ifc.createIfcDirection([float(x) for x in direction])
        return self.ifc.createIfcExtrudedAreaSolid(profile, position, dir_vec, depth)

    def create_shape_representation(self, items, representation_type="SweptSolid"):
        """
        Create a shape representation containing geometric items.

        Args:
            items: List of geometric items (e.g., IfcExtrudedAreaSolid)
            representation_type: Type of representation (default "SweptSolid")

        Returns:
            IfcShapeRepresentation
        """
        context = self.get_geometric_context()
        return self.ifc.createIfcShapeRepresentation(
            context,
            "Body",
            representation_type,
            items
        )

    def create_local_placement(self, relative_placement, placement_rel_to=None):
        """
        Create a local placement for positioning elements.

        Args:
            relative_placement: IfcAxis2Placement3D for position/orientation
            placement_rel_to: Parent placement (default: storey placement)

        Returns:
            IfcLocalPlacement
        """
        if placement_rel_to is None:
            placement_rel_to = self.storey.ObjectPlacement
        return self.ifc.createIfcLocalPlacement(
            placement_rel_to,
            relative_placement
        )

    def calculate_wall_geometry(self, x1, y1, x2, y2, thickness):
        """
        Calculate wall geometry parameters.

        Args:
            x1, y1: Start point coordinates
            x2, y2: End point coordinates
            thickness: Wall thickness

        Returns:
            Dictionary with length, angle, center, x_direction, y_direction
        """
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx**2 + dy**2)

        # Avoid division by zero
        if length < 1e-6:
            length = 1e-6

        # Calculate direction vectors
        x_direction = [dx / length, dy / length, 0.0]
        y_direction = [-dy / length, dx / length, 0.0]

        # Calculate center point
        center = [(x1 + x2) / 2.0, (y1 + y2) / 2.0, 0.0]

        # Calculate angle
        angle = math.atan2(dy, dx)

        return {
            "length": length,
            "angle": angle,
            "center": center,
            "x_direction": x_direction,
            "y_direction": y_direction
        }

    def generate_from_spec(self, spec: dict, output_path: str = None) -> str:
        """
        Generate IFC file from JSON specification.
        
        Args:
            spec: JSON specification dictionary
            output_path: Output path for IFC file (optional)
            
        Returns:
            Path to the generated IFC file
        """
        # Validate spec
        if "status" in spec and spec["status"] == "invalid_json":
            raise ValueError("Cannot generate BIM from invalid specification")
        
        # Create project structure
        project_name = spec.get("project_name", "AI Generated House")
        self.create_project_structure(project_name)
        
        # Extract room information (handle both old and new spec formats)
        # New format: {"metadata": {"bedrooms": 3, ...}, "rooms": [...]}
        # Old format: {"bedrooms": 3, "bathrooms": 2, ...}
        metadata = spec.get("metadata", spec)  # Fallback to spec itself if no metadata key
        num_bedrooms = metadata.get("bedrooms", 0)
        num_bathrooms = metadata.get("bathrooms", 0)

        # For kitchen, living room, etc., check rooms list if available
        rooms_list = spec.get("rooms", [])
        has_kitchen = metadata.get("kitchen", False) or any(r.get("type") == "kitchen" for r in rooms_list)
        has_living_room = metadata.get("living_room", False) or any(r.get("type") == "living_room" for r in rooms_list)
        has_dining_room = metadata.get("dining_room", False) or any(r.get("type") == "dining_room" for r in rooms_list)
        has_study = metadata.get("study", False) or any(r.get("type") == "study" for r in rooms_list)
        
        # Use rule-based layout optimizer for intelligent room placement
        print("Optimizing room layout...")
        optimizer = RuleBasedLayoutOptimizer()
        rooms = optimizer.optimize_layout(metadata)

        print(f"Generated layout with {len(rooms)} rooms")

        # Create rooms with optimized positions
        for room in rooms:
            self.create_simple_room(
                room.name,
                room.width,
                room.height,
                x_offset=room.x,
                y_offset=room.y
            )
            print(f"  Created {room.name}: {room.width}x{room.height}m at ({room.x:.1f}, {room.y:.1f})")
        
        # Save IFC file
        if output_path is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(__file__).parent.parent / "output" / f"building_{timestamp}.ifc"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.ifc.write(str(output_path))
        print(f"IFC file generated: {output_path}")
        
        return str(output_path)


def main():
    """Example usage of BIM generator."""
    # Example specification
    spec = {
        "project_name": "Modern Family Home",
        "bedrooms": 3,
        "bathrooms": 2,
        "kitchen": True,
        "living_room": True,
        "dining_room": True,
        "study": False,
        "total_area_sqm": 120,
        "style": "modern"
    }
    
    print("="*80)
    print("BIM GENERATION ENGINE DEMO")
    print("="*80)
    print("\nInput Specification:")
    print(json.dumps(spec, indent=2))
    
    # Generate BIM
    generator = BIMGenerator()
    output_file = generator.generate_from_spec(spec)
    
    print(f"\n[OK] IFC file created successfully!")
    print(f"  Location: {output_file}")
    print("\nYou can open this file in:")
    print("  - BlenderBIM")
    print("  - Revit (via IFC import)")
    print("  - FreeCAD")
    print("  - Any IFC viewer")
    print("="*80)


if __name__ == "__main__":
    main()
