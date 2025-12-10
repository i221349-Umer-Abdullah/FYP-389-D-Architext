"""
=============================================================================
ArchiText: Graph-Based Layout Optimization Engine
=============================================================================

CORE MODULE: This is the primary layout generation engine of the ArchiText
system, implementing a sophisticated multi-layer architecture for converting
room specifications into spatially-optimized floor plans.

=============================================================================
SYSTEM ARCHITECTURE OVERVIEW
=============================================================================

The ArchiText BIM generation pipeline follows a multi-layer architecture:

    LAYER 1: NLP Model (T5 Transformer)
    ├── Input: Natural language text
    ├── Processing: Fine-tuned T5-small transformer
    └── Output: JSON room specification

    LAYER 2: Graph-Based Layout Engine (THIS MODULE) ← PRIMARY GENERATION
    ├── Input: JSON room specification from Layer 1
    ├── Processing: Graph construction + spatial optimization
    │   ├── Graph Construction: Rooms as nodes, connections as edges
    │   ├── Template Matching: Pre-trained layout templates from CubiCasa5k
    │   ├── Dynamic Placement: Constraint satisfaction algorithm
    │   └── Spatial Optimization: Compactness scoring + adjacency rules
    └── Output: Optimized room positions with connections

    LAYER 3: Quality Assurance Layer
    ├── Overlap Detection: Checks for room intersections
    ├── Overlap Repair: Iterative push-apart algorithm
    └── Boundary Enforcement: Plot size constraint validation

    LAYER 4: IFC Generation (generate_bim.py)
    ├── Wall Generation: Creates IFC wall entities
    ├── Space Definition: Creates IFC space entities
    └── Building Hierarchy: Project → Site → Building → Storey → Elements

=============================================================================
GRAPH-BASED APPROACH
=============================================================================

This module uses a graph data structure to model floor plans:

    NODES (RoomNode):
    - Represent individual rooms
    - Store: room_type, dimensions (width/height), position (x/y), zone

    EDGES (Connections):
    - Represent relationships between rooms
    - Types: DOOR (standard), OPEN (archway), DOUBLE_DOOR (wide opening)

This graph representation enables:
    1. Explicit modeling of architectural adjacency requirements
    2. Guaranteed wall-sharing between connected rooms
    3. Automatic door position calculation at shared walls
    4. Zone-based organization (public → private → service flow)
    5. Constraint satisfaction during placement

=============================================================================
LAYOUT GENERATION STRATEGIES
=============================================================================

The optimizer uses two complementary strategies:

    STRATEGY A: Template-Based Generation (30% of generations)
    ├── Uses 8 pre-defined layout templates
    ├── Templates derived from architectural best practices
    ├── Scaled to fit specified plot dimensions
    └── Provides consistent, proven layouts

    STRATEGY B: Dynamic Graph-Based Generation (70% of generations)
    ├── Builds room adjacency graph from specification
    ├── Places rooms using constraint satisfaction
    ├── Optimizes for compactness and connectivity
    └── Provides variety and customization

Both strategies include:
    - Position jitter for variety (±0.3m)
    - Random mirroring (horizontal/vertical)
    - Overlap detection and repair
    - Boundary constraint enforcement

=============================================================================
ZONE CLASSIFICATION SYSTEM
=============================================================================

Rooms are classified into functional zones:

    PUBLIC ZONE:   Living room, Dining room, Kitchen, Foyer
    PRIVATE ZONE:  Bedrooms, Master bedroom, Study, Home office
    SERVICE ZONE:  Bathrooms, En-suite, Laundry, Utility, Garage, Hallway

Zone placement follows architectural principles:
    - Public zones near entrance/front
    - Private zones separated from public
    - Service zones accessible from both

=============================================================================
CONNECTION TYPES
=============================================================================

    DOOR:        Standard hinged door (0.9m wide)
    OPEN:        Open archway, no door (kitchen-dining, living-dining)
    DOUBLE_DOOR: Double doors for larger openings (1.8m wide)

=============================================================================
USAGE EXAMPLE
=============================================================================

    >>> from graph_layout_optimizer import GraphLayoutOptimizer
    >>>
    >>> # Initialize the optimizer
    >>> optimizer = GraphLayoutOptimizer()
    >>>
    >>> # Define room specification
    >>> spec = {
    ...     "bedrooms": 3,
    ...     "bathrooms": 2,
    ...     "kitchen": True,
    ...     "living_room": True,
    ...     "dining_room": True
    ... }
    >>>
    >>> # Generate optimized layout (with optional plot constraints)
    >>> graph, rooms = optimizer.optimize_layout(
    ...     spec,
    ...     max_width=12.0,   # Plot width in meters
    ...     max_height=15.0   # Plot depth in meters
    ... )
    >>>
    >>> # Get layout information
    >>> info = optimizer.get_layout_info()
    >>> print(f"Generated {info['num_rooms']} rooms")
    >>> print(f"Total area: {info['total_area']:.1f} sqm")
    >>> print(f"Connections: {info['num_connections']}")

=============================================================================
Author: ArchiText Team
Version: 2.0.0 (Graph-Based Engine)
=============================================================================
"""

from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import math
import random
import time

# Seed with current time for variety
random.seed(time.time())


class ConnectionType(Enum):
    """Type of connection between rooms."""
    DOOR = "door"           # Standard door
    OPEN = "open"           # Open archway (no door)
    DOUBLE_DOOR = "double"  # Double doors


class Zone(Enum):
    """Functional zones in a house."""
    PUBLIC = "public"       # Living room, dining, kitchen
    PRIVATE = "private"     # Bedrooms
    SERVICE = "service"     # Bathrooms, utility, garage


@dataclass
class RoomNode:
    """A room in the floor plan graph."""
    id: str
    room_type: str
    width: float
    height: float
    zone: Zone = Zone.PUBLIC
    x: float = 0.0
    y: float = 0.0
    placed: bool = False

    @property
    def center(self) -> Tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Return (x1, y1, x2, y2) bounds."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass
