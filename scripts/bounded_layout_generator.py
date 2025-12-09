"""
=============================================================================
ArchiText: Bounded Layout Generator
=============================================================================

This module implements area-constrained floor plan generation. It ensures
that generated layouts fit within specified plot/area boundaries, supporting
multiple measurement units common in real estate.

Approach: Generate-and-Validate
-------------------------------
The system uses an iterative approach:
    1. Parse area specification (e.g., "5 marla", "60x80 feet")
    2. Generate layout using GraphLayoutOptimizer
    3. Check if layout fits within bounds
    4. If too large, scale down room dimensions and retry
    5. Repeat until success or max attempts reached

Supported Area Units:
---------------------
    Pakistani/Indian:
        - marla (1 marla = 272.25 sq ft = 25.29 sqm)
        - kanal (1 kanal = 20 marla = 505.86 sqm)

    Imperial:
        - sq ft, square feet
        - WxH feet (e.g., "60x80 feet")

    Metric:
        - sq m, sqm, m2, square meters
        - WxH meters (e.g., "20x25 meters")

Features:
---------
    - Automatic unit conversion to meters
    - Intelligent room scaling
    - Space utilization reporting
    - Multiple retry attempts with progressive scaling

Example Usage:
--------------
    >>> generator = BoundedLayoutGenerator()
    >>> result = generator.generate(
    ...     spec={"bedrooms": 3, "bathrooms": 2, "kitchen": True},
    ...     area_spec="5 marla"
    ... )
    >>> if result.success:
    ...     print(f"Layout fits in {result.bounds_used.area_sqm:.0f} sqm")

Author: ArchiText Team
Version: 1.0.0
=============================================================================
"""

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from copy import deepcopy

from area_parser import AreaParser, AreaBounds
from graph_layout_optimizer import GraphLayoutOptimizer, RoomNode, FloorPlanGraph


@dataclass
class GenerationResult:
    """Result of a bounded layout generation attempt."""
    success: bool
    graph: Optional[FloorPlanGraph]
    rooms: List[RoomNode]
    bounds_used: Optional[AreaBounds]
    actual_bounds: Tuple[float, float, float, float]  # (min_x, min_y, max_x, max_y)
    actual_area: float  # sqm
    scale_factor: float
    attempts: int
    message: str


