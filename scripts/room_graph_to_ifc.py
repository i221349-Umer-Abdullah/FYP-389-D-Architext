"""
=============================================================================
ArchiText: Generic Room Graph → IFC Adapter (Layer 4)
=============================================================================

This module is the clean interface between Layer 2 (GNN/CVAE graph output)
and Layer 4 (IFC export). It accepts a standardized RoomGraph object and
converts it to an IFC file via the existing BIMGenerator.

The old gnn_to_ifc_pipeline.py was tightly coupled to the CubiCasa5k GNN
architecture. This replaces it with a model-agnostic adapter that works
with any graph generator that produces the standard RoomGraph format.

Standard RoomGraph format (what Layer 2 must output):
    {
        "rooms": [
            {
                "id": "bedroom_0",          # unique ID
                "type": "bedroom",          # ResPlan room type string
                "x": 0.0,                   # metres, absolute position
                "y": 0.0,
                "width": 4.5,              # metres
                "height": 3.2,
                "area": 14.4,              # metres² (optional, derived if missing)
                "connections": ["living"]   # list of adjacent room IDs (optional)
            },
            ...
        ],
        "metadata": {
            "total_area": 120.0,           # metres²
            "unit_type": "apartment",
            "generated_by": "resplan_gnn"
        }
    }

Usage:
    from scripts.room_graph_to_ifc import RoomGraphToIFC

    adapter = RoomGraphToIFC()
    ifc_path = adapter.convert(room_graph, output_path="output/my_house.ifc")

=============================================================================
"""

import os
import sys
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add scripts dir to path so we can import BIMGenerator
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from generate_bim import BIMGenerator

# ── ResPlan room type → human-readable name ────────────────────────────────────
ROOM_TYPE_LABELS = {
    "wall":     "Wall",
    "bedroom":  "Bedroom",
    "bathroom": "Bathroom",
    "living":   "Living Room",
    "kitchen":  "Kitchen",
    "balcony":  "Balcony",
    "storage":  "Storage",
    "parking":  "Parking",
    "garden":   "Garden",
    "pool":     "Pool",
    "stair":    "Staircase",
    "veranda":  "Veranda",
    "inner":    "Inner Hallway",
    # Legacy names from old CubiCasa model (kept for backward compat)
    "living_room":  "Living Room",
    "dining_room":  "Dining Room",
    "study":        "Study",
    "garage":       "Garage",
    "hallway":      "Hallway",
    "other":        "Room",
}

# Minimum sensible dimensions (metres) per room type
MIN_DIMENSIONS = {
    "bedroom":  (2.5, 2.5),
    "bathroom": (1.5, 1.5),
    "living":   (3.0, 3.0),
    "kitchen":  (2.0, 2.0),
    "balcony":  (1.0, 1.0),
    "storage":  (0.8, 0.8),
    "parking":  (2.4, 4.8),
    "garden":   (2.0, 2.0),
    "pool":     (2.0, 4.0),
    "stair":    (1.0, 2.0),
    "veranda":  (1.5, 1.5),
    "inner":    (1.0, 1.0),
    "wall":     (0.2, 0.2),
}
DEFAULT_MIN = (1.5, 1.5)

STANDARD_CEILING_HEIGHT = 2.7  # metres