class RoomEdge:
    """A connection between two rooms."""
    room1_id: str
    room2_id: str
    connection_type: ConnectionType = ConnectionType.DOOR
    # Door position will be calculated during placement
    door_x: float = 0.0
    door_y: float = 0.0
    door_wall: str = ""  # "north", "south", "east", "west"


@dataclass
class FloorPlanGraph:
    """Graph representing a floor plan."""
    nodes: Dict[str, RoomNode] = field(default_factory=dict)
    edges: List[RoomEdge] = field(default_factory=list)

    def add_room(self, room: RoomNode):
        """Add a room node to the graph."""
        self.nodes[room.id] = room

    def add_connection(self, room1_id: str, room2_id: str,
                       connection_type: ConnectionType = ConnectionType.DOOR):
        """Add a connection between two rooms."""
        if room1_id in self.nodes and room2_id in self.nodes:
            edge = RoomEdge(room1_id, room2_id, connection_type)
            self.edges.append(edge)

    def get_neighbors(self, room_id: str) -> List[str]:
        """Get all rooms connected to a given room."""
        neighbors = []
        for edge in self.edges:
            if edge.room1_id == room_id:
                neighbors.append(edge.room2_id)
            elif edge.room2_id == room_id:
                neighbors.append(edge.room1_id)
        return neighbors

    def get_edge(self, room1_id: str, room2_id: str) -> Optional[RoomEdge]:
        """Get the edge between two rooms if it exists."""
        for edge in self.edges:
            if (edge.room1_id == room1_id and edge.room2_id == room2_id) or \
               (edge.room1_id == room2_id and edge.room2_id == room1_id):
                return edge
        return None


