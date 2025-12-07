"""
BIM Generation Engine using IfcOpenShell.
Converts JSON building specifications to IFC files.
"""

import json
import datetime
import uuid
from pathlib import Path
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.geom


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
        
        # Note: Full geometric representation would require creating
        # IfcExtrudedAreaSolid and other geometric entities.
        # For MVP, we're creating the IFC structure without detailed geometry.
        
        return wall
    
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
        
        # Simple room dimensions (can be improved with Layout Optimizer later)
        bedroom_size = (3.5, 3.0)  # 3.5m x 3m
        bathroom_size = (2.0, 2.5)  # 2m x 2.5m
        kitchen_size = (3.0, 4.0)   # 3m x 4m
        living_size = (5.0, 4.5)    # 5m x 4.5m
        dining_size = (3.5, 3.5)    # 3.5m x 3.5m
        study_size = (2.5, 3.0)     # 2.5m x 3m
        
        # Simple layout - arrange rooms in a grid
        x, y = 0.0, 0.0
        
        # Create bedrooms
        for i in range(num_bedrooms):
            self.create_simple_room(
                f"Bedroom {i+1}",
                bedroom_size[0],
                bedroom_size[1],
                x_offset=x,
                y_offset=y
            )
            x += bedroom_size[0] + 0.2  # Add spacing
        
        # Reset to next row
        x = 0.0
        y += bedroom_size[1] + 0.2
        
        # Create bathrooms
        for i in range(num_bathrooms):
            self.create_simple_room(
                f"Bathroom {i+1}",
                bathroom_size[0],
                bathroom_size[1],
                x_offset=x,
                y_offset=y
            )
            x += bathroom_size[0] + 0.2
        
        # Create living room
        if has_living_room:
            x = 0.0
            y += bathroom_size[1] + 0.2
            self.create_simple_room(
                "Living Room",
                living_size[0],
                living_size[1],
                x_offset=x,
                y_offset=y
            )
            x += living_size[0] + 0.2
        
        # Create kitchen
        if has_kitchen:
            if not has_living_room:
                x = 0.0
                y += bathroom_size[1] + 0.2
            self.create_simple_room(
                "Kitchen",
                kitchen_size[0],
                kitchen_size[1],
                x_offset=x,
                y_offset=y
            )
        
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
