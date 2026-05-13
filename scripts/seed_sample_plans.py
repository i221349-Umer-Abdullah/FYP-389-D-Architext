#!/usr/bin/env python3
"""
Seed pre-designed sample floor plans into the Architext MongoDB so they
appear immediately in the public dashboard — no generation required.

Usage
-----
  # Make sure MONGODB_URI is set (same value as frontend/.env.local):
  set MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/architext
  python scripts/seed_sample_plans.py

  # Re-running is safe — plans already present (matched by title) are skipped.
"""

import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent.parent

try:
    from dotenv import load_dotenv
    for _f in [ROOT / "frontend" / ".env.local", ROOT / "frontend" / ".env"]:
        if _f.exists():
            load_dotenv(_f)
            print(f"[seed] Loaded env from {_f.name}")
            break
except ImportError:
    pass

MONGODB_URI = os.getenv("MONGODB_URI", "")
if not MONGODB_URI:
    print(
        "ERROR: MONGODB_URI is not set.\n"
        "Add it to frontend/.env.local or export it:\n"
        '  set MONGODB_URI="mongodb+srv://..."'
    )
    sys.exit(1)

# ── Room colour palette ───────────────────────────────────────────────────────
_COLOURS = {
    "living": "#AED6F1", "kitchen": "#A9DFBF", "dining": "#D5F5E3",
    "bedroom": "#F9E79F", "bathroom": "#FADBD8", "hallway": "#D7DBDD",
    "balcony": "#A9CCE3", "garden": "#82E0AA",  "parking": "#CCD1D1",
    "storage": "#D2B4DE", "stair":   "#F0B27A", "veranda": "#85C1E9",
    "other":   "#EAECEE",
}


def _render_png(rooms: list) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches

    fig, ax = plt.subplots(figsize=(8, 8))
    xs  = [r["x"]               for r in rooms]
    ys  = [r["y"]               for r in rooms]
    xe  = [r["x"] + r["width"]  for r in rooms]
    ye  = [r["y"] + r["height"] for r in rooms]

    margin = 1.0
    ax.set_xlim(min(xs) - margin, max(xe) + margin)
    ax.set_ylim(min(ys) - margin, max(ye) + margin)
    ax.set_aspect("equal")
    ax.grid(True, linestyle="--", alpha=0.3, color="#999")
    ax.set_xlabel("metres", fontsize=8)
    ax.set_ylabel("metres", fontsize=8)

    for r in rooms:
        colour = _COLOURS.get(r["type"], "#EAECEE")
        rect   = patches.Rectangle(
            (r["x"], r["y"]), r["width"], r["height"],
            linewidth=1.5, edgecolor="#333", facecolor=colour, alpha=0.85,
        )
        ax.add_patch(rect)
        label = r["type"].replace("_", " ").title()
        area  = round(r.get("area", r["width"] * r["height"]), 1)
        ax.text(
            r["x"] + r["width"] / 2, r["y"] + r["height"] / 2,
            f"{label}\n{area} m²",
            ha="center", va="center", fontsize=7.5, fontweight="bold", color="#222",
        )

    total = sum(r.get("area", r["width"] * r["height"]) for r in rooms)
    ax.set_title(f"{len(rooms)} rooms  ·  {round(total, 1)} m²", fontsize=10)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _r(id_, type_, x, y, w, h):
    return {"id": id_, "type": type_, "x": x, "y": y,
            "width": w, "height": h, "area": round(w * h, 2)}


# ── All sample plans ──────────────────────────────────────────────────────────

