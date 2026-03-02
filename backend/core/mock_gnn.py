"""
Mock GNN Layout Generator — Layer 2 placeholder.

Used UNTIL the real ResPlan GNN finishes training.
Produces a plausible rule-based room layout from a spec dict
so the end-to-end pipeline works before model weights are ready.

!! TO SWAP IN THE REAL MODEL:
   Replace the `generate()` method body with:
       return RealGNNAdapter(model_path).generate(spec)
   Everything else (pipeline, API, IFC adapter) stays the same.
"""

import random
import math
from typing import List, Dict, Any


# Typical room sizes in metres (width x height ranges per type)
ROOM_SIZE_RANGES = {
    "bedroom":  ((3.0, 4.5), (3.0, 4.0)),
    "bathroom": ((1.8, 2.5), (1.8, 2.5)),
    "living":   ((4.0, 6.0), (3.5, 5.0)),
    "kitchen":  ((2.5, 4.0), (2.5, 3.5)),
    "balcony":  ((1.5, 3.0), (1.0, 1.8)),
    "storage":  ((1.5, 2.5), (1.5, 2.0)),
    "parking":  ((2.5, 3.5), (4.5, 6.0)),
    "garden":   ((3.0, 6.0), (3.0, 5.0)),
    "pool":     ((3.0, 4.0), (5.0, 8.0)),
    "stair":    ((2.0, 2.5), (2.5, 3.5)),
    "veranda":  ((2.0, 4.0), (1.5, 2.5)),
    "inner":    ((1.2, 2.0), (2.0, 3.5)),
}

def _rand_size(room_type: str):
    rw, rh = ROOM_SIZE_RANGES.get(room_type, ((2.5, 4.0), (2.5, 4.0)))
    w = round(random.uniform(*rw), 1)
    h = round(random.uniform(*rh), 1)
    return w, h


def generate_mock_layout(spec: Dict[str, Any]) -> List[Dict]:
    """
    Generate a simple grid-packed room layout from a normalised spec dict.
    Returns a list of room dicts matching the RoomGraphToIFC input format.
    """
    # Build ordered room list from spec
    room_order = [
        "inner", "living", "kitchen",
        "bedroom", "bedroom", "bedroom", "bedroom",
        "bathroom", "bathroom", "bathroom",
        "balcony", "veranda", "garden", "pool",
        "storage", "parking", "stair",
    ]

    rooms_to_place = []
    type_count: Dict[str, int] = {}

    for rtype in room_order:
        wanted = int(spec.get(rtype, 0))
        placed  = type_count.get(rtype, 0)
        if placed < wanted:
            rooms_to_place.append(rtype)
            type_count[rtype] = placed + 1

    # Pack rooms in rows — simple greedy strip packing
    rooms: List[Dict] = []
    row_x, row_y = 0.0, 0.0
    row_height    = 0.0
    MAX_ROW_WIDTH = math.sqrt(float(spec.get("net_area", 100))) * 1.4

    for i, rtype in enumerate(rooms_to_place):
        w, h = _rand_size(rtype)

        # Start new row if too wide
        if row_x + w > MAX_ROW_WIDTH and row_x > 0:
            row_y    += row_height + 0.2  # 20cm corridor gap
            row_x     = 0.0
            row_height = 0.0

        rooms.append({
            "id":     f"{rtype}_{type_count.get(rtype+'_placed', 0)}",
            "type":   rtype,
            "x":      round(row_x, 2),
            "y":      round(row_y, 2),
            "width":  w,
            "height": h,
        })

        row_x      += w + 0.2
        row_height  = max(row_height, h)
        type_count[rtype + '_placed'] = type_count.get(rtype + '_placed', 0) + 1

    return rooms


class MockGNNAdapter:
    """
    Drop-in placeholder for the real GNN until model weights are ready.
    """
    IS_MOCK = True

    def generate(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Args:
            spec: normalised room spec dict (from spec_converter.normalise_spec)

        Returns:
            Standard room_graph dict (compatible with RoomGraphToIFC)
        """
        rooms = generate_mock_layout(spec)
        total_area = sum(r["width"] * r["height"] for r in rooms)

        return {
            "rooms": rooms,
            "metadata": {
                "unit_type":     spec.get("unit_type", "house"),
                "total_area":    round(total_area, 1),
                "requested_area": spec.get("net_area", 100),
                "generated_by":  "mock_gnn_v0 (placeholder — real model training)",
                "is_mock":       True,
            }
        }