class BoundedLayoutGenerator:
    """
    Generates floor plans constrained to a specified area.

    Strategy (Option 2 - Generate and Validate):
    1. Parse the area specification
    2. Generate a layout using GraphLayoutOptimizer
    3. Check if layout fits within bounds
    4. If too large, scale down room dimensions and retry
    5. Repeat until success or max attempts reached
    """

    MAX_ATTEMPTS = 10
    MIN_SCALE_FACTOR = 0.5  # Don't scale rooms below 50% of original

    def __init__(self):
        self.area_parser = AreaParser()
        self.base_optimizer = GraphLayoutOptimizer()

    def generate(self, spec: Dict, area_spec: str = None,
                 bounds: AreaBounds = None) -> GenerationResult:
        """
        Generate a layout constrained to the specified area.

        Args:
            spec: Room specification dictionary
            area_spec: Area specification string (e.g., "5 marla", "60x80 feet")
            bounds: Pre-parsed AreaBounds (overrides area_spec)

        Returns:
            GenerationResult with the generated layout
        """
        # Parse area specification
        if bounds is None and area_spec:
            bounds = self.area_parser.parse(area_spec)
            if bounds is None:
                return GenerationResult(
                    success=False,
                    graph=None,
                    rooms=[],
                    bounds_used=None,
                    actual_bounds=(0, 0, 0, 0),
                    actual_area=0,
                    scale_factor=1.0,
                    attempts=0,
                    message=f"Failed to parse area specification: {area_spec}"
                )

        # If no bounds specified, generate without constraints
        if bounds is None:
            return self._generate_unconstrained(spec)

        # Try to generate within bounds
        return self._generate_bounded(spec, bounds)

    def _generate_unconstrained(self, spec: Dict) -> GenerationResult:
        """Generate a layout without area constraints."""
        optimizer = GraphLayoutOptimizer()
        graph, rooms = optimizer.optimize_layout(spec)
        info = optimizer.get_layout_info()

        return GenerationResult(
            success=True,
            graph=graph,
            rooms=rooms,
            bounds_used=None,
            actual_bounds=info['bounds'],
            actual_area=info['total_area'],
            scale_factor=1.0,
            attempts=1,
            message="Generated unconstrained layout"
        )

    def _generate_bounded(self, spec: Dict, bounds: AreaBounds) -> GenerationResult:
        """Generate a layout that fits within the specified bounds."""

        target_width = bounds.width
        target_height = bounds.height
        target_area = bounds.area_sqm

        best_result = None
        best_fit_score = float('inf')  # Lower is better

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            # Calculate scale factor based on attempt
            # Start at 1.0 and decrease if layout is too large
            if attempt == 1:
                scale = 1.0
            else:
                # Progressive scaling based on previous attempt's overflow
                if best_result:
                    actual_w = best_result.actual_bounds[2] - best_result.actual_bounds[0]
                    actual_h = best_result.actual_bounds[3] - best_result.actual_bounds[1]

                    # Calculate how much we need to shrink
                    width_ratio = target_width / actual_w if actual_w > 0 else 1
                    height_ratio = target_height / actual_h if actual_h > 0 else 1
                    scale = min(width_ratio, height_ratio, scale) * 0.95  # 5% safety margin
                else:
                    scale = 1.0 - (attempt - 1) * 0.1

            # Ensure minimum scale
            scale = max(scale, self.MIN_SCALE_FACTOR)

            # Generate layout with scaled room dimensions
            result = self._generate_scaled(spec, scale)

            if result is None:
                continue

            # Check if layout fits within bounds
            actual_w = result.actual_bounds[2] - result.actual_bounds[0]
            actual_h = result.actual_bounds[3] - result.actual_bounds[1]

            fits_width = actual_w <= target_width
            fits_height = actual_h <= target_height

            # Calculate fit score (how well it fits)
            overflow_x = max(0, actual_w - target_width)
            overflow_y = max(0, actual_h - target_height)
            fit_score = overflow_x + overflow_y

            # Track best result
            if fit_score < best_fit_score:
                best_fit_score = fit_score
                best_result = result
                best_result.attempts = attempt
                best_result.bounds_used = bounds

            # Success condition
            if fits_width and fits_height:
                # Normalize layout to start at origin (0, 0)
                normalized = self._normalize_layout(result.graph, result.rooms)
                result.graph = normalized[0]
                result.rooms = normalized[1]
                result.actual_bounds = self._calculate_bounds(result.rooms)
                result.success = True
                result.message = (f"Generated layout fitting in {target_width:.1f}m x {target_height:.1f}m "
                                  f"(scale: {scale:.2f}, attempts: {attempt})")
                return result

        # Return best attempt even if not perfect fit
        if best_result:
            normalized = self._normalize_layout(best_result.graph, best_result.rooms)
            best_result.graph = normalized[0]
            best_result.rooms = normalized[1]
            best_result.actual_bounds = self._calculate_bounds(best_result.rooms)
            best_result.success = False
            actual_w = best_result.actual_bounds[2] - best_result.actual_bounds[0]
            actual_h = best_result.actual_bounds[3] - best_result.actual_bounds[1]
            best_result.message = (f"Best effort: {actual_w:.1f}m x {actual_h:.1f}m "
                                   f"(target: {target_width:.1f}m x {target_height:.1f}m, "
                                   f"overflow: {actual_w - target_width:.1f}m x {actual_h - target_height:.1f}m)")
            return best_result

        return GenerationResult(
            success=False,
            graph=None,
            rooms=[],
            bounds_used=bounds,
            actual_bounds=(0, 0, 0, 0),
            actual_area=0,
            scale_factor=1.0,
            attempts=self.MAX_ATTEMPTS,
            message="Failed to generate layout after maximum attempts"
        )

    def _generate_scaled(self, spec: Dict, scale: float) -> Optional[GenerationResult]:
        """Generate a layout with scaled room dimensions."""

        # Create a copy of the optimizer with scaled dimensions
        optimizer = GraphLayoutOptimizer()

        # Scale all room dimensions
        original_dims = deepcopy(optimizer.ROOM_DIMENSIONS)
        for room_type, (w, h) in original_dims.items():
            optimizer.ROOM_DIMENSIONS[room_type] = (w * scale, h * scale)

        try:
            graph, rooms = optimizer.optimize_layout(spec)
            info = optimizer.get_layout_info()

            return GenerationResult(
                success=False,  # Will be set later
                graph=graph,
                rooms=rooms,
                bounds_used=None,
                actual_bounds=info['bounds'],
                actual_area=info['total_area'],
                scale_factor=scale,
                attempts=0,
                message=""
            )
        except Exception as e:
            print(f"[!] Layout generation failed: {e}")
            return None
        finally:
            # Restore original dimensions
            optimizer.ROOM_DIMENSIONS = original_dims

    def _normalize_layout(self, graph: FloorPlanGraph,
                          rooms: List[RoomNode]) -> Tuple[FloorPlanGraph, List[RoomNode]]:
        """Normalize layout to start at origin (0, 0)."""
        if not rooms:
            return graph, rooms

        # Find minimum coordinates
        min_x = min(r.x for r in rooms)
        min_y = min(r.y for r in rooms)

        # Shift all rooms (rooms list and graph.nodes contain the same objects,
        # so we only need to update one)
        for room in rooms:
            room.x -= min_x
            room.y -= min_y

        return graph, rooms

    def _calculate_bounds(self, rooms: List[RoomNode]) -> Tuple[float, float, float, float]:
        """Calculate bounding box of all rooms."""
        if not rooms:
            return (0, 0, 0, 0)

        min_x = min(r.x for r in rooms)
        min_y = min(r.y for r in rooms)
        max_x = max(r.x + r.width for r in rooms)
        max_y = max(r.y + r.height for r in rooms)

        return (min_x, min_y, max_x, max_y)

    def estimate_required_area(self, spec: Dict) -> float:
        """
        Estimate the minimum area required for a given specification.

        Returns area in square meters.
        """
        optimizer = GraphLayoutOptimizer()

        # Calculate total room area
        total_area = 0
        num_bedrooms = spec.get("bedrooms", 2)
        num_bathrooms = spec.get("bathrooms", 1)

        if spec.get("living_room", True):
            w, h = optimizer.ROOM_DIMENSIONS.get("living_room", (5.5, 4.5))
            total_area += w * h

        if spec.get("kitchen", True):
            w, h = optimizer.ROOM_DIMENSIONS.get("kitchen", (4.0, 3.5))
            total_area += w * h

        if spec.get("dining_room", False):
            w, h = optimizer.ROOM_DIMENSIONS.get("dining_room", (4.0, 3.5))
            total_area += w * h

        if num_bedrooms > 0:
            # Master bedroom
            w, h = optimizer.ROOM_DIMENSIONS.get("master_bedroom", (4.5, 4.0))
            total_area += w * h

            # Other bedrooms
            w, h = optimizer.ROOM_DIMENSIONS.get("bedroom", (3.5, 3.5))
            total_area += (num_bedrooms - 1) * w * h

            # Hallway
            w, h = optimizer.ROOM_DIMENSIONS.get("hallway", (4.0, 1.5))
            total_area += w * h

        if num_bathrooms > 0 and num_bedrooms > 0:
            # En-suite
            w, h = optimizer.ROOM_DIMENSIONS.get("en_suite", (2.5, 2.5))
            total_area += w * h

        # Additional bathrooms
        if num_bathrooms > 1:
            w, h = optimizer.ROOM_DIMENSIONS.get("bathroom", (2.5, 2.5))
            total_area += (num_bathrooms - 1) * w * h

        if spec.get("study", False):
            w, h = optimizer.ROOM_DIMENSIONS.get("study", (3.0, 3.0))
            total_area += w * h

        if spec.get("garage", False):
            w, h = optimizer.ROOM_DIMENSIONS.get("garage", (6.0, 3.0))
            total_area += w * h

        # Add 20% for walls and circulation
        return total_area * 1.2


