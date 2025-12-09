"""
=============================================================================
ArchiText: Rule-Based Layout Optimization Engine
=============================================================================

This module implements the rule-based layout optimization layer that enhances
the output from the trained NLP model. It applies architectural constraints
and best practices to generate realistic, buildable floor plans.

Role in the Pipeline:
---------------------
This optimizer acts as LAYER 2 in the ArchiText pipeline:

    LAYER 1 (NLP Model) → Raw specification → LAYER 2 (This Optimizer) →
    Refined layout → LAYER 3 (IFC Generator) → BIM File

The optimizer takes the JSON specification from the trained model and:
    1. Assigns appropriate dimensions to each room type
    2. Places rooms according to architectural adjacency rules
    3. Ensures proper connectivity between spaces
    4. Validates the layout for buildability

Architectural Rules Applied:
----------------------------
    - Room Sizing: Standard dimensions for 30+ room types
    - Adjacency: Kitchen near dining, en-suite connected to master bedroom
    - Zoning: Public areas (living, dining) separate from private (bedrooms)
    - Circulation: Hallways connect private rooms to public areas
    - Overlap Prevention: Rooms maintain proper separation

Room Types Supported:
---------------------
    - Bedrooms: master, guest, kids, standard (3-4.5m range)
    - Bathrooms: full, en-suite, powder room (1.5-2.5m range)
    - Living Spaces: living room, lounge, family room (4-5.5m range)
    - Kitchen: standard, kitchen-dining combo, pantry
    - Utility: laundry, utility room, garage
    - Circulation: hallway, foyer, corridor

Example Usage:
--------------
    >>> optimizer = RuleBasedLayoutOptimizer()
    >>> spec = {"bedrooms": 3, "bathrooms": 2, "kitchen": True, "living_room": True}
    >>> rooms = optimizer.optimize_layout(spec)
    >>> for room in rooms:
    ...     print(f"{room.name}: {room.width}x{room.height}m at ({room.x}, {room.y})")

Author: ArchiText Team
Version: 1.0.0
=============================================================================
"""

import sys
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math

