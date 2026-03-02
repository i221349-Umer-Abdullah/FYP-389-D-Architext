"""
Generic Room Graph → IFC Adapter (Layer 4)
Placed inside backend/core/ for clean importability without sys.path tricks.

Accepts standard RoomGraph dicts from any Layer 2 model and converts
them to IFC files via the BIMGenerator in scripts/generate_bim.py.

Standard RoomGraph format:
    {
        "rooms": [
            {"id": "bedroom_0", "type": "bedroom",
             "x": 0.0, "y": 0.0, "width": 4.5, "height": 3.2},
            ...
        ],
        "metadata": {"unit_type": "house", "total_area": 120, ...}
    }
"""

import sys
import os
import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Ensure generate_bim.py can be found
_SCRIPTS = Path(__file__).parent.parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from generate_bim import BIMGenerator

ROOM_TYPE_LABELS = {
    "wall":      "Wall",        "bedroom":   "Bedroom",
    "bathroom":  "Bathroom",    "living":    "Living Room",
    "kitchen":   "Kitchen",     "balcony":   "Balcony",
    "storage":   "Storage",     "parking":   "Parking",
    "garden":    "Garden",      "pool":      "Pool",
    "stair":     "Staircase",   "veranda":   "Veranda",
    "inner":     "Inner Hallway",
    "living_room": "Living Room", "dining_room": "Dining Room",
    "study":     "Study",       "garage":    "Garage",
    "hallway":   "Hallway",     "other":     "Room",
}

MIN_DIMENSIONS = {
    "bedroom": (2.5, 2.5), "bathroom": (1.5, 1.5), "living": (3.0, 3.0),
    "kitchen": (2.0, 2.0), "balcony": (1.0, 1.0),  "storage": (0.8, 0.8),
    "parking": (2.4, 4.8), "garden": (2.0, 2.0),   "pool": (2.0, 4.0),
    "stair": (1.0, 2.0),   "veranda": (1.5, 1.5),  "inner": (1.0, 1.0),
    "wall": (0.2, 0.2),
}
DEFAULT_MIN        = (1.5, 1.5)
STANDARD_HEIGHT    = 2.7


class RoomGraphToIFC:
    def __init__(self, ceiling_height: float = STANDARD_HEIGHT):
        self.ceiling_height = ceiling_height

    def convert(self, room_graph: dict, output_path: Optional[str] = None,
                project_name: Optional[str] = None) -> str:
        rooms    = room_graph.get("rooms", [])
        metadata = room_graph.get("metadata", {})
        if not rooms:
            raise ValueError("room_graph contains no rooms")

        project_name = project_name or f"AI Generated {metadata.get('unit_type','Building').title()}"
        if output_path is None:
            ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            out = Path(__file__).parent.parent.parent / "output"
            out.mkdir(parents=True, exist_ok=True)
            output_path = str(out / f"generated_{ts}.ifc")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        rooms = self._validate(rooms)
        rooms = self._label(rooms)

        gen = BIMGenerator()
        gen.create_project_structure(project_name)
        for r in rooms:
            if r["type"] == "wall":
                continue
            gen.create_simple_room(
                name=r["display_name"], length=r["width"], width=r["height"],
                height=self.ceiling_height, x_offset=r["x"], y_offset=r["y"],
            )
        gen.ifc.write(output_path)
        return output_path

    def get_room_summary(self, room_graph: dict) -> dict:
        rooms = self._validate(room_graph.get("rooms", []))
        rooms = self._label(rooms)
        summary, total = [], 0.0
        for r in rooms:
            if r["type"] == "wall": continue
            area   = r["width"] * r["height"]
            total += area
            summary.append({
                "name": r["display_name"], "type": r["type"],
                "area_m2": round(area, 2),
                "x": round(r["x"], 2), "y": round(r["y"], 2),
                "width": round(r["width"], 2), "height": round(r["height"], 2),
            })
        return {
            "rooms": summary, "room_count": len(summary),
            "total_area_m2": round(total, 2),
            "metadata": room_graph.get("metadata", {}),
        }

    def _validate(self, rooms):
        out = []
        for i, r in enumerate(rooms):
            r = dict(r)
            r.setdefault("id", f"room_{i}")
            r.setdefault("type", "other")
            r.setdefault("x", 0.0)
            r.setdefault("y", 0.0)
            mw, mh  = MIN_DIMENSIONS.get(r["type"], DEFAULT_MIN)
            r["width"]  = max(float(r.get("width",  mw)), mw)
            r["height"] = max(float(r.get("height", mh)), mh)
            r["x"]      = max(0.0, float(r["x"]))
            r["y"]      = max(0.0, float(r["y"]))
            out.append(r)
        return out

    def _label(self, rooms):
        counts: Dict[str, int] = {}
        for r in rooms:
            counts[r["type"]] = counts.get(r["type"], 0) + 1
        seen: Dict[str, int] = {}
        for r in rooms:
            t     = r["type"]
            label = ROOM_TYPE_LABELS.get(t, t.replace("_"," ").title())
            seen[t] = seen.get(t, 0) + 1
            r["display_name"] = f"{label} {seen[t]}" if counts[t] > 1 else label
        return rooms