SAMPLE_PLANS = [

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPACT / LOW-INCOME (3–5 MARLA)
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "title": "3-Marla Starter Home",
        "description": "~76 m² · 6 rooms · budget 1-bedroom with veranda and parking",
        "style_id": "haveli",
        "material_tier": "budget",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0,  2.5, 5.0),
            _r("veranda_1",  "veranda",  2.5,  0.0,  4.5, 2.0),
            _r("living_2",   "living",   2.5,  2.0,  4.5, 3.0),
            _r("kitchen_3",  "kitchen",  7.0,  0.0,  3.0, 5.0),
            _r("bathroom_4", "bathroom", 0.0,  5.0,  2.5, 2.5),
            _r("bedroom_5",  "bedroom",  2.5,  5.0,  7.5, 4.5),
        ],
    },

    {
        "title": "3-Marla Two-Storey Ground Floor",
        "description": "~80 m² · 7 rooms · narrow two-storey typical of new housing societies",
        "style_id": "modern",
        "material_tier": "budget",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0,  3.0, 4.5),
            _r("veranda_1",  "veranda",  3.0,  0.0,  5.0, 1.8),
            _r("living_2",   "living",   3.0,  1.8,  5.0, 2.7),
            _r("kitchen_3",  "kitchen",  8.0,  0.0,  3.5, 4.5),
            _r("hallway_4",  "hallway",  0.0,  4.5, 11.5, 1.3),
            _r("bathroom_5", "bathroom", 0.0,  5.8,  2.5, 2.5),
            _r("bedroom_6",  "bedroom",  2.5,  5.8,  9.0, 4.5),
        ],
    },

    {
        "title": "5-Marla Standard Pakistani House",
        "description": "~126 m² · 9 rooms · classic 2-bedroom layout found across Pakistan",
        "style_id": "haveli",
        "material_tier": "standard",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0,  2.8, 5.5),
            _r("veranda_1",  "veranda",  2.8,  0.0,  4.5, 2.0),
            _r("living_2",   "living",   2.8,  2.0,  4.5, 3.5),
            _r("kitchen_3",  "kitchen",  7.3,  0.0,  3.2, 5.5),
            _r("hallway_4",  "hallway",  0.0,  5.5, 10.5, 1.4),
            _r("bathroom_5", "bathroom", 0.0,  6.9,  2.5, 2.6),
            _r("bathroom_6", "bathroom", 2.5,  6.9,  2.5, 2.6),
            _r("bedroom_7",  "bedroom",  5.0,  6.9,  5.5, 4.0),
            _r("bedroom_8",  "bedroom",  0.0,  9.5,  5.0, 3.5),
        ],
    },

    {
        "title": "5-Marla House with Servant Quarter",
        "description": "~130 m² · 10 rooms · 2 bedrooms with dedicated servant quarter and utility",
        "style_id": "modern",
        "material_tier": "standard",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0,  3.0, 6.0),
            _r("servant_1",  "bedroom",  3.0,  0.0,  2.5, 3.0),
            _r("kitchen_2",  "kitchen",  3.0,  3.0,  2.5, 3.0),
            _r("veranda_3",  "veranda",  5.5,  0.0,  4.5, 2.5),
            _r("living_4",   "living",   5.5,  2.5,  4.5, 3.5),
            _r("hallway_5",  "hallway",  0.0,  6.0, 10.0, 1.4),
            _r("bathroom_6", "bathroom", 0.0,  7.4,  2.5, 2.5),
            _r("bathroom_7", "bathroom", 2.5,  7.4,  2.5, 2.5),
            _r("bedroom_8",  "bedroom",  5.0,  7.4,  5.0, 4.5),
            _r("bedroom_9",  "bedroom",  0.0,  9.9,  5.0, 3.5),
        ],
    },

    {
        "title": "Old City Narrow Gali House",
        "description": "~90 m² · 7 rooms · deep-narrow plot typical of old Lahore & Rawalpindi galis",
        "style_id": "haveli",
        "material_tier": "budget",
        "rooms": [
            _r("veranda_0",  "veranda",  0.0,  0.0,  5.5, 1.8),
            _r("living_1",   "living",   0.0,  1.8,  5.5, 3.5),
            _r("kitchen_2",  "kitchen",  0.0,  5.3,  5.5, 3.0),
            _r("bathroom_3", "bathroom", 0.0,  8.3,  2.5, 2.5),
            _r("storage_4",  "storage",  2.5,  8.3,  3.0, 2.5),
            _r("bedroom_5",  "bedroom",  0.0, 10.8,  5.5, 4.0),
            _r("bedroom_6",  "bedroom",  0.0, 14.8,  5.5, 4.0),
        ],
    },

    {
        "title": "Corner Plot 5-Marla House",
        "description": "~145 m² · 9 rooms · wider corner plot with 2 bedrooms and large master suite",
        "style_id": "modern",
        "material_tier": "standard",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0,  4.0, 5.0),
            _r("veranda_1",  "veranda",  4.0,  0.0,  5.0, 2.0),
            _r("living_2",   "living",   4.0,  2.0,  5.0, 3.0),
            _r("kitchen_3",  "kitchen",  9.0,  0.0,  5.0, 5.0),
            _r("hallway_4",  "hallway",  0.0,  5.0, 14.0, 1.4),
            _r("bathroom_5", "bathroom", 0.0,  6.4,  2.8, 2.8),
            _r("bathroom_6", "bathroom", 2.8,  6.4,  2.8, 2.8),
            _r("bedroom_7",  "bedroom",  5.6,  6.4,  8.4, 5.5),
            _r("bedroom_8",  "bedroom",  0.0,  9.2,  5.6, 4.5),
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # MEDIUM HOUSES (7–10 MARLA)
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "title": "7-Marla Victorian House — Lahore Civil Lines",
        "description": "~185 m² · 11 rooms · 3 bedrooms in ornate colonial style with drawing room",
        "style_id": "victorian",
        "material_tier": "standard",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0,  4.5, 7.0),
            _r("veranda_1",  "veranda",  4.5,  0.0,  5.5, 2.5),
            _r("drawing_2",  "living",   4.5,  2.5,  5.5, 4.5),
            _r("kitchen_3",  "kitchen", 10.0,  0.0,  4.0, 3.5),
            _r("dining_4",   "dining",  10.0,  3.5,  4.0, 3.5),
            _r("hallway_5",  "hallway",  0.0,  7.0, 14.0, 1.5),
            _r("bathroom_6", "bathroom", 0.0,  8.5,  3.0, 3.0),
            _r("bathroom_7", "bathroom", 3.0,  8.5,  3.0, 3.0),
            _r("bedroom_8",  "bedroom",  6.0,  8.5,  8.0, 4.5),
            _r("bedroom_9",  "bedroom",  0.0, 11.5,  6.0, 4.5),
            _r("bedroom_10", "bedroom",  6.0, 13.0,  8.0, 3.0),
        ],
    },

    {
        "title": "7-Marla Mediterranean House",
        "description": "~180 m² · 12 rooms · 3 bedrooms with terracotta roof, garden and dining patio",
        "style_id": "mediterranean",
        "material_tier": "standard",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0,  4.0, 6.5),
            _r("veranda_1",  "veranda",  4.0,  0.0,  5.0, 2.5),
            _r("living_2",   "living",   4.0,  2.5,  5.0, 4.0),
            _r("kitchen_3",  "kitchen",  9.0,  0.0,  4.0, 3.5),
            _r("dining_4",   "dining",   9.0,  3.5,  4.0, 3.0),
            _r("garden_5",   "garden",  13.0,  0.0,  3.5, 6.5),
            _r("hallway_6",  "hallway",  0.0,  6.5, 16.5, 1.5),
            _r("bathroom_7", "bathroom", 0.0,  8.0,  3.0, 3.0),
            _r("bathroom_8", "bathroom", 3.0,  8.0,  3.0, 3.0),
            _r("bedroom_9",  "bedroom",  6.0,  8.0,  5.25,5.0),
            _r("bedroom_10", "bedroom", 11.25, 8.0,  5.25,5.0),
            _r("bedroom_11", "bedroom",  0.0, 11.0,  6.0, 4.5),
        ],
    },

    {
        "title": "10-Marla DHA-Style House",
        "description": "~252 m² · 14 rooms · 4 bedrooms, drawing room, TV lounge, utility area",
        "style_id": "modern",
        "material_tier": "standard",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0,  6.0, 7.0),
            _r("drawing_1",  "living",   6.0,  0.0,  5.5, 4.0),
            _r("kitchen_2",  "kitchen", 11.5,  0.0,  4.0, 3.5),
            _r("utility_3",  "storage", 11.5,  3.5,  4.0, 3.5),
            _r("lounge_4",   "living",   6.0,  4.0,  5.5, 3.0),
            _r("garden_5",   "garden",  15.5,  0.0,  3.5, 7.0),
            _r("hallway_6",  "hallway",  0.0,  7.0, 19.0, 1.5),
            _r("bathroom_7", "bathroom", 0.0,  8.5,  3.0, 3.0),
            _r("bathroom_8", "bathroom", 3.0,  8.5,  3.0, 3.0),
            _r("bathroom_9", "bathroom", 6.0,  8.5,  3.0, 3.0),
            _r("bedroom_10", "bedroom",  9.0,  8.5,  5.0, 5.0),
            _r("bedroom_11", "bedroom", 14.0,  8.5,  5.0, 5.0),
            _r("bedroom_12", "bedroom",  0.0, 11.5,  4.5, 5.0),
            _r("bedroom_13", "bedroom",  4.5, 11.5,  4.5, 5.0),
        ],
    },

    {
        "title": "10-Marla Bahria Town Luxury House",
        "description": "~265 m² · 15 rooms · 4 bedrooms, study, prayer room, open garden",
        "style_id": "modern",
        "material_tier": "premium",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0,  7.0, 7.5),
            _r("drawing_1",  "living",   7.0,  0.0,  5.5, 4.5),
            _r("kitchen_2",  "kitchen", 12.5,  0.0,  4.5, 4.0),
            _r("dining_3",   "dining",  12.5,  4.0,  4.5, 3.5),
            _r("lounge_4",   "living",   7.0,  4.5,  5.5, 3.0),
            _r("garden_5",   "garden",  17.0,  0.0,  4.5, 7.5),
            _r("hallway_6",  "hallway",  0.0,  7.5, 21.5, 1.5),
            _r("prayer_7",   "storage",  0.0,  9.0,  2.5, 2.5),
            _r("bathroom_8", "bathroom", 2.5,  9.0,  3.0, 3.0),
            _r("bathroom_9", "bathroom", 5.5,  9.0,  3.0, 3.0),
            _r("bathroom_10","bathroom", 8.5,  9.0,  3.0, 3.0),
            _r("study_11",   "storage", 11.5,  9.0,  3.5, 3.0),
            _r("bedroom_12", "bedroom", 15.0,  9.0,  6.5, 5.5),
            _r("bedroom_13", "bedroom",  0.0, 11.5,  5.5, 5.0),
            _r("bedroom_14", "bedroom",  5.5, 12.0,  9.5, 4.5),
            _r("bedroom_15", "bedroom", 15.0, 14.5,  6.5, 3.5),
        ],
    },

    {
        "title": "Joint Family House — Two Units",
        "description": "~250 m² · 14 rooms · 10-marla plot with two independent family units",
        "style_id": "haveli",
        "material_tier": "standard",
        "rooms": [
            _r("parking_0",   "parking",  0.0,  0.0,  5.0, 7.0),
            _r("living_a",    "living",   5.0,  0.0,  5.0, 4.0),
            _r("kitchen_a",   "kitchen",  5.0,  4.0,  5.0, 3.0),
            _r("living_b",    "living",  10.0,  0.0,  5.5, 4.5),
            _r("kitchen_b",   "kitchen", 10.0,  4.5,  5.5, 2.5),
            _r("garden_0",    "garden",  15.5,  0.0,  3.5, 7.0),
            _r("hallway_0",   "hallway",  0.0,  7.0, 19.0, 1.5),
            _r("bathroom_a1", "bathroom", 0.0,  8.5,  2.5, 2.8),
            _r("bathroom_a2", "bathroom", 2.5,  8.5,  2.5, 2.8),
            _r("bedroom_a1",  "bedroom",  5.0,  8.5,  5.0, 4.5),
            _r("bedroom_a2",  "bedroom",  0.0, 11.3,  5.0, 4.2),
            _r("bathroom_b1", "bathroom",10.0,  8.5,  2.8, 2.8),
            _r("bathroom_b2", "bathroom",12.8,  8.5,  2.8, 2.8),
            _r("bedroom_b1",  "bedroom", 15.6,  8.5,  3.4, 7.0),
            _r("bedroom_b2",  "bedroom", 10.0, 11.3,  5.6, 4.2),
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # LARGE HOUSES (1–2 KANAL)
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "title": "2-Bedroom Haveli",
        "description": "5 marla · 9 rooms · traditional Pakistani courtyard style with veranda and parking",
        "style_id": "haveli",
        "material_tier": "standard",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0,  2.8, 5.5),
            _r("veranda_1",  "veranda",  2.8,  0.0,  4.5, 2.0),
            _r("living_2",   "living",   2.8,  2.0,  4.5, 3.5),
            _r("kitchen_3",  "kitchen",  7.3,  0.0,  3.2, 5.5),
            _r("hallway_4",  "hallway",  0.0,  5.5, 10.5, 1.4),
            _r("bathroom_5", "bathroom", 0.0,  6.9,  2.5, 2.6),
            _r("bathroom_6", "bathroom", 2.5,  6.9,  2.5, 2.6),
            _r("bedroom_7",  "bedroom",  5.0,  6.9,  5.5, 4.0),
            _r("bedroom_8",  "bedroom",  0.0,  9.5,  5.0, 3.5),
        ],
    },

    {
        "title": "3-Bedroom Modern Villa",
        "description": "10 marla · 11 rooms · open-plan living, garden, and double garage",
        "style_id": "modern",
        "material_tier": "standard",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0,  6.0, 6.5),
            _r("living_1",   "living",   6.0,  0.0,  6.5, 5.0),
            _r("kitchen_2",  "kitchen", 12.5,  0.0,  4.0, 3.5),
            _r("dining_3",   "dining",  12.5,  3.5,  4.0, 3.0),
            _r("garden_4",   "garden",   6.0,  5.0,  6.5, 1.5),
            _r("hallway_5",  "hallway",  0.0,  6.5, 16.5, 1.5),
            _r("bathroom_6", "bathroom", 0.0,  8.0,  3.0, 3.0),
            _r("bathroom_7", "bathroom", 3.0,  8.0,  3.0, 3.0),
            _r("bedroom_8",  "bedroom",  6.0,  8.0,  5.25,5.0),
            _r("bedroom_9",  "bedroom", 11.25, 8.0,  5.25,5.0),
            _r("bedroom_10", "bedroom",  0.0, 11.0,  6.0, 4.5),
        ],
    },

    {
        "title": "1-Kanal Premium Family House",
        "description": "~395 m² · 16 rooms · 5-bedroom executive house with study and stair",
        "style_id": "modern",
        "material_tier": "premium",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0,  7.0, 8.0),
            _r("drawing_1",  "living",   7.0,  0.0,  6.0, 5.0),
            _r("kitchen_2",  "kitchen", 13.0,  0.0,  5.0, 4.5),
            _r("dining_3",   "dining",  13.0,  4.5,  5.0, 3.5),
            _r("lounge_4",   "living",   7.0,  5.0,  6.0, 3.0),
            _r("garden_5",   "garden",  18.0,  0.0,  7.0, 8.0),
            _r("hallway_6",  "hallway",  0.0,  8.0, 25.0, 1.8),
            _r("bathroom_7", "bathroom", 0.0,  9.8,  3.5, 3.5),
            _r("bathroom_8", "bathroom", 3.5,  9.8,  3.5, 3.5),
            _r("bathroom_9", "bathroom", 7.0,  9.8,  3.5, 3.5),
            _r("bathroom_10","bathroom",10.5,  9.8,  3.5, 3.5),
            _r("stair_11",   "stair",   14.0,  9.8,  4.0, 3.5),
            _r("master_12",  "bedroom", 18.0,  9.8,  7.0, 6.0),
            _r("bedroom_13", "bedroom",  0.0, 13.3,  6.0, 5.5),
            _r("bedroom_14", "bedroom",  6.0, 13.3,  6.0, 5.5),
            _r("bedroom_15", "bedroom", 12.0, 13.3,  6.0, 5.5),
        ],
    },

    {
        "title": "1-Kanal Old Lahore Mughal Haveli",
        "description": "~390 m² · 17 rooms · sandstone arches with veranda, grand living and ornate symmetry",
        "style_id": "mughal",
        "material_tier": "premium",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0,  7.0, 7.5),
            _r("veranda_1",  "veranda",  7.0,  0.0,  7.0, 3.0),
            _r("living_2",   "living",   7.0,  3.0,  7.0, 4.5),
            _r("kitchen_3",  "kitchen", 14.0,  0.0,  4.5, 4.0),
            _r("dining_4",   "dining",  14.0,  4.0,  4.5, 3.5),
            _r("garden_5",   "garden",  18.5,  0.0,  4.5, 7.5),
            _r("hallway_6",  "hallway",  0.0,  7.5, 23.0, 1.8),
            _r("storage_7",  "storage",  0.0,  9.3,  3.5, 3.5),
            _r("bathroom_8", "bathroom", 3.5,  9.3,  3.0, 3.5),
            _r("bathroom_9", "bathroom", 6.5,  9.3,  3.0, 3.5),
            _r("bathroom_10","bathroom", 9.5,  9.3,  3.0, 3.5),
            _r("bathroom_11","bathroom",12.5,  9.3,  3.0, 3.5),
            _r("master_12",  "bedroom", 15.5,  9.3,  7.5, 5.5),
            _r("bedroom_13", "bedroom",  0.0, 12.8,  5.75,5.5),
            _r("bedroom_14", "bedroom",  5.75,12.8,  5.75,5.5),
            _r("bedroom_15", "bedroom", 11.5, 12.8,  4.0, 5.5),
            _r("stair_16",   "stair",   15.5, 14.8,  7.5, 3.5),
        ],
    },

    {
        "title": "2-Kanal Farmhouse — Islamabad",
        "description": "~700 m² · 18 rooms · sprawling 6-bedroom farmhouse with courtyard garden",
        "style_id": "mediterranean",
        "material_tier": "premium",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0, 10.0, 9.0),
            _r("veranda_1",  "veranda", 10.0,  0.0,  8.0, 3.5),
            _r("drawing_2",  "living",  10.0,  3.5,  8.0, 5.5),
            _r("kitchen_3",  "kitchen", 18.0,  0.0,  6.0, 5.0),
            _r("dining_4",   "dining",  18.0,  5.0,  6.0, 4.0),
            _r("garden_5",   "garden",  24.0,  0.0,  8.0, 9.0),
            _r("hallway_6",  "hallway",  0.0,  9.0, 32.0, 2.0),
            _r("bathroom_7", "bathroom", 0.0, 11.0,  3.5, 3.5),
            _r("bathroom_8", "bathroom", 3.5, 11.0,  3.5, 3.5),
            _r("bathroom_9", "bathroom", 7.0, 11.0,  3.5, 3.5),
            _r("bathroom_10","bathroom",10.5, 11.0,  3.5, 3.5),
            _r("bathroom_11","bathroom",14.0, 11.0,  3.5, 3.5),
            _r("stair_12",   "stair",   17.5, 11.0,  4.5, 4.0),
            _r("master_13",  "bedroom", 22.0, 11.0, 10.0, 7.0),
            _r("bedroom_14", "bedroom",  0.0, 14.5,  7.0, 6.5),
            _r("bedroom_15", "bedroom",  7.0, 14.5,  7.0, 6.5),
            _r("bedroom_16", "bedroom", 14.0, 15.0,  8.0, 6.0),
            _r("bedroom_17", "bedroom", 22.0, 18.0, 10.0, 5.5),
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # APARTMENTS & SPECIAL TYPES
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "title": "Studio Apartment",
        "description": "Compact 82 m² · 6 rooms · modern single-occupancy with balcony",
        "style_id": "modern",
        "material_tier": "budget",
        "rooms": [
            _r("living_0",   "living",   0.0,  0.0,  5.5, 4.0),
            _r("kitchen_1",  "kitchen",  5.5,  0.0,  3.0, 4.0),
            _r("balcony_2",  "balcony",  8.5,  0.0,  1.8, 4.0),
            _r("hallway_3",  "hallway",  0.0,  4.0, 10.3, 1.2),
            _r("bathroom_4", "bathroom", 0.0,  5.2,  2.5, 2.5),
            _r("bedroom_5",  "bedroom",  2.5,  5.2,  7.8, 4.5),
        ],
    },

    {
        "title": "2-Bedroom City Apartment",
        "description": "~110 m² · 8 rooms · compact urban apartment with open-plan kitchen and balcony",
        "style_id": "modern",
        "material_tier": "standard",
        "rooms": [
            _r("living_0",   "living",   0.0,  0.0,  6.5, 4.5),
            _r("kitchen_1",  "kitchen",  6.5,  0.0,  4.0, 4.5),
            _r("balcony_2",  "balcony", 10.5,  0.0,  2.0, 4.5),
            _r("hallway_3",  "hallway",  0.0,  4.5, 12.5, 1.3),
            _r("bathroom_4", "bathroom", 0.0,  5.8,  2.5, 2.5),
            _r("bathroom_5", "bathroom", 2.5,  5.8,  2.5, 2.5),
            _r("bedroom_6",  "bedroom",  5.0,  5.8,  7.5, 4.5),
            _r("bedroom_7",  "bedroom",  0.0,  8.3,  5.0, 4.0),
        ],
    },

    {
        "title": "3-Bedroom High-Rise Apartment Floor",
        "description": "~165 m² · 11 rooms · mid-to-high-rise floor plan with balconies on both ends",
        "style_id": "modern",
        "material_tier": "standard",
        "rooms": [
            _r("balcony_0",  "balcony",  0.0,  0.0,  1.8, 5.5),
            _r("living_1",   "living",   1.8,  0.0,  6.5, 4.0),
            _r("dining_2",   "dining",   1.8,  4.0,  6.5, 1.5),
            _r("kitchen_3",  "kitchen",  8.3,  0.0,  4.0, 5.5),
            _r("balcony_4",  "balcony", 12.3,  0.0,  1.8, 5.5),
            _r("hallway_5",  "hallway",  0.0,  5.5, 14.1, 1.3),
            _r("bathroom_6", "bathroom", 0.0,  6.8,  2.5, 2.8),
            _r("bathroom_7", "bathroom", 2.5,  6.8,  2.5, 2.8),
            _r("bedroom_8",  "bedroom",  5.0,  6.8,  9.1, 4.5),
            _r("bedroom_9",  "bedroom",  0.0,  9.6,  5.0, 4.5),
            _r("bedroom_10", "bedroom",  5.0, 11.3,  9.1, 3.0),
        ],
    },

    {
        "title": "Penthouse — Open Plan Luxury",
        "description": "~230 m² · 12 rooms · 3-bedroom penthouse with wraparound terrace and premium finishes",
        "style_id": "modern",
        "material_tier": "premium",
        "rooms": [
            _r("terrace_0",  "balcony",  0.0,  0.0, 18.0, 3.0),
            _r("living_1",   "living",   0.0,  3.0,  8.0, 5.0),
            _r("dining_2",   "dining",   8.0,  3.0,  5.0, 5.0),
            _r("kitchen_3",  "kitchen", 13.0,  3.0,  5.0, 5.0),
            _r("hallway_4",  "hallway",  0.0,  8.0, 18.0, 1.5),
            _r("bathroom_5", "bathroom", 0.0,  9.5,  3.0, 3.0),
            _r("bathroom_6", "bathroom", 3.0,  9.5,  3.0, 3.0),
            _r("bathroom_7", "bathroom", 6.0,  9.5,  3.0, 3.0),
            _r("master_8",   "bedroom",  9.0,  9.5,  9.0, 6.0),
            _r("bedroom_9",  "bedroom",  0.0, 12.5,  5.0, 5.0),
            _r("bedroom_10", "bedroom",  5.0, 12.5,  4.0, 5.0),
            _r("study_11",   "storage",  0.0, 17.5, 18.0, 2.5),
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # STYLE-FORWARD SHOWCASE
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "title": "4-Bedroom Mediterranean Family Home",
        "description": "12 marla · 14 rooms · stucco walls, terracotta tiles, shaded garden and veranda",
        "style_id": "mediterranean",
        "material_tier": "standard",
        "rooms": [
            _r("parking_0",  "parking",   0.0,  0.0,  5.5, 6.5),
            _r("veranda_1",  "veranda",   5.5,  0.0,  5.0, 2.2),
            _r("living_2",   "living",    5.5,  2.2,  5.0, 4.3),
            _r("kitchen_3",  "kitchen",  10.5,  0.0,  4.0, 3.5),
            _r("dining_4",   "dining",   10.5,  3.5,  4.0, 3.0),
            _r("garden_5",   "garden",   14.5,  0.0,  4.0, 6.5),
            _r("hallway_6",  "hallway",   0.0,  6.5, 18.5, 1.5),
            _r("bathroom_7", "bathroom",  0.0,  8.0,  3.0, 3.0),
            _r("bathroom_8", "bathroom",  3.0,  8.0,  3.0, 3.0),
            _r("bathroom_9", "bathroom",  6.0,  8.0,  3.0, 3.0),
            _r("bedroom_10", "bedroom",   9.0,  8.0,  4.75,5.0),
            _r("bedroom_11", "bedroom",  13.75, 8.0,  4.75,5.0),
            _r("bedroom_12", "bedroom",   0.0, 11.0,  4.5, 4.5),
            _r("bedroom_13", "bedroom",   4.5, 11.0,  4.5, 4.5),
        ],
    },

    {
        "title": "Victorian 4-Bedroom Manor",
        "description": "~320 m² · 15 rooms · timber, steep roofs, grand double drawing room",
        "style_id": "victorian",
        "material_tier": "premium",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0,  7.0, 8.0),
            _r("veranda_1",  "veranda",  7.0,  0.0,  7.0, 2.5),
            _r("drawing_2",  "living",   7.0,  2.5,  7.0, 5.5),
            _r("kitchen_3",  "kitchen", 14.0,  0.0,  5.0, 4.5),
            _r("dining_4",   "dining",  14.0,  4.5,  5.0, 3.5),
            _r("garden_5",   "garden",  19.0,  0.0,  4.5, 8.0),
            _r("hallway_6",  "hallway",  0.0,  8.0, 23.5, 1.8),
            _r("bathroom_7", "bathroom", 0.0,  9.8,  3.0, 3.5),
            _r("bathroom_8", "bathroom", 3.0,  9.8,  3.0, 3.5),
            _r("bathroom_9", "bathroom", 6.0,  9.8,  3.0, 3.5),
            _r("bathroom_10","bathroom", 9.0,  9.8,  3.0, 3.5),
            _r("master_11",  "bedroom", 12.0,  9.8, 11.5, 6.0),
            _r("bedroom_12", "bedroom",  0.0, 13.3,  6.0, 5.5),
            _r("bedroom_13", "bedroom",  6.0, 13.3,  6.0, 5.5),
            _r("bedroom_14", "bedroom", 12.0, 15.8, 11.5, 3.0),
        ],
    },

    {
        "title": "Grand Mughal Residence",
        "description": "~1 kanal · 17 rooms · monumental sandstone arches, vaulted ceilings, ornate symmetry",
        "style_id": "mughal",
        "material_tier": "premium",
        "rooms": [
            _r("parking_0",  "parking",  0.0,  0.0,  7.0, 7.5),
            _r("veranda_1",  "veranda",  7.0,  0.0,  7.0, 3.0),
            _r("living_2",   "living",   7.0,  3.0,  7.0, 4.5),
            _r("kitchen_3",  "kitchen", 14.0,  0.0,  4.5, 4.0),
            _r("dining_4",   "dining",  14.0,  4.0,  4.5, 3.5),
            _r("garden_5",   "garden",  18.5,  0.0,  4.5, 7.5),
            _r("hallway_6",  "hallway",  0.0,  7.5, 23.0, 1.8),
            _r("storage_7",  "storage",  0.0,  9.3,  3.5, 3.5),
            _r("bathroom_8", "bathroom", 3.5,  9.3,  3.0, 3.5),
            _r("bathroom_9", "bathroom", 6.5,  9.3,  3.0, 3.5),
            _r("bathroom_10","bathroom", 9.5,  9.3,  3.0, 3.5),
            _r("bathroom_11","bathroom",12.5,  9.3,  3.0, 3.5),
            _r("master_12",  "bedroom", 15.5,  9.3,  7.5, 5.5),
            _r("bedroom_13", "bedroom",  0.0, 12.8,  5.75,5.5),
            _r("bedroom_14", "bedroom",  5.75,12.8,  5.75,5.5),
            _r("bedroom_15", "bedroom", 11.5, 12.8,  4.0, 5.5),
            _r("stair_16",   "stair",   15.5, 14.8,  7.5, 3.5),
        ],
    },
]


