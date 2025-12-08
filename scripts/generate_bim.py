"""
BIM Generation Engine using IfcOpenShell.
Converts JSON building specifications to IFC files.
"""

import json
import datetime
import uuid
import math
from pathlib import Path
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.geom
from layout_optimizer_rules import RuleBasedLayoutOptimizer


class BIMGenerator:
    """Generate IFC BIM models from JSON specifications."""
    
    def __init__(self):
        """Initialize BIM generator."""
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
        # Create a new IFC file (IFC4 schema)
        self.ifc = ifcopenshell.file(schema="IFC4")
        
        # Create basic IFC entities manually for compatibility
        create_guid = lambda: ifcopenshell.guid.compress(uuid.uuid4().hex)
        
        # Create OwnerHistory
        person = self.ifc.createIfcPerson()
        person.GivenName = "AI"
        person.FamilyName = "Generator"
        
        org = self.ifc.createIfcOrganization()
        org.Name = "AI BIM System"
        
        person_org = self.ifc.createIfcPersonAndOrganization()
        person_org.ThePerson = person
        person_org.TheOrganization = org
        
        application = self.ifc.createIfcApplication()
        application.ApplicationDeveloper = org
        application.Version = "1.0"
        application.ApplicationFullName = "Text-to-BIM AI"
        application.ApplicationIdentifier = "TextToBIM"
        
        timestamp = int(datetime.datetime.now().timestamp())
        
        self.owner_history = self.ifc.createIfcOwnerHistory()
        self.owner_history.OwningUser = person_org
        self.owner_history.OwningApplication = application
        self.owner_history.CreationDate = timestamp
        
        # Create project
        self.project = self.ifc.createIfcProject(create_guid())
        self.project.OwnerHistory = self.owner_history
        self.project.Name = project_name
        
        # Create site
        self.site = self.ifc.createIfcSite(create_guid())
        self.site.OwnerHistory = self.owner_history
        self.site.Name = "Site"
        
        # Create building
        self.building = self.ifc.createIfcBuilding(create_guid())
        self.building.OwnerHistory = self.owner_history
        self.building.Name = "Building"
        
        # Create storey
        self.storey = self.ifc.createIfcBuildingStorey(create_guid())
        self.storey.OwnerHistory = self.owner_history
        self.storey.Name = "Ground Floor"
        self.storey.Elevation = 0.0
        
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

        # Create geometric representation context
        context_dim = 3
        precision = 1.0e-5
        self.geom_context = self.ifc.createIfcGeometricRepresentationContext(
            None,
            "Model",
            context_dim,
            precision,
            self.create_axis2placement_3d([0., 0., 0.]),
            None
        )

        # Create storey placement
        storey_placement = self.create_axis2placement_3d([0., 0., 0.])
        self.storey.ObjectPlacement = self.ifc.createIfcLocalPlacement(
            None,
            storey_placement
        )

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
        
        # Create space object
        space = self.ifc.createIfcSpace(create_guid())
        space.OwnerHistory = self.owner_history
        space.Name = name
        
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
        Create a wall between two points.
        
        Args:
            name: Wall name
            x1, y1: Start coordinates
            x2, y2: End coordinates
            height: Wall height in meters
            thickness: Wall thickness in meters
            
        Returns:
            The created IfcWall object
        """
        create_guid = lambda: ifcopenshell.guid.compress(uuid.uuid4().hex)
        
        # Create wall element
        wall = self.ifc.createIfcWall(create_guid())
        wall.OwnerHistory = self.owner_history
        wall.Name = name
        
        # Assign wall to storey
        self.ifc.createIfcRelContainedInSpatialStructure(
            create_guid(),
            self.owner_history,
            f"WallContainer_{name}",
            None,
            [wall],
            self.storey
        )

        # Calculate wall geometry
        geom = self.calculate_wall_geometry(x1, y1, x2, y2, thickness)

        # Create wall profile (rectangular cross-section)
        profile = self.create_rectangle_profile(
            thickness,
            geom["length"],
            f"{name}_Profile"
        )

        # Create extrusion placement
        extrusion_position = self.create_axis2placement_3d(
            [x1, y1, 0.],
            [0., 0., 1.],
            geom["x_direction"]
        )

        # Create extruded solid (extrude vertically)
        extruded_solid = self.create_extruded_solid(
            profile,
            extrusion_position,
            [0., 0., 1.],
            height
        )

        # Create shape representation
        shape_rep = self.create_shape_representation([extruded_solid])

        # Create product definition shape
        product_shape = self.ifc.createIfcProductDefinitionShape(
            None,
            None,
            [shape_rep]
        )

        # Assign shape to wall
        wall.Representation = product_shape

        # Create wall placement
        wall_placement = self.create_axis2placement_3d(
            geom["center"],
            [0., 0., 1.],
            geom["x_direction"]
        )
        wall.ObjectPlacement = self.create_local_placement(
            wall_placement,
            self.storey.ObjectPlacement
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
