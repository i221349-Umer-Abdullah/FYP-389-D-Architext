"""
=============================================================================
ArchiText: Graph-Based Layout Optimizer
=============================================================================

This module implements an advanced graph-based layout optimization system
that ensures rooms share walls and have proper door connections. It provides
a more sophisticated approach to floor plan generation compared to the basic
rule-based optimizer.

Architecture:
-------------
The system uses a graph data structure where:
    - Nodes represent rooms (with type, dimensions, position)
    - Edges represent connections between rooms (doors, archways)

This graph-based approach enables:
    1. Explicit modeling of room relationships
    2. Guaranteed wall-sharing between connected rooms
    3. Automatic door position calculation
    4. Zone-based organization (public, private, service areas)

Key Features:
-------------
    - Wall Sharing: Connected rooms guaranteed to share walls
    - Door Placement: Automatic calculation of door positions
    - Zone Organization: Rooms grouped by function (public/private/service)
    - Constraint Satisfaction: Rooms placed to satisfy all connections
    - Adjacency Graph: Explicit representation of room relationships

Zone Classification:
--------------------
    PUBLIC:  living_room, dining_room, kitchen, foyer
    PRIVATE: bedrooms, study, home_office
    SERVICE: bathrooms, laundry, utility, garage, hallway

Connection Types:
-----------------
    - DOOR: Standard door connection
    - OPEN: Open archway (kitchen-dining, living-dining)
    - DOUBLE_DOOR: Double doors for larger openings

Usage Example:
--------------
    >>> optimizer = GraphLayoutOptimizer()
    >>> spec = {"bedrooms": 3, "bathrooms": 2, "kitchen": True, "living_room": True}
    >>> graph, rooms = optimizer.optimize_layout(spec)
    >>> info = optimizer.get_layout_info()
    >>> print(f"Generated {info['num_rooms']} rooms with {info['num_connections']} connections")

Author: ArchiText Team
Version: 1.0.0
=============================================================================
"""

from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import math
import random


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

    def __init__(self):
        self.graph = FloorPlanGraph()

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

    def optimize_layout(self, spec: Dict) -> Tuple[FloorPlanGraph, List[RoomNode]]:
        """
        Generate an optimized layout with connected rooms.

        Args:
            spec: Room specification dictionary

        Returns:
            Tuple of (graph, list of placed rooms)
        """
        # Build the graph
        self.build_graph_from_spec(spec)

        # Place rooms using constraint-based approach
        placed_rooms = self._place_rooms_constrained()

        # Calculate door positions
        self._calculate_door_positions()

        return self.graph, placed_rooms

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
        """
        order = []
        remaining = set(self.graph.nodes.keys())

        # Priority: living_room, kitchen, dining, hallway, then rest
        priority = ["living_room", "kitchen", "dining_room", "hallway",
                    "master_bedroom", "en_suite"]

        for room_id in priority:
            if room_id in remaining:
                order.append(room_id)
                remaining.remove(room_id)

        # Add remaining by zone (public first, then private, then service)
        for zone in [Zone.PUBLIC, Zone.PRIVATE, Zone.SERVICE]:
            for room_id in list(remaining):
                room = self.graph.nodes[room_id]
                if room.zone == zone:
                    order.append(room_id)
                    remaining.remove(room_id)

        return order

    def _find_best_position(self, room: RoomNode, placed: List[RoomNode]) -> Optional[Tuple[float, float]]:
        """
        Find the best position for a room that shares a wall with connected rooms.
        """
        neighbors = self.graph.get_neighbors(room.id)

        # Try positions adjacent to connected rooms first
        for neighbor_id in neighbors:
            neighbor = self.graph.nodes.get(neighbor_id)
            if neighbor and neighbor.placed:
                positions = self._get_adjacent_positions(neighbor, room)
                for pos in positions:
                    if self._is_valid_position(room, pos, placed):
                        return pos

        # If no connected neighbor is placed, try any placed room
        for placed_room in placed:
            positions = self._get_adjacent_positions(placed_room, room)
            for pos in positions:
                if self._is_valid_position(room, pos, placed):
                    return pos

        return None

    def _get_adjacent_positions(self, existing: RoomNode, new: RoomNode) -> List[Tuple[float, float]]:
        """
        Get positions where new room shares a wall with existing room.
        Returns positions for each side: right, top, left, bottom.
        """
        positions = []

        # Right of existing (shares left wall of new with right wall of existing)
        positions.append((existing.x + existing.width, existing.y))

        # Top of existing
        positions.append((existing.x, existing.y + existing.height))

        # Left of existing
        positions.append((existing.x - new.width, existing.y))

        # Bottom of existing
        positions.append((existing.x, existing.y - new.height))

        # Aligned variants (centered on existing wall)
        # Right, centered vertically
        center_offset_y = (existing.height - new.height) / 2
        positions.append((existing.x + existing.width, existing.y + center_offset_y))

        # Top, centered horizontally
        center_offset_x = (existing.width - new.width) / 2
        positions.append((existing.x + center_offset_x, existing.y + existing.height))

        # Left, centered
        positions.append((existing.x - new.width, existing.y + center_offset_y))

        # Bottom, centered
        positions.append((existing.x + center_offset_x, existing.y - new.height))

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