# ── Seeder ────────────────────────────────────────────────────────────────────

def seed():
    try:
        from pymongo import MongoClient
        import gridfs
    except ImportError:
        print("ERROR: pymongo is required.  Run:  pip install pymongo")
        sys.exit(1)

    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=8000)

    try:
        db = client.get_default_database()
    except Exception:
        db_name = os.getenv("MONGODB_DB", "")
        if not db_name:
            parsed  = urlparse(MONGODB_URI)
            db_name = parsed.path.lstrip("/").split("?")[0] or "test"
        db = client[db_name]

    fs        = gridfs.GridFS(db, collection="floorPlanFiles")
    plans_col = db["floorplans"]

    print(f"[seed] Connected to database: {db.name}")
    print(f"[seed] {len(SAMPLE_PLANS)} plans defined — checking for existing records…\n")

    seeded = skipped = 0
    for plan in SAMPLE_PLANS:
        if plans_col.find_one({"title": plan["title"]}):
            print(f"  SKIP  {plan['title']}")
            skipped += 1
            continue

        print(f"  SEED  {plan['title']} …", end=" ", flush=True)
        png_bytes = _render_png(plan["rooms"])
        print(f"{len(png_bytes) // 1024} KB PNG", end=" ", flush=True)

        filename = plan["title"].lower().replace(" ", "-").replace("—", "").replace("·", "") \
                       .replace("/", "-").strip("-") + ".png"
        file_id  = fs.put(png_bytes, filename=filename, content_type="image/png")

        studio_data = json.dumps({
            "format":            "architext-studio-project",
            "version":           1,
            "prompt":            plan["description"],
            "generatedAt":       datetime.now(timezone.utc).isoformat(),
            "architectureStyle": plan["style_id"],
            "materialTier":      plan["material_tier"],
            "rooms":             plan["rooms"],
            "llm": {
                "rooms":        plan["rooms"],
                "totalAreaM2":  round(sum(r["area"] for r in plan["rooms"]), 1),
                "styleId":      plan["style_id"],
                "materialTier": plan["material_tier"],
            },
            "gnn": None,
        })

        plans_col.insert_one({
            "title":         plan["title"],
            "description":   plan["description"],
            "originalName":  filename,
            "fileId":        file_id,
            "mimeType":      "image/png",
            "size":          len(png_bytes),
            "uploaderName":  "Architext",
            "uploaderEmail": "sample@architext.ai",
            "uploadedAt":    datetime.now(timezone.utc),
            "isPublic":      True,
            "studioData":    studio_data,
            "versions":      [],
            "reactions":     [],
            "comments":      [],
        })
        print("✓")
        seeded += 1

    print(f"\n[seed] Done — {seeded} seeded, {skipped} already existed.")


if __name__ == "__main__":
    seed()