class RoomGraphToIFC:
    """
    Converts a standardized room graph (from any Layer 2 model) to an IFC file.

    Usage:
        adapter = RoomGraphToIFC()
        ifc_path = adapter.convert(room_graph, output_path="output/house.ifc")
    """

    def __init__(self, ceiling_height: float = STANDARD_CEILING_HEIGHT):
        self.ceiling_height = ceiling_height

    def convert(
        self,
        room_graph: dict,
        output_path: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> str:
        """
        Convert a room graph dict to an IFC file.

        Args:
            room_graph:   Standard room graph dict (see module docstring)
            output_path:  Where to save the .ifc file. Auto-generated if None.
            project_name: IFC project name. Derived from metadata if None.

        Returns:
            Absolute path to the saved .ifc file.
        """
        rooms    = room_graph.get("rooms", [])
        metadata = room_graph.get("metadata", {})

        if not rooms:
            raise ValueError("room_graph contains no rooms")

        # Derive project name
        if project_name is None:
            unit = metadata.get("unit_type", "building").title()
            project_name = f"AI Generated {unit}"

        # Auto output path
        if output_path is None:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = Path(__file__).parent.parent / "output"
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(out_dir / f"generated_{ts}.ifc")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Validate and sanitise rooms
        rooms = self._validate_rooms(rooms)

        # Number duplicate room names (e.g. Bedroom 1, Bedroom 2)
        rooms = self._label_rooms(rooms)

        # Generate IFC
        generator = BIMGenerator()
        generator.create_project_structure(project_name)

        for room in rooms:
            # Skip structural walls — they have no space volume
            if room["type"] == "wall":
                continue
            generator.create_simple_room(
                name    = room["display_name"],
                length  = room["width"],
                width   = room["height"],
                height  = self.ceiling_height,
                x_offset= room["x"],
                y_offset= room["y"],
            )

        generator.ifc.write(output_path)
        print(f"[IFC] Saved: {output_path}")
        print(f"[IFC] Rooms: {len([r for r in rooms if r['type'] != 'wall'])}")
        total_area = sum(r["width"] * r["height"] for r in rooms if r["type"] != "wall")
        print(f"[IFC] Total area: {total_area:.1f} m²")

        return output_path

    def convert_from_node_list(
        self,
        nodes: List[Dict],
        metadata: Optional[dict] = None,
        output_path: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> str:
        """
        Convenience wrapper — accepts a flat list of room dicts directly
        (the format returned by the GNN inference code).

        Args:
            nodes: List of dicts, each with keys: type, x, y, width, height
                   (and optionally: id, area, connections)
        """
        room_graph = {
            "rooms":    nodes,
            "metadata": metadata or {"generated_by": "gnn"},
        }
        return self.convert(room_graph, output_path=output_path, project_name=project_name)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _validate_rooms(self, rooms: List[Dict]) -> List[Dict]:
        """Enforce minimum dimensions and fill in missing fields."""
        validated = []
        for i, room in enumerate(rooms):
            r = dict(room)

            # Ensure required fields exist
            r.setdefault("id",   f"room_{i}")
            r.setdefault("type", "other")
            r.setdefault("x",    0.0)
            r.setdefault("y",    0.0)

            # Enforce minimum sizes
            min_w, min_h = MIN_DIMENSIONS.get(r["type"], DEFAULT_MIN)
            r["width"]  = max(float(r.get("width",  min_w)), min_w)
            r["height"] = max(float(r.get("height", min_h)), min_h)

            # Derive area if missing
            if "area" not in r:
                r["area"] = r["width"] * r["height"]

            # Clamp positions to non-negative
            r["x"] = max(0.0, float(r["x"]))
            r["y"] = max(0.0, float(r["y"]))

            validated.append(r)
        return validated

    def _label_rooms(self, rooms: List[Dict]) -> List[Dict]:
        """Assign human-readable display names, numbering duplicates."""
        type_counts: Dict[str, int] = {}
        for r in rooms:
            type_counts[r["type"]] = type_counts.get(r["type"], 0) + 1

        type_seen: Dict[str, int] = {}
        for r in rooms:
            rtype = r["type"]
            label = ROOM_TYPE_LABELS.get(rtype, rtype.replace("_", " ").title())
            type_seen[rtype] = type_seen.get(rtype, 0) + 1

            if type_counts[rtype] > 1:
                r["display_name"] = f"{label} {type_seen[rtype]}"
            else:
                r["display_name"] = label

        return rooms

    def get_room_summary(self, room_graph: dict) -> dict:
        """Return a summary dict of the room graph (for API responses)."""
        rooms = self._validate_rooms(room_graph.get("rooms", []))
        rooms = self._label_rooms(rooms)

        summary_rooms = []
        total_area = 0.0
        for r in rooms:
            if r["type"] == "wall":
                continue
            area = r["width"] * r["height"]
            total_area += area
            summary_rooms.append({
                "name":   r["display_name"],
                "type":   r["type"],
                "area_m2": round(area, 2),
                "x": round(r["x"], 2),
                "y": round(r["y"], 2),
                "width":  round(r["width"], 2),
                "height": round(r["height"], 2),
            })

        return {
            "rooms":      summary_rooms,
            "room_count": len(summary_rooms),
            "total_area_m2": round(total_area, 2),
            "metadata":   room_graph.get("metadata", {}),
        }


# ── Quick test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Example room graph (matches ResPlan room types)
    test_graph = {
        "rooms": [
            {"id": "living_0",   "type": "living",   "x": 0.0,  "y": 0.0,  "width": 5.5, "height": 4.0},
            {"id": "kitchen_0",  "type": "kitchen",  "x": 5.5,  "y": 0.0,  "width": 3.0, "height": 4.0},
            {"id": "bedroom_0",  "type": "bedroom",  "x": 0.0,  "y": 4.0,  "width": 4.0, "height": 3.5},
            {"id": "bedroom_1",  "type": "bedroom",  "x": 4.0,  "y": 4.0,  "width": 4.5, "height": 3.5},
            {"id": "bathroom_0", "type": "bathroom", "x": 0.0,  "y": 7.5,  "width": 2.5, "height": 2.0},
            {"id": "balcony_0",  "type": "balcony",  "x": 5.5,  "y": 4.0,  "width": 3.0, "height": 2.0},
            {"id": "inner_0",    "type": "inner",    "x": 2.5,  "y": 7.5,  "width": 2.0, "height": 1.5},
        ],
        "metadata": {
            "unit_type": "apartment",
            "total_area": 90.0,
            "generated_by": "test",
        }
    }

    print("Testing RoomGraphToIFC adapter...")
    adapter = RoomGraphToIFC()

    # Print summary
    summary = adapter.get_room_summary(test_graph)
    print(f"\nRoom summary ({summary['room_count']} rooms, {summary['total_area_m2']} m²):")
    for r in summary["rooms"]:
        print(f"  {r['name']:20} {r['area_m2']:5.1f} m²  at ({r['x']}, {r['y']})")

    # Generate IFC
    os.makedirs("output", exist_ok=True)
    ifc_path = adapter.convert(test_graph, output_path="output/adapter_test.ifc",
                               project_name="Adapter Test House")
    print(f"\nIFC saved: {ifc_path}")

    sz = os.path.getsize(ifc_path) / 1024
    print(f"File size: {sz:.1f} KB")
    print("\nDone! Open output/adapter_test.ifc in BlenderBIM or FreeCAD to verify.")