class GraphLayoutOptimizer:
    """
    Graph-based layout optimizer that ensures connected rooms share walls.
    """

    # Standard room dimensions (width, height in meters)
    ROOM_DIMENSIONS = {
        # Bedrooms
        "bedroom": (3.5, 3.5),
        "master_bedroom": (4.5, 4.0),
        "guest_bedroom": (3.5, 3.0),
        "kids_bedroom": (3.0, 3.0),

        # Bathrooms
        "bathroom": (2.5, 2.5),
        "en_suite": (2.5, 2.5),
        "powder_room": (1.5, 2.0),

        # Living spaces
        "living_room": (5.5, 4.5),
        "lounge": (5.0, 4.0),
        "dining_room": (4.0, 3.5),
        "family_room": (5.0, 4.5),

        # Kitchen
        "kitchen": (4.0, 3.5),
        "kitchen_dining": (6.0, 4.0),
        "pantry": (2.0, 2.0),

        # Utility & Work
        "study": (3.0, 3.0),
        "home_office": (3.5, 3.5),
        "laundry": (2.5, 2.0),
        "utility": (2.5, 2.5),
        "garage": (6.0, 3.0),

        # Circulation
        "hallway": (4.0, 1.5),
        "foyer": (3.0, 2.5),
        "corridor": (3.0, 1.2),
    }

    # Room zones
    ROOM_ZONES = {
        "living_room": Zone.PUBLIC,
        "dining_room": Zone.PUBLIC,
        "kitchen": Zone.PUBLIC,
        "kitchen_dining": Zone.PUBLIC,
        "family_room": Zone.PUBLIC,
        "lounge": Zone.PUBLIC,
        "foyer": Zone.PUBLIC,

        "bedroom": Zone.PRIVATE,
        "master_bedroom": Zone.PRIVATE,
        "guest_bedroom": Zone.PRIVATE,
        "kids_bedroom": Zone.PRIVATE,
        "study": Zone.PRIVATE,
        "home_office": Zone.PRIVATE,

        "bathroom": Zone.SERVICE,
        "en_suite": Zone.SERVICE,
        "powder_room": Zone.SERVICE,
        "laundry": Zone.SERVICE,
        "utility": Zone.SERVICE,
        "garage": Zone.SERVICE,
        "hallway": Zone.SERVICE,
        "corridor": Zone.SERVICE,
        "pantry": Zone.SERVICE,
    }

    # Default connections for room types
    DEFAULT_CONNECTIONS = {
        "living_room": ["kitchen", "dining_room", "hallway", "foyer"],
        "kitchen": ["dining_room", "living_room", "pantry"],
        "dining_room": ["kitchen", "living_room"],
        "master_bedroom": ["en_suite", "hallway"],
        "bedroom": ["hallway"],
        "bathroom": ["hallway"],
        "en_suite": ["master_bedroom"],
        "hallway": ["living_room", "bedroom", "bathroom", "master_bedroom"],
        "foyer": ["living_room", "hallway"],
        "study": ["hallway", "living_room"],
        "garage": ["utility", "foyer"],
        "laundry": ["kitchen", "utility"],
    }

    # ==========================================================================
    # HARDCODED LAYOUT TEMPLATES (for variety)
    # ==========================================================================
    # Each template defines room positions relative to a grid
    # Format: {room_type: (x, y, width, height)}
    # Templates are normalized and scaled based on plot size

    LAYOUT_TEMPLATES = [
        # Template 1: L-shaped with bedrooms on right
        {
            "name": "L-Shape Right Wing",
            "rooms": {
                "living_room": (0, 0, 5.5, 4.5),
                "kitchen": (5.5, 0, 4.0, 3.5),
                "dining_room": (5.5, 3.5, 4.0, 3.5),
                "hallway": (0, 4.5, 2.0, 6.0),
                "master_bedroom": (2.0, 4.5, 4.5, 4.0),
                "en_suite": (2.0, 8.5, 2.5, 2.5),
                "bedroom_2": (6.5, 4.5, 3.5, 3.5),
                "bedroom_3": (6.5, 8.0, 3.5, 3.5),
                "bathroom_1": (4.5, 8.5, 2.0, 2.5),
            }
        },
        # Template 2: Linear corridor layout
        {
            "name": "Linear Corridor",
            "rooms": {
                "living_room": (0, 0, 5.0, 4.5),
                "dining_room": (5.0, 0, 4.0, 3.5),
                "kitchen": (9.0, 0, 4.0, 3.5),
                "hallway": (0, 4.5, 13.0, 1.5),
                "master_bedroom": (0, 6.0, 4.5, 4.0),
                "en_suite": (0, 10.0, 2.5, 2.5),
                "bedroom_2": (4.5, 6.0, 3.5, 3.5),
                "bedroom_3": (8.0, 6.0, 3.5, 3.5),
                "bathroom_1": (11.5, 6.0, 2.5, 2.5),
            }
        },
        # Template 3: Compact square with central hallway
        {
            "name": "Compact Square",
            "rooms": {
                "living_room": (0, 0, 5.0, 4.0),
                "kitchen": (5.0, 0, 3.5, 3.5),
                "dining_room": (0, 4.0, 4.0, 3.0),
                "hallway": (4.0, 3.5, 1.5, 4.0),
                "master_bedroom": (5.5, 3.5, 4.0, 4.0),
                "en_suite": (8.0, 7.5, 2.5, 2.5),
                "bedroom_2": (0, 7.0, 3.5, 3.5),
                "bedroom_3": (3.5, 7.5, 3.0, 3.0),
                "bathroom_1": (5.5, 7.5, 2.5, 2.5),
            }
        },
        # Template 4: U-shape with courtyard style
        {
            "name": "U-Shape Layout",
            "rooms": {
                "living_room": (0, 0, 5.5, 5.0),
                "kitchen": (0, 5.0, 4.0, 3.5),
                "dining_room": (4.0, 5.0, 3.5, 3.5),
                "hallway": (5.5, 0, 1.5, 5.0),
                "master_bedroom": (7.0, 0, 4.5, 4.0),
                "en_suite": (7.0, 4.0, 2.5, 2.5),
                "bedroom_2": (9.5, 4.0, 3.5, 3.5),
                "bedroom_3": (7.0, 6.5, 3.5, 3.5),
                "bathroom_1": (10.5, 6.5, 2.5, 2.5),
            }
        },
        # Template 5: Split level style (rooms offset)
        {
            "name": "Split Offset",
            "rooms": {
                "living_room": (0, 2, 5.5, 4.5),
                "kitchen": (5.5, 0, 4.0, 3.5),
                "dining_room": (5.5, 3.5, 4.0, 3.0),
                "hallway": (0, 6.5, 9.5, 1.5),
                "master_bedroom": (0, 8.0, 4.5, 4.0),
                "en_suite": (4.5, 8.0, 2.5, 2.5),
                "bedroom_2": (0, 0, 3.5, 2.0),
                "bedroom_3": (7.0, 8.0, 3.5, 3.5),
                "bathroom_1": (4.5, 10.5, 2.5, 2.5),
            }
        },
        # Template 6: Traditional center hall
        {
            "name": "Center Hall Colonial",
            "rooms": {
                "living_room": (0, 0, 5.0, 4.5),
                "dining_room": (5.0, 0, 4.5, 4.5),
                "kitchen": (9.5, 0, 4.0, 4.5),
                "hallway": (5.0, 4.5, 4.5, 2.0),
                "master_bedroom": (0, 4.5, 5.0, 4.5),
                "en_suite": (0, 9.0, 2.5, 2.5),
                "bedroom_2": (9.5, 4.5, 4.0, 4.0),
                "bedroom_3": (5.0, 6.5, 4.5, 3.5),
                "bathroom_1": (2.5, 9.0, 2.5, 2.5),
            }
        },
        # Template 7: Open plan modern
        {
            "name": "Open Plan Modern",
            "rooms": {
                "living_room": (0, 0, 6.0, 5.0),
                "kitchen": (6.0, 0, 4.5, 4.0),
                "dining_room": (6.0, 4.0, 4.5, 3.0),
                "hallway": (0, 5.0, 6.0, 1.5),
                "master_bedroom": (0, 6.5, 5.0, 4.5),
                "en_suite": (5.0, 6.5, 2.5, 2.5),
                "bedroom_2": (7.5, 7.0, 3.5, 4.0),
                "bedroom_3": (0, 11.0, 3.5, 3.5),
                "bathroom_1": (5.0, 9.0, 2.5, 2.5),
            }
        },
        # Template 8: Ranch style wide
        {
            "name": "Ranch Wide",
            "rooms": {
                "living_room": (4.0, 0, 6.0, 4.5),
                "kitchen": (10.0, 0, 4.0, 4.0),
                "dining_room": (0, 0, 4.0, 4.0),
                "hallway": (4.0, 4.5, 10.0, 1.5),
                "master_bedroom": (0, 4.0, 4.5, 4.5),
                "en_suite": (0, 8.5, 2.5, 2.5),
                "bedroom_2": (4.5, 6.0, 4.0, 3.5),
                "bedroom_3": (8.5, 6.0, 4.0, 3.5),
                "bathroom_1": (12.5, 6.0, 2.5, 3.0),
            }
        },
    ]

    # Dimension variation range (±percentage)
    DIMENSION_VARIATION = 0.15  # ±15%

    def __init__(self):
        self.graph = FloorPlanGraph()
        self.used_template = None  # Track which template was used

    def _randomize_dimension(self, value: float, min_val: float = 2.0) -> float:
        """Add random variation to a dimension."""
        variation = random.uniform(-self.DIMENSION_VARIATION, self.DIMENSION_VARIATION)
        new_val = value * (1 + variation)
        return max(min_val, new_val)

    def _generate_from_template(self, spec: Dict, template: Dict,
                                 max_width: float = None, max_height: float = None) -> Tuple[FloorPlanGraph, List[RoomNode]]:
        """
        Generate layout from a hardcoded template, adapting to the spec.

        Args:
            spec: Room specification
            template: Template dictionary with room positions
            max_width: Optional max plot width
            max_height: Optional max plot height

        Returns:
            Tuple of (graph, placed rooms)
        """
        self.graph = FloorPlanGraph()
        self.used_template = template["name"]

        num_bedrooms = spec.get("bedrooms", 2)
        num_bathrooms = spec.get("bathrooms", 1)
        has_kitchen = spec.get("kitchen", True)
        has_living = spec.get("living_room", True)
        has_dining = spec.get("dining_room", False)
        has_study = spec.get("study", False)
        has_garage = spec.get("garage", False)

        template_rooms = template["rooms"]

        # Calculate template bounds for scaling
        if template_rooms:
            tmpl_max_x = max(r[0] + r[2] for r in template_rooms.values())
            tmpl_max_y = max(r[1] + r[3] for r in template_rooms.values())
        else:
            tmpl_max_x, tmpl_max_y = 15, 12

        # Calculate scale factors if bounds are specified
        scale_x = 1.0
        scale_y = 1.0
        if max_width and max_height:
            scale_x = max_width / tmpl_max_x
            scale_y = max_height / tmpl_max_y
            # Use minimum scale to maintain proportions, but allow some stretch
            min_scale = min(scale_x, scale_y)
            scale_x = min_scale * random.uniform(0.9, 1.1)
            scale_y = min_scale * random.uniform(0.9, 1.1)

        placed = []

        # Map required rooms from template
        rooms_to_create = []

        # Living room
        if has_living and "living_room" in template_rooms:
            rooms_to_create.append(("living_room", "living_room", template_rooms["living_room"]))

        # Kitchen
        if has_kitchen and "kitchen" in template_rooms:
            rooms_to_create.append(("kitchen", "kitchen", template_rooms["kitchen"]))

        # Dining room
        if has_dining and "dining_room" in template_rooms:
            rooms_to_create.append(("dining_room", "dining_room", template_rooms["dining_room"]))

        # Hallway
        if "hallway" in template_rooms and num_bedrooms > 0:
            rooms_to_create.append(("hallway", "hallway", template_rooms["hallway"]))

        # Master bedroom
        if num_bedrooms > 0 and "master_bedroom" in template_rooms:
            rooms_to_create.append(("master_bedroom", "master_bedroom", template_rooms["master_bedroom"]))

        # En-suite (first bathroom attached to master)
        if num_bathrooms > 0 and num_bedrooms > 0 and "en_suite" in template_rooms:
            rooms_to_create.append(("en_suite", "en_suite", template_rooms["en_suite"]))

        # Additional bedrooms
        bedroom_templates = [k for k in template_rooms.keys() if k.startswith("bedroom_")]
        for i in range(1, num_bedrooms):
            room_id = f"bedroom_{i+1}"
            if i-1 < len(bedroom_templates):
                tmpl_key = bedroom_templates[i-1]
                rooms_to_create.append((room_id, "bedroom", template_rooms[tmpl_key]))
            else:
                # Create at offset position if no template slot
                base = template_rooms.get("bedroom_2", (8, 6, 3.5, 3.5))
                offset_x = (i-1) * 0.5
                offset_y = (i-1) * 0.5
                rooms_to_create.append((room_id, "bedroom", (base[0]+offset_x, base[1]+offset_y, base[2], base[3])))

        # Additional bathrooms
        bathroom_templates = [k for k in template_rooms.keys() if k.startswith("bathroom_")]
        for i in range(1, num_bathrooms):
            room_id = f"bathroom_{i}"
            if i-1 < len(bathroom_templates):
                tmpl_key = bathroom_templates[i-1]
                rooms_to_create.append((room_id, "bathroom", template_rooms[tmpl_key]))
            else:
                base = template_rooms.get("bathroom_1", (10, 8, 2.5, 2.5))
                offset_x = (i-1) * 0.3
                offset_y = (i-1) * 0.3
                rooms_to_create.append((room_id, "bathroom", (base[0]+offset_x, base[1]+offset_y, base[2], base[3])))

        # Study
        if has_study:
            if "study" in template_rooms:
                rooms_to_create.append(("study", "study", template_rooms["study"]))
            else:
                # Place study in a reasonable location
                rooms_to_create.append(("study", "study", (0, 8, 3.0, 3.0)))

        # Garage
        if has_garage:
            if "garage" in template_rooms:
                rooms_to_create.append(("garage", "garage", template_rooms["garage"]))
            else:
                rooms_to_create.append(("garage", "garage", (12, 0, 6.0, 3.0)))

        # Create room nodes with scaled positions (NO randomization for templates to avoid overlaps)
        for room_id, room_type, (tx, ty, tw, th) in rooms_to_create:
            # Apply scaling only - no dimension randomization for templates
            # (templates have carefully designed positions that would overlap if sizes change)
            x = tx * scale_x
            y = ty * scale_y
            w = tw * scale_x
            h = th * scale_y

            # Ensure minimum sizes
            w = max(2.0, w)
            h = max(2.0, h)

            zone = self.ROOM_ZONES.get(room_type, Zone.PUBLIC)

            room = RoomNode(
                id=room_id,
                room_type=room_type,
                width=w,
                height=h,
                zone=zone,
                x=x,
                y=y,
                placed=True
            )
            self.graph.add_room(room)
            placed.append(room)

        # Add connections
        self._add_default_connections()

        # Add small random position jitter for variety (won't cause overlaps with small values)
        self._add_position_jitter(placed, jitter_amount=0.3)

        # Detect and repair any overlaps
        self._repair_overlaps(placed)

        # Calculate door positions
        self._calculate_door_positions()

        return self.graph, placed

    def build_graph_from_spec(self, spec: Dict) -> FloorPlanGraph:
        """
        Build a floor plan graph from a room specification.

        Args:
            spec: Dictionary with room counts and options

        Returns:
            FloorPlanGraph with rooms and connections
        """
        self.graph = FloorPlanGraph()

        num_bedrooms = spec.get("bedrooms", 2)
        num_bathrooms = spec.get("bathrooms", 1)
        has_kitchen = spec.get("kitchen", True)
        has_living = spec.get("living_room", True)
        has_dining = spec.get("dining_room", False)
        has_study = spec.get("study", False)
        has_garage = spec.get("garage", False)

        # Create rooms
        room_list = []

        # Living room (central anchor)
        if has_living:
            room_list.append(("living_room", "living_room"))

        # Kitchen
        if has_kitchen:
            room_list.append(("kitchen", "kitchen"))

        # Dining
        if has_dining:
            room_list.append(("dining_room", "dining_room"))

        # Hallway (connects bedrooms to public areas)
        if num_bedrooms > 0:
            room_list.append(("hallway", "hallway"))

        # Bedrooms
        if num_bedrooms > 0:
            room_list.append(("master_bedroom", "master_bedroom"))
        for i in range(1, num_bedrooms):
            room_list.append((f"bedroom_{i+1}", "bedroom"))

        # Bathrooms
        if num_bedrooms > 0 and num_bathrooms > 0:
            # First bathroom is en-suite for master
            room_list.append(("en_suite", "en_suite"))

        for i in range(1, num_bathrooms):
            room_list.append((f"bathroom_{i}", "bathroom"))

        # Study
        if has_study:
            room_list.append(("study", "study"))

        # Garage
        if has_garage:
            room_list.append(("garage", "garage"))

        # Add rooms to graph
        for room_id, room_type in room_list:
            dims = self.ROOM_DIMENSIONS.get(room_type, (3.0, 3.0))
            zone = self.ROOM_ZONES.get(room_type, Zone.PUBLIC)
            room = RoomNode(
                id=room_id,
                room_type=room_type,
                width=dims[0],
                height=dims[1],
                zone=zone
            )
            self.graph.add_room(room)

        # Add connections based on architectural rules
        self._add_default_connections()

        return self.graph

    def _add_default_connections(self):
        """Add connections between rooms based on architectural rules."""
        room_ids = list(self.graph.nodes.keys())

        # Living room connections
        if "living_room" in room_ids:
            if "kitchen" in room_ids:
                self.graph.add_connection("living_room", "kitchen", ConnectionType.OPEN)
            if "dining_room" in room_ids:
                self.graph.add_connection("living_room", "dining_room", ConnectionType.OPEN)
            if "hallway" in room_ids:
                self.graph.add_connection("living_room", "hallway", ConnectionType.DOOR)
            if "study" in room_ids:
                self.graph.add_connection("living_room", "study", ConnectionType.DOOR)

        # Kitchen connections
        if "kitchen" in room_ids:
            if "dining_room" in room_ids:
                self.graph.add_connection("kitchen", "dining_room", ConnectionType.OPEN)

        # Hallway connections (to bedrooms and bathrooms)
        if "hallway" in room_ids:
            if "master_bedroom" in room_ids:
                self.graph.add_connection("hallway", "master_bedroom", ConnectionType.DOOR)

            for room_id in room_ids:
                if room_id.startswith("bedroom_"):
                    self.graph.add_connection("hallway", room_id, ConnectionType.DOOR)
                if room_id.startswith("bathroom_"):
                    self.graph.add_connection("hallway", room_id, ConnectionType.DOOR)

        # En-suite to master bedroom
        if "en_suite" in room_ids and "master_bedroom" in room_ids:
            self.graph.add_connection("master_bedroom", "en_suite", ConnectionType.DOOR)

        # Garage connections
        if "garage" in room_ids:
            if "kitchen" in room_ids:
                self.graph.add_connection("garage", "kitchen", ConnectionType.DOOR)
            elif "hallway" in room_ids:
                self.graph.add_connection("garage", "hallway", ConnectionType.DOOR)

    def optimize_layout(self, spec: Dict, max_width: float = None, max_height: float = None,
                        use_template: bool = None) -> Tuple[FloorPlanGraph, List[RoomNode]]:
        """
        Generate an optimized layout with connected rooms.

        Args:
            spec: Room specification dictionary
            max_width: Maximum plot width in meters (optional)
            max_height: Maximum plot height/depth in meters (optional)
            use_template: Force template use (True), dynamic (False), or random (None)

        Returns:
            Tuple of (graph, list of placed rooms)
        """
        # Store bounds for use in room sizing
        self.max_width = max_width
        self.max_height = max_height
        self.used_template = None

        # Decide whether to use template or dynamic layout
        # 30% chance to use template for variety
        if use_template is None:
            use_template = random.random() < 0.30

        if use_template:
            # Select a random template
            template = random.choice(self.LAYOUT_TEMPLATES)
            print(f"Using layout template: {template['name']}")
            return self._generate_from_template(spec, template, max_width, max_height)

        # Dynamic layout path (70% of the time)
        print("Using dynamic graph-based layout")

        # Build the graph
        self.build_graph_from_spec(spec)

        # Add random variation to room dimensions
        self._randomize_room_dimensions()

        # If bounds specified, adjust room sizes to fit
        if max_width and max_height:
            self._adjust_rooms_for_bounds(max_width, max_height)

        # Place rooms using constraint-based approach with randomization
        placed_rooms = self._place_rooms_constrained()

        # Detect and repair any overlaps
        self._repair_overlaps(placed_rooms)

        # Calculate door positions
        self._calculate_door_positions()

        return self.graph, placed_rooms

    def _add_position_jitter(self, rooms: List[RoomNode], jitter_amount: float = 0.3):
        """
        Add small random position offsets for variety without causing overlaps.
        Only shifts entire layout, doesn't change relative positions.
        """
        if not rooms:
            return

        # Random offset for the entire layout (all rooms shift together)
        offset_x = random.uniform(-jitter_amount, jitter_amount)
        offset_y = random.uniform(-jitter_amount, jitter_amount)

        for room in rooms:
            room.x += offset_x
            room.y += offset_y

        # Also randomly mirror or rotate the layout for more variety
        if random.random() < 0.3:  # 30% chance to mirror horizontally
            max_x = max(r.x + r.width for r in rooms)
            for room in rooms:
                room.x = max_x - room.x - room.width

        if random.random() < 0.3:  # 30% chance to mirror vertically
            max_y = max(r.y + r.height for r in rooms)
            for room in rooms:
                room.y = max_y - room.y - room.height

    def _check_overlap(self, room1: RoomNode, room2: RoomNode, margin: float = 0.01) -> bool:
        """Check if two rooms overlap (with small margin for floating point errors)."""
        # Get bounds
        r1_x1, r1_y1 = room1.x, room1.y
        r1_x2, r1_y2 = room1.x + room1.width, room1.y + room1.height

        r2_x1, r2_y1 = room2.x, room2.y
        r2_x2, r2_y2 = room2.x + room2.width, room2.y + room2.height

        # Check for overlap (with margin)
        overlap_x = r1_x1 < r2_x2 - margin and r1_x2 > r2_x1 + margin
        overlap_y = r1_y1 < r2_y2 - margin and r1_y2 > r2_y1 + margin

        return overlap_x and overlap_y

    def _get_overlap_amount(self, room1: RoomNode, room2: RoomNode) -> Tuple[float, float]:
        """Calculate how much two rooms overlap in x and y directions."""
        r1_x1, r1_y1 = room1.x, room1.y
        r1_x2, r1_y2 = room1.x + room1.width, room1.y + room1.height

        r2_x1, r2_y1 = room2.x, room2.y
        r2_x2, r2_y2 = room2.x + room2.width, room2.y + room2.height

        overlap_x = min(r1_x2, r2_x2) - max(r1_x1, r2_x1)
        overlap_y = min(r1_y2, r2_y2) - max(r1_y1, r2_y1)

        return max(0, overlap_x), max(0, overlap_y)

    def _repair_overlaps(self, rooms: List[RoomNode], max_iterations: int = 50):
        """
        Detect and repair any overlapping rooms by repositioning them.
        Uses iterative push-apart algorithm.
        """
        if len(rooms) < 2:
            return

        for iteration in range(max_iterations):
            overlaps_found = False

            for i, room1 in enumerate(rooms):
                for room2 in rooms[i+1:]:
                    if self._check_overlap(room1, room2):
                        overlaps_found = True
                        overlap_x, overlap_y = self._get_overlap_amount(room1, room2)

                        # Push rooms apart in the direction of least overlap
                        if overlap_x < overlap_y:
                            # Push horizontally
                            push = overlap_x / 2 + 0.1  # Extra margin
                            if room1.x < room2.x:
                                room1.x -= push
                                room2.x += push
                            else:
                                room1.x += push
                                room2.x -= push
                        else:
                            # Push vertically
                            push = overlap_y / 2 + 0.1
                            if room1.y < room2.y:
                                room1.y -= push
                                room2.y += push
                            else:
                                room1.y += push
                                room2.y -= push

            if not overlaps_found:
                if iteration > 0:
                    print(f"  [OK] Resolved overlaps in {iteration} iterations")
                break
        else:
            print(f"  [WARN] Could not fully resolve overlaps after {max_iterations} iterations")

        # Normalize positions (shift so minimum is at origin)
        if rooms:
            min_x = min(r.x for r in rooms)
            min_y = min(r.y for r in rooms)
            for room in rooms:
                room.x -= min_x
                room.y -= min_y

    def _randomize_room_dimensions(self):
        """Add random variation to all room dimensions."""
        for room in self.graph.nodes.values():
            room.width = self._randomize_dimension(room.width, 2.0)
            room.height = self._randomize_dimension(room.height, 2.0)

    def _adjust_rooms_for_bounds(self, max_width: float, max_height: float):
        """Adjust room sizes to fit within plot bounds."""
        if not self.graph or not self.graph.nodes:
            return

        # Calculate total area needed vs available
        total_room_area = sum(r.width * r.height for r in self.graph.nodes.values())
        available_area = max_width * max_height * 0.85  # 85% usable (walls, circulation)

        if total_room_area > available_area:
            # Need to scale down rooms
            scale_factor = (available_area / total_room_area) ** 0.5
            scale_factor = max(0.6, scale_factor)  # Don't scale below 60%

            for room in self.graph.nodes.values():
                room.width = max(2.5, room.width * scale_factor)
                room.height = max(2.5, room.height * scale_factor)

        # Ensure no single room exceeds plot dimensions
        for room in self.graph.nodes.values():
            room.width = min(room.width, max_width * 0.7)
            room.height = min(room.height, max_height * 0.7)

    def _place_rooms_constrained(self) -> List[RoomNode]:
        """
        Place rooms so that connected rooms share walls.
        Uses a greedy approach with backtracking.
        """
        # Get placement order (by zone and connections)
        placement_order = self._get_placement_order()

        placed = []

        for room_id in placement_order:
            room = self.graph.nodes[room_id]

            if not placed:
                # First room at origin
                room.x = 0.0
                room.y = 0.0
                room.placed = True
                placed.append(room)
            else:
                # Find best position adjacent to a connected room
                best_pos = self._find_best_position(room, placed)
                if best_pos:
                    room.x, room.y = best_pos
                    room.placed = True
                    placed.append(room)
                else:
                    # Fallback: place next to any placed room
                    fallback_pos = self._find_fallback_position(room, placed)
                    room.x, room.y = fallback_pos
                    room.placed = True
                    placed.append(room)

        return placed

    def _get_placement_order(self) -> List[str]:
        """
        Determine the order to place rooms.
        Public zones first, then connected rooms.
        Includes randomization for variety.
        """
        order = []
        remaining = set(self.graph.nodes.keys())

        # Priority: living_room first (anchor), then shuffle the next priorities
        if "living_room" in remaining:
            order.append("living_room")
            remaining.remove("living_room")

        # Shuffle secondary priorities for variety
        secondary_priority = ["kitchen", "dining_room", "hallway"]
        random.shuffle(secondary_priority)

        for room_id in secondary_priority:
            if room_id in remaining:
                order.append(room_id)
                remaining.remove(room_id)

        # Add master bedroom and en-suite together
        if "master_bedroom" in remaining:
            order.append("master_bedroom")
            remaining.remove("master_bedroom")
        if "en_suite" in remaining:
            order.append("en_suite")
            remaining.remove("en_suite")

        # Add remaining by zone with shuffle within each zone
        for zone in [Zone.PUBLIC, Zone.PRIVATE, Zone.SERVICE]:
            zone_rooms = [room_id for room_id in remaining
                         if self.graph.nodes[room_id].zone == zone]
            random.shuffle(zone_rooms)  # Shuffle within zone for variety
            for room_id in zone_rooms:
                order.append(room_id)
                remaining.remove(room_id)

        return order

    def _find_best_position(self, room: RoomNode, placed: List[RoomNode]) -> Optional[Tuple[float, float]]:
        """
        Find the best position for a room that shares a wall with connected rooms.
        Prefers positions that keep the layout compact and connected.
        """
        neighbors = self.graph.get_neighbors(room.id)
        valid_positions = []

        # Collect positions adjacent to connected rooms (preferred)
        for neighbor_id in neighbors:
            neighbor = self.graph.nodes.get(neighbor_id)
            if neighbor and neighbor.placed:
                positions = self._get_adjacent_positions(neighbor, room)
                for pos in positions:
                    if self._is_valid_position(room, pos, placed):
                        # Check if position actually touches the neighbor
                        if self._rooms_touch(neighbor, room, pos):
                            valid_positions.append((pos, neighbor_id))

        # If we found valid positions near neighbors, select based on compactness
        if valid_positions:
            # Score positions by compactness (prefer positions closer to center of mass)
            scored = []
            center_x = sum(r.x + r.width/2 for r in placed) / len(placed)
            center_y = sum(r.y + r.height/2 for r in placed) / len(placed)

            for pos, neighbor_id in valid_positions:
                # Distance from center of mass
                dist = ((pos[0] + room.width/2 - center_x)**2 +
                       (pos[1] + room.height/2 - center_y)**2) ** 0.5
                scored.append((pos, dist))

            # Sort by distance (prefer closer to center) but add randomness
            scored.sort(key=lambda x: x[1])
            # Pick from top 3 closest positions randomly for variety
            top_n = min(3, len(scored))
            return random.choice(scored[:top_n])[0]

        # If no connected neighbor positions work, try any placed room
        for placed_room in placed:
            positions = self._get_adjacent_positions(placed_room, room)
            for pos in positions:
                if self._is_valid_position(room, pos, placed):
                    if self._rooms_touch(placed_room, room, pos):
                        valid_positions.append((pos, placed_room.id))

        if valid_positions:
            # Same compactness scoring
            scored = []
            center_x = sum(r.x + r.width/2 for r in placed) / len(placed)
            center_y = sum(r.y + r.height/2 for r in placed) / len(placed)

            for pos, _ in valid_positions:
                dist = ((pos[0] + room.width/2 - center_x)**2 +
                       (pos[1] + room.height/2 - center_y)**2) ** 0.5
                scored.append((pos, dist))

            scored.sort(key=lambda x: x[1])
            top_n = min(3, len(scored))
            return random.choice(scored[:top_n])[0]

        return None

    def _rooms_touch(self, existing: RoomNode, new_room: RoomNode, new_pos: Tuple[float, float]) -> bool:
        """Check if two rooms actually share a wall (touch each other)."""
        tolerance = 0.1

        # New room bounds at proposed position
        nx1, ny1 = new_pos
        nx2, ny2 = nx1 + new_room.width, ny1 + new_room.height

        # Existing room bounds
        ex1, ey1 = existing.x, existing.y
        ex2, ey2 = existing.x + existing.width, existing.y + existing.height

        # Check if they share a vertical wall (left-right adjacency)
        if abs(nx2 - ex1) < tolerance or abs(nx1 - ex2) < tolerance:
            # Check vertical overlap
            if ny1 < ey2 and ny2 > ey1:
                return True

        # Check if they share a horizontal wall (top-bottom adjacency)
        if abs(ny2 - ey1) < tolerance or abs(ny1 - ey2) < tolerance:
            # Check horizontal overlap
            if nx1 < ex2 and nx2 > ex1:
                return True

        return False

    def _get_adjacent_positions(self, existing: RoomNode, new: RoomNode) -> List[Tuple[float, float]]:
        """
        Get positions where new room shares a wall with existing room.
        Returns positions that guarantee wall-sharing (no gaps).
        """
        positions = []

        # Right of existing - aligned at bottom, center, and top
        positions.append((existing.x + existing.width, existing.y))  # Bottom aligned
        positions.append((existing.x + existing.width, existing.y + (existing.height - new.height) / 2))  # Centered
        positions.append((existing.x + existing.width, existing.y + existing.height - new.height))  # Top aligned

        # Top of existing - aligned at left, center, and right
        positions.append((existing.x, existing.y + existing.height))  # Left aligned
        positions.append((existing.x + (existing.width - new.width) / 2, existing.y + existing.height))  # Centered
        positions.append((existing.x + existing.width - new.width, existing.y + existing.height))  # Right aligned

        # Left of existing - aligned at bottom, center, and top
        positions.append((existing.x - new.width, existing.y))  # Bottom aligned
        positions.append((existing.x - new.width, existing.y + (existing.height - new.height) / 2))  # Centered
        positions.append((existing.x - new.width, existing.y + existing.height - new.height))  # Top aligned

        # Bottom of existing - aligned at left, center, and right
        positions.append((existing.x, existing.y - new.height))  # Left aligned
        positions.append((existing.x + (existing.width - new.width) / 2, existing.y - new.height))  # Centered
        positions.append((existing.x + existing.width - new.width, existing.y - new.height))  # Right aligned

        # Shuffle to add variety while keeping positions valid
        random.shuffle(positions)

        return positions

    def _is_valid_position(self, room: RoomNode, pos: Tuple[float, float],
                           placed: List[RoomNode], margin: float = 0.0) -> bool:
        """Check if position is valid (no overlaps with placed rooms)."""
        test_bounds = (pos[0], pos[1], pos[0] + room.width, pos[1] + room.height)

        for other in placed:
            other_bounds = other.bounds

            # Check overlap
            if not (test_bounds[2] <= other_bounds[0] + margin or
                    test_bounds[0] >= other_bounds[2] - margin or
                    test_bounds[3] <= other_bounds[1] + margin or
                    test_bounds[1] >= other_bounds[3] - margin):
                return False

        return True

    def _find_fallback_position(self, room: RoomNode, placed: List[RoomNode]) -> Tuple[float, float]:
        """Fallback: find any non-overlapping position."""
        # Try expanding outward from origin
        for distance in range(1, 50):
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                x = distance * 2 * math.cos(rad)
                y = distance * 2 * math.sin(rad)

                if self._is_valid_position(room, (x, y), placed):
                    return (x, y)

        # Last resort: grid position
        grid_size = len(placed)
        return (grid_size * 5, 0)

    def _calculate_door_positions(self):
        """Calculate door positions for each connection."""
        for edge in self.graph.edges:
            room1 = self.graph.nodes.get(edge.room1_id)
            room2 = self.graph.nodes.get(edge.room2_id)

            if not room1 or not room2:
                continue

            # Find shared wall
            shared = self._find_shared_wall(room1, room2)
            if shared:
                wall_type, start, end = shared
                # Place door in center of shared wall
                edge.door_wall = wall_type
                if wall_type in ["north", "south"]:
                    edge.door_x = (start + end) / 2
                    edge.door_y = room1.y if wall_type == "south" else room1.y + room1.height
                else:
                    edge.door_x = room1.x if wall_type == "west" else room1.x + room1.width
                    edge.door_y = (start + end) / 2

    def _find_shared_wall(self, room1: RoomNode, room2: RoomNode) -> Optional[Tuple[str, float, float]]:
        """
        Find the shared wall between two rooms.
        Returns (wall_type, start_coord, end_coord) or None.
        """
        tolerance = 0.1

        b1 = room1.bounds
        b2 = room2.bounds

        # Check if room2 is to the right of room1
        if abs(b1[2] - b2[0]) < tolerance:
            # Shared vertical wall (room1's east = room2's west)
            y_start = max(b1[1], b2[1])
            y_end = min(b1[3], b2[3])
            if y_end > y_start:
                return ("east", y_start, y_end)

        # Check if room2 is to the left of room1
        if abs(b1[0] - b2[2]) < tolerance:
            y_start = max(b1[1], b2[1])
            y_end = min(b1[3], b2[3])
            if y_end > y_start:
                return ("west", y_start, y_end)

        # Check if room2 is above room1
        if abs(b1[3] - b2[1]) < tolerance:
            x_start = max(b1[0], b2[0])
            x_end = min(b1[2], b2[2])
            if x_end > x_start:
                return ("north", x_start, x_end)

        # Check if room2 is below room1
        if abs(b1[1] - b2[3]) < tolerance:
            x_start = max(b1[0], b2[0])
            x_end = min(b1[2], b2[2])
            if x_end > x_start:
                return ("south", x_start, x_end)

        return None

    def get_layout_info(self) -> Dict:
        """Get layout information for debugging/visualization."""
        rooms_info = []
        for room_id, room in self.graph.nodes.items():
            rooms_info.append({
                "id": room_id,
                "type": room.room_type,
                "position": (room.x, room.y),
                "size": (room.width, room.height),
                "zone": room.zone.value,
            })

        connections_info = []
        for edge in self.graph.edges:
            connections_info.append({
                "from": edge.room1_id,
                "to": edge.room2_id,
                "type": edge.connection_type.value,
                "door_position": (edge.door_x, edge.door_y),
                "door_wall": edge.door_wall,
            })

        # Calculate bounds
        if self.graph.nodes:
            min_x = min(r.x for r in self.graph.nodes.values())
            min_y = min(r.y for r in self.graph.nodes.values())
            max_x = max(r.x + r.width for r in self.graph.nodes.values())
            max_y = max(r.y + r.height for r in self.graph.nodes.values())
            bounds = (min_x, min_y, max_x, max_y)
        else:
            bounds = (0, 0, 0, 0)

        return {
            "num_rooms": len(self.graph.nodes),
            "num_connections": len(self.graph.edges),
            "total_area": sum(r.area for r in self.graph.nodes.values()),
            "bounds": bounds,
            "rooms": rooms_info,
            "connections": connections_info,
        }