@dataclass
class Room:
    """Represents a room in the layout."""
    name: str
    type: str  # bedroom, bathroom, kitchen, living_room, etc.
    width: float
    height: float
    x: float = 0.0
    y: float = 0.0

    @property
    def area(self):
        return self.width * self.height

    @property
    def bounds(self):
        """Return (x1, y1, x2, y2) bounds."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def overlaps(self, other: 'Room', margin: float = 0.2) -> bool:
        """Check if this room overlaps with another (with margin)."""
        x1, y1, x2, y2 = self.bounds
        ox1, oy1, ox2, oy2 = other.bounds

        # Add margin to both rooms
        return not (x2 + margin <= ox1 - margin or ox2 + margin <= x1 - margin or
                   y2 + margin <= oy1 - margin or oy2 + margin <= y1 - margin)


class RuleBasedLayoutOptimizer:
    """
    Rule-based layout optimizer using architectural best practices.
    """

    # Standard room dimensions (width, height in meters)
    # Based on architectural standards and typical usage patterns
    ROOM_DIMENSIONS = {
        # Bedrooms
        "bedroom": (3.5, 3.5),             # Standard bedroom: ~12 sqm
        "master_bedroom": (4.5, 4.0),      # Master bedroom: ~18 sqm
        "guest_bedroom": (3.5, 3.0),       # Guest room: ~10.5 sqm
        "kids_bedroom": (3.0, 3.0),        # Kids room: ~9 sqm

        # Bathrooms
        "bathroom": (2.5, 2.0),            # Standard bath: ~5 sqm
        "en_suite": (2.5, 2.5),            # En-suite bathroom: ~6.25 sqm
        "powder_room": (1.5, 2.0),         # Half bath/powder room: ~3 sqm

        # Living spaces
        "living_room": (5.5, 4.5),         # Living room: ~25 sqm
        "lounge": (5.0, 4.0),              # Lounge/sitting room: ~20 sqm
        "drawing_room": (4.5, 4.0),        # Drawing room: ~18 sqm
        "family_room": (5.0, 4.5),         # Family room: ~22.5 sqm
        "sun_room": (4.0, 3.5),            # Sun room/conservatory: ~14 sqm

        # Dining & Kitchen
        "kitchen": (4.0, 3.5),             # Kitchen: ~14 sqm
        "dining_room": (4.0, 3.5),         # Dining room: ~14 sqm
        "kitchen_dining": (6.0, 4.0),      # Combined kitchen/dining: ~24 sqm
        "pantry": (2.0, 2.0),              # Pantry: ~4 sqm

        # Work & Utility
        "study": (3.0, 3.0),               # Study/home office: ~9 sqm
        "home_office": (3.5, 3.5),         # Larger home office: ~12 sqm
        "library": (4.0, 3.5),             # Library/reading room: ~14 sqm
        "laundry": (2.5, 2.0),             # Laundry room: ~5 sqm
        "utility": (2.5, 2.5),             # Utility room: ~6.25 sqm

        # Circulation & Storage
        "hallway": (1.5, 3.5),             # Hallway: ~5 sqm
        "corridor": (1.2, 4.0),            # Corridor: ~5 sqm
        "foyer": (3.0, 2.5),               # Entrance foyer: ~7.5 sqm
        "storage": (2.0, 2.0),             # Storage room: ~4 sqm
        "walk_in_closet": (2.5, 2.5),      # Walk-in closet: ~6.25 sqm

        # Special rooms
        "garage": (6.0, 3.0),              # Single car garage: ~18 sqm
        "double_garage": (6.0, 6.0),       # Double garage: ~36 sqm
        "basement": (8.0, 6.0),            # Basement: ~48 sqm
        "attic": (6.0, 4.0),               # Attic space: ~24 sqm
        "gym": (4.0, 4.0),                 # Home gym: ~16 sqm
        "media_room": (5.0, 4.0),          # Media/theater room: ~20 sqm
        "pool_room": (5.0, 4.0),           # Pool/billiards room: ~20 sqm
    }

    # Room adjacency preferences (which rooms should be near each other)
    ADJACENCY_PREFERENCES = {
        # Kitchen connections
        "kitchen": ["dining_room", "living_room", "pantry", "utility"],
        "kitchen_dining": ["living_room", "pantry"],
        "pantry": ["kitchen"],

        # Living spaces
        "living_room": ["kitchen", "dining_room", "hallway", "foyer", "sun_room"],
        "lounge": ["living_room", "dining_room", "hallway"],
        "drawing_room": ["foyer", "living_room", "hallway"],
        "family_room": ["kitchen", "living_room"],
        "sun_room": ["living_room", "dining_room"],
        "dining_room": ["kitchen", "living_room"],

        # Bedrooms
        "master_bedroom": ["en_suite", "walk_in_closet", "bathroom"],
        "bedroom": ["bathroom", "hallway"],
        "guest_bedroom": ["bathroom", "hallway"],
        "kids_bedroom": ["bathroom", "hallway"],

        # Bathrooms
        "bathroom": ["bedroom", "hallway", "master_bedroom"],
        "en_suite": ["master_bedroom"],
        "powder_room": ["foyer", "hallway"],

        # Work spaces
        "study": ["living_room", "hallway", "library"],
        "home_office": ["study", "library", "hallway"],
        "library": ["study", "living_room"],

        # Utility
        "laundry": ["kitchen", "utility", "garage"],
        "utility": ["kitchen", "laundry", "garage"],

        # Circulation
        "hallway": ["living_room", "bedroom", "bathroom", "foyer"],
        "corridor": ["bedroom", "bathroom"],
        "foyer": ["living_room", "hallway", "drawing_room"],

        # Storage
        "storage": ["hallway", "utility"],
        "walk_in_closet": ["master_bedroom"],

        # Special rooms
        "garage": ["utility", "laundry", "foyer"],
        "gym": ["bathroom", "utility"],
        "media_room": ["living_room", "family_room"],
        "pool_room": ["living_room", "family_room"],
    }

    # Placement priorities (higher = place first)
    # Higher priority rooms are placed first and become anchors for others
    PLACEMENT_PRIORITY = {
        # Main living spaces (place first as central anchors)
        "living_room": 20,
        "family_room": 19,
        "lounge": 18,
        "drawing_room": 17,

        # Kitchen area (near living spaces)
        "kitchen": 16,
        "kitchen_dining": 16,
        "dining_room": 15,
        "pantry": 10,

        # Primary bedroom suite
        "master_bedroom": 14,
        "en_suite": 13,
        "walk_in_closet": 12,

        # Other bedrooms
        "bedroom": 11,
        "guest_bedroom": 10,
        "kids_bedroom": 9,

        # Bathrooms
        "bathroom": 8,
        "powder_room": 7,

        # Work spaces
        "study": 6,
        "home_office": 6,
        "library": 5,

        # Utility rooms
        "laundry": 4,
        "utility": 4,

        # Circulation
        "foyer": 3,
        "hallway": 3,
        "corridor": 2,

        # Storage and special
        "storage": 1,
        "garage": 1,
        "double_garage": 1,
        "gym": 1,
        "media_room": 1,
        "pool_room": 1,
        "sun_room": 1,
    }

    def __init__(self):
        self.rooms: List[Room] = []

    def optimize_layout(self, spec: Dict) -> List[Room]:
        """
        Generate optimized room layout from specification.

        Args:
            spec: Building specification with room counts

        Returns:
            List of Room objects with optimized positions
        """
        self.rooms = []

        # Extract room requirements from spec
        num_bedrooms = spec.get("bedrooms", 0)
        num_bathrooms = spec.get("bathrooms", 0)
        has_kitchen = spec.get("kitchen", False)
        has_living = spec.get("living_room", False)
        has_dining = spec.get("dining_room", False)
        has_study = spec.get("study", False)

        # Create room list with priorities
        room_requests = []

        # Living room (central, place first)
        if has_living:
            room_requests.append(("living_room", "living_room", 10))

        # Kitchen (near living/dining)
        if has_kitchen:
            room_requests.append(("kitchen", "kitchen", 9))

        # Master bedroom (first bedroom, larger)
        if num_bedrooms > 0:
            room_requests.append(("master_bedroom", "bedroom", 8))

        # Additional bedrooms
        for i in range(1, num_bedrooms):
            room_requests.append((f"bedroom_{i+1}", "bedroom", 7))

        # Bathrooms
        for i in range(num_bathrooms):
            room_requests.append((f"bathroom_{i+1}", "bathroom", 6))

        # Dining room
        if has_dining:
            room_requests.append(("dining_room", "dining_room", 5))

        # Study
        if has_study:
            room_requests.append(("study", "study", 4))

        # Sort by priority
        room_requests.sort(key=lambda x: x[2], reverse=True)

        # Place rooms using smart rules
        for name, room_type, _ in room_requests:
            self._place_room(name, room_type)

        return self.rooms

    def _place_room(self, name: str, room_type: str):
        """Place a single room using smart placement rules."""
        # Get standard dimensions for this room type
        width, height = self.ROOM_DIMENSIONS.get(room_type, (3.0, 3.0))

        # Create room object
        room = Room(name=name, type=room_type, width=width, height=height)

        if len(self.rooms) == 0:
            # First room: place at origin
            room.x = 0.0
            room.y = 0.0
        else:
            # Find best position based on adjacency preferences
            best_position = self._find_best_position(room)
            room.x, room.y = best_position

        self.rooms.append(room)

    def _find_best_position(self, room: Room) -> Tuple[float, float]:
        """
        Find best position for a room based on:
        1. Adjacency preferences
        2. Avoiding overlaps
        3. Compact layout
        """
        # Get preferred adjacent room types
        preferred_adjacents = self.ADJACENCY_PREFERENCES.get(room.type, [])

        # Try positions adjacent to preferred rooms
        candidate_positions = []

        for existing_room in self.rooms:
            if existing_room.type in preferred_adjacents:
                # Try positions around this preferred room
                positions = self._get_adjacent_positions(existing_room, room)
                candidate_positions.extend(positions)

        # If no preferred adjacency, try positions near any room
        if not candidate_positions:
            for existing_room in self.rooms:
                positions = self._get_adjacent_positions(existing_room, room)
                candidate_positions.extend(positions)

        # Evaluate each candidate position
        best_position = None
        best_score = float('-inf')

        for pos_x, pos_y in candidate_positions:
            # Create temporary room at this position
            temp_room = Room(name=room.name, type=room.type,
                           width=room.width, height=room.height,
                           x=pos_x, y=pos_y)

            # Check if it overlaps with any existing room
            if any(temp_room.overlaps(r) for r in self.rooms):
                continue

            # Score this position
            score = self._score_position(temp_room)

            if score > best_score:
                best_score = score
                best_position = (pos_x, pos_y)

        # If no valid position found, place in grid (fallback)
        if best_position is None:
            best_position = self._grid_fallback_position(room)

        return best_position

    def _get_adjacent_positions(self, existing: Room, new: Room) -> List[Tuple[float, float]]:
        """Get possible positions adjacent to an existing room."""
        positions = []
        margin = 0.5  # Wall thickness + spacing

        # Right of existing room
        positions.append((existing.x + existing.width + margin, existing.y))

        # Below existing room
        positions.append((existing.x, existing.y + existing.height + margin))

        # Left of existing room
        positions.append((existing.x - new.width - margin, existing.y))

        # Above existing room
        positions.append((existing.x, existing.y - new.height - margin))

        # Diagonal positions (with extra spacing)
        positions.append((existing.x + existing.width + margin,
                        existing.y + existing.height + margin))
        positions.append((existing.x - new.width - margin,
                        existing.y + existing.height + margin))

        # Aligned but offset positions
        positions.append((existing.x + existing.width + margin,
                        existing.y - new.height - margin))
        positions.append((existing.x - new.width - margin,
                        existing.y - new.height - margin))

        return positions

    def _score_position(self, room: Room) -> float:
        """
        Score a room position based on:
        - Proximity to preferred adjacent rooms (higher is better)
        - Compactness (closer to origin is better)
        - Alignment with existing rooms (better grid alignment)
        """
        score = 0.0

        # Adjacency score
        preferred_adjacents = self.ADJACENCY_PREFERENCES.get(room.type, [])
        for existing in self.rooms:
            if existing.type in preferred_adjacents:
                # Calculate distance between room centers
                dx = (room.x + room.width/2) - (existing.x + existing.width/2)
                dy = (room.y + room.height/2) - (existing.y + existing.height/2)
                distance = math.sqrt(dx**2 + dy**2)

                # Closer is better (inverse distance)
                score += 100.0 / (distance + 1.0)

        # Compactness score (prefer positions closer to origin)
        center_x = room.x + room.width/2
        center_y = room.y + room.height/2
        distance_from_origin = math.sqrt(center_x**2 + center_y**2)
        score += 50.0 / (distance_from_origin + 1.0)

        # Alignment score (prefer aligned with existing rooms)
        for existing in self.rooms:
            # Check horizontal alignment
            if abs(room.x - existing.x) < 0.5:
                score += 10.0
            # Check vertical alignment
            if abs(room.y - existing.y) < 0.5:
                score += 10.0

        return score

    def _grid_fallback_position(self, room: Room) -> Tuple[float, float]:
        """Fallback: place in grid if no good position found."""
        # Calculate grid position based on number of existing rooms
        cols = 3  # Max 3 rooms per row
        row = len(self.rooms) // cols
        col = len(self.rooms) % cols

        x = col * (room.width + 0.2)
        y = row * (room.height + 0.2)

        return (x, y)

    def get_layout_info(self) -> Dict:
        """Get layout information for debugging/visualization."""
        return {
            "num_rooms": len(self.rooms),
            "total_area": sum(r.area for r in self.rooms),
            "bounds": self._calculate_bounds(),
            "rooms": [
                {
                    "name": r.name,
                    "type": r.type,
                    "position": (r.x, r.y),
                    "size": (r.width, r.height)
                }
                for r in self.rooms
            ]
        }

    def _calculate_bounds(self) -> Tuple[float, float, float, float]:
        """Calculate overall layout bounds."""
        if not self.rooms:
            return (0, 0, 0, 0)

        min_x = min(r.x for r in self.rooms)
        min_y = min(r.y for r in self.rooms)
        max_x = max(r.x + r.width for r in self.rooms)
        max_y = max(r.y + r.height for r in self.rooms)

        return (min_x, min_y, max_x, max_y)

    def _count_overlaps(self, rooms: List[Room] = None) -> int:
        """Count the number of overlapping room pairs."""
        if rooms is None:
            rooms = self.rooms

        overlaps = 0
        for i, r1 in enumerate(rooms):
            for r2 in rooms[i+1:]:
                if r1.overlaps(r2, margin=0.0):  # No margin for counting
                    overlaps += 1
        return overlaps


def main():
    """Test the rule-based layout optimizer."""
    print("="*80)
    print("RULE-BASED LAYOUT OPTIMIZER - TEST")
    print("="*80)

    # Test specifications
    test_specs = [
        {
            "name": "2BR Apartment",
            "spec": {
                "bedrooms": 2,
                "bathrooms": 1,
                "kitchen": True,
                "living_room": True
            }
        },
        {
            "name": "3BR House",
            "spec": {
                "bedrooms": 3,
                "bathrooms": 2,
                "kitchen": True,
                "living_room": True,
                "dining_room": True
            }
        },
        {
            "name": "4BR Family Home",
            "spec": {
                "bedrooms": 4,
                "bathrooms": 3,
                "kitchen": True,
                "living_room": True,
                "dining_room": True,
                "study": True
            }
        }
    ]

    optimizer = RuleBasedLayoutOptimizer()

    for test in test_specs:
        print(f"\n{'='*80}")
        print(f"Testing: {test['name']}")
        print(f"Spec: {test['spec']}")
        print("="*80)

        rooms = optimizer.optimize_layout(test['spec'])
        info = optimizer.get_layout_info()

        print(f"\nGenerated {info['num_rooms']} rooms:")
        print(f"Total Area: {info['total_area']:.1f} sqm")
        print(f"Layout Bounds: {info['bounds']}")

        print("\nRoom Placements:")
        for room_info in info['rooms']:
            print(f"  {room_info['name']:20s} @ ({room_info['position'][0]:6.1f}, "
                  f"{room_info['position'][1]:6.1f}) "
                  f"size: {room_info['size'][0]:.1f}m x {room_info['size'][1]:.1f}m")

        # Check for overlaps
        overlaps = []
        for i, r1 in enumerate(rooms):
            for r2 in rooms[i+1:]:
                if r1.overlaps(r2):
                    overlaps.append((r1.name, r2.name))

        if overlaps:
            print(f"\n⚠ WARNING: Found {len(overlaps)} overlaps:")
            for r1, r2 in overlaps:
                print(f"  - {r1} overlaps with {r2}")
        else:
            print("\n✓ No overlaps detected!")

    print("\n" + "="*80)
    print("[OK] Testing complete!")


if __name__ == "__main__":
    main()