def main():
    """Test the bounded layout generator."""
    print("=" * 70)
    print("BOUNDED LAYOUT GENERATOR - TEST")
    print("=" * 70)

    generator = BoundedLayoutGenerator()

    # Test cases with different area specifications
    test_cases = [
        {
            "name": "5 Marla House",
            "area": "5 marla",
            "spec": {
                "bedrooms": 2,
                "bathrooms": 1,
                "kitchen": True,
                "living_room": True,
            }
        },
        {
            "name": "10 Marla House",
            "area": "10 marla",
            "spec": {
                "bedrooms": 3,
                "bathrooms": 2,
                "kitchen": True,
                "living_room": True,
                "dining_room": True,
            }
        },
        {
            "name": "60x80 Feet Plot",
            "area": "60x80 feet",
            "spec": {
                "bedrooms": 3,
                "bathrooms": 2,
                "kitchen": True,
                "living_room": True,
                "dining_room": True,
                "study": True,
            }
        },
        {
            "name": "Tight 100 sqm",
            "area": "100 sqm",
            "spec": {
                "bedrooms": 2,
                "bathrooms": 1,
                "kitchen": True,
                "living_room": True,
            }
        },
        {
            "name": "1 Kanal House",
            "area": "1 kanal",
            "spec": {
                "bedrooms": 4,
                "bathrooms": 3,
                "kitchen": True,
                "living_room": True,
                "dining_room": True,
                "study": True,
                "garage": True,
            }
        },
    ]

    for test in test_cases:
        print(f"\n{'=' * 70}")
        print(f"Test: {test['name']}")
        print(f"Area: {test['area']}")
        print(f"Spec: {test['spec']}")
        print("=" * 70)

        # Estimate required area first
        estimated = generator.estimate_required_area(test['spec'])
        print(f"\nEstimated required area: {estimated:.1f} sqm")

        # Generate bounded layout
        result = generator.generate(test['spec'], test['area'])

        if result.bounds_used:
            print(f"Target bounds: {result.bounds_used.width:.1f}m x {result.bounds_used.height:.1f}m "
                  f"({result.bounds_used.area_sqm:.1f} sqm)")

        status = "[OK]" if result.success else "[!!]"
        print(f"\n{status} {result.message}")

        if result.rooms:
            actual_w = result.actual_bounds[2] - result.actual_bounds[0]
            actual_h = result.actual_bounds[3] - result.actual_bounds[1]
            print(f"Actual layout: {actual_w:.1f}m x {actual_h:.1f}m ({result.actual_area:.1f} sqm)")
            print(f"Scale factor: {result.scale_factor:.2f}")
            print(f"Attempts: {result.attempts}")

            print("\nRooms:")
            for room in result.rooms:
                print(f"  {room.id:20s} @ ({room.x:5.1f}, {room.y:5.1f}) "
                      f"size: {room.width:.1f}x{room.height:.1f}m")

    print("\n" + "=" * 70)
    print("[OK] Bounded layout generator tests complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