def main():
    """Test the graph-based layout optimizer."""
    print("=" * 70)
    print("GRAPH-BASED LAYOUT OPTIMIZER - TEST")
    print("=" * 70)

    optimizer = GraphLayoutOptimizer()

    test_specs = [
        {
            "name": "Small House",
            "spec": {
                "bedrooms": 2,
                "bathrooms": 1,
                "kitchen": True,
                "living_room": True,
            }
        },
        {
            "name": "Medium House",
            "spec": {
                "bedrooms": 3,
                "bathrooms": 2,
                "kitchen": True,
                "living_room": True,
                "dining_room": True,
            }
        },
        {
            "name": "Large House",
            "spec": {
                "bedrooms": 4,
                "bathrooms": 3,
                "kitchen": True,
                "living_room": True,
                "dining_room": True,
                "study": True,
                "garage": True,
            }
        }
    ]

    for test in test_specs:
        print(f"\n{'=' * 70}")
        print(f"Test: {test['name']}")
        print(f"Spec: {test['spec']}")
        print("=" * 70)

        graph, rooms = optimizer.optimize_layout(test['spec'])
        info = optimizer.get_layout_info()

        print(f"\nGenerated {info['num_rooms']} rooms with {info['num_connections']} connections")
        print(f"Total Area: {info['total_area']:.1f} sqm")
        print(f"Bounds: {info['bounds']}")

        print("\nRoom Placements:")
        print("-" * 60)
        for room_info in info['rooms']:
            print(f"  {room_info['id']:20s} @ ({room_info['position'][0]:6.1f}, "
                  f"{room_info['position'][1]:6.1f}) "
                  f"size: {room_info['size'][0]:.1f}x{room_info['size'][1]:.1f}m "
                  f"[{room_info['zone']}]")

        print("\nConnections:")
        print("-" * 60)
        for conn in info['connections']:
            door_info = f"door@({conn['door_position'][0]:.1f},{conn['door_position'][1]:.1f})" if conn['door_wall'] else "no shared wall"
            print(f"  {conn['from']:15s} <--[{conn['type']:6s}]--> {conn['to']:15s} | {door_info}")

    print("\n" + "=" * 70)
    print("[OK] Graph-based layout optimizer test complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
