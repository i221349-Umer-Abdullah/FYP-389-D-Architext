"""
Rule-Based Layout Optimizer for Room Placement
Uses heuristics and architectural best practices.
Can be upgraded to ML-based optimizer later.
"""

import sys
from typing import Dict, List, Tuple
from dataclasses import dataclass
import math

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


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
    ROOM_DIMENSIONS = {
        "bedroom": (3.5, 3.0),
        "master_bedroom": (4.0, 3.5),
        "bathroom": (2.0, 2.5),
        "kitchen": (3.0, 4.0),
        "living_room": (5.0, 4.5),
        "dining_room": (3.5, 3.0),
        "study": (2.5, 3.0),
        "hallway": (1.5, 3.0),
        "storage": (2.0, 2.0),
    }

    # Room adjacency preferences (which rooms should be near each other)
    ADJACENCY_PREFERENCES = {
        "kitchen": ["dining_room", "living_room"],
        "living_room": ["kitchen", "dining_room", "hallway"],
        "dining_room": ["kitchen", "living_room"],
        "master_bedroom": ["bathroom"],
        "bedroom": ["bathroom", "hallway"],
        "bathroom": ["bedroom", "hallway"],
        "study": ["living_room", "hallway"],
    }

    # Placement priorities (higher = place first)
    PLACEMENT_PRIORITY = {
        "living_room": 10,
        "kitchen": 9,
        "master_bedroom": 8,
        "bedroom": 7,
        "bathroom": 6,
        "dining_room": 5,
        "study": 4,
        "hallway": 3,
        "storage": 2,
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
