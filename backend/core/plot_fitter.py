"""
Plot Constraint Fitter — Layer 3.5

Scales and repositions a generated room layout to fit within a given
plot boundary (plot_w × plot_h metres).

Algorithm
---------
1. Normalize   — shift all rooms so the bounding box starts at (0, 0).
2. Scale        — uniformly shrink/grow the layout to fill the available
                  area (plot minus margin). Topology is fully preserved:
                  rooms that were adjacent stay adjacent, relative
                  positions unchanged.
3. Min-size     — restore rooms that shrank below habitable minimums.
                  This can cause new overlaps; handled in step 4.
4. Bounded push-apart — the existing push-apart logic, but clamped so
                  rooms can never cross the plot boundary. Maintains
                  adjacency while resolving overlaps.
5. Final clamp  — hard-clip any room still partially outside.
6. Re-normalize — shift back so the whole layout sits within
                  (MARGIN, MARGIN) .. (plot_w - MARGIN, plot_h - MARGIN).

The "logical quality" guarantee: because steps 1-2 preserve the
LLM/GNN topology and steps 3-5 only apply the minimum perturbation
needed, the result looks like the original layout resized to the plot —
not a random scatter.
"""

import math
from typing import List, Dict

MARGIN   = 0.35   # metres from each plot edge (≈1 ft)
PADDING  = 0.05   # gap between rooms after push-apart
MAX_PASSES = 80

MIN_SIZES: Dict[str, tuple] = {
    "bedroom":  (2.5, 2.5),
    "bathroom": (1.5, 1.5),
    "living":   (3.0, 3.0),
    "kitchen":  (2.0, 2.0),
    "balcony":  (1.2, 1.2),
    "storage":  (0.9, 0.9),
    "parking":  (2.4, 4.8),
    "garden":   (2.0, 2.0),
    "stair":    (1.0, 2.0),
    "veranda":  (1.5, 1.5),
    "hallway":  (1.0, 1.5),
    "dining":   (2.5, 2.5),
}
DEFAULT_MIN = (1.2, 1.2)


def fit_rooms_to_plot(rooms: List[dict], plot_w: float, plot_h: float) -> List[dict]:
    """
    Return a new list of rooms fitted within plot_w × plot_h metres.
    Rooms are dicts with keys: x, y, width, height, type (and others preserved).
    """
    if not rooms:
        return rooms

    avail_w = max(plot_w  - 2 * MARGIN, 1.0)
    avail_h = max(plot_h  - 2 * MARGIN, 1.0)

    # Deep-copy so we don't mutate the caller's dicts
    rs = [dict(r) for r in rooms]

    # ── Step 1: Normalize to origin ──────────────────────────────────────
    min_x = min(r["x"] for r in rs)
    min_y = min(r["y"] for r in rs)
    for r in rs:
        r["x"] = round(r["x"] - min_x, 3)
        r["y"] = round(r["y"] - min_y, 3)

    # ── Step 2: Uniform scale ────────────────────────────────────────────
    curr_w = max(r["x"] + r["width"]  for r in rs)
    curr_h = max(r["y"] + r["height"] for r in rs)

    if curr_w > 0 and curr_h > 0:
        scale = min(avail_w / curr_w, avail_h / curr_h)
        for r in rs:
            r["x"]      = round(r["x"]      * scale, 3)
            r["y"]      = round(r["y"]      * scale, 3)
            r["width"]  = round(r["width"]  * scale, 3)
            r["height"] = round(r["height"] * scale, 3)

    # ── Step 3: Enforce minimum room sizes ───────────────────────────────
    for r in rs:
        rtype = r.get("type", "other")
        min_w, min_h = MIN_SIZES.get(rtype, DEFAULT_MIN)
        r["width"]  = max(r["width"],  min_w)
        r["height"] = max(r["height"], min_h)

    # ── Step 3.5: Grid-based scale-down ──────────────────────────────────
    # If any room is larger than its fair share of a sqrt(N)×sqrt(N) grid,
    # shrink it so all N rooms can physically pack into the available area.
    # This handles the mode-collapse case where the GNN/LLM places every
    # room at the same position: the uniform scale in step 2 scaled one
    # room's bounding box to fill the plot, making each room plot-sized.
    if len(rs) > 1:
        cols = math.ceil(math.sqrt(len(rs)))
        rows = math.ceil(len(rs) / cols)
        grid_max_w = (avail_w - PADDING * (cols - 1)) / cols
        grid_max_h = (avail_h - PADDING * (rows - 1)) / rows
        for r in rs:
            if r["width"] > grid_max_w or r["height"] > grid_max_h:
                rtype = r.get("type", "other")
                min_w, min_h = MIN_SIZES.get(rtype, DEFAULT_MIN)
                s = min(grid_max_w / r["width"], grid_max_h / r["height"])
                r["width"]  = round(max(r["width"]  * s, min_w), 3)
                r["height"] = round(max(r["height"] * s, min_h), 3)

    # ── Step 3.6: Break position degeneracy for coincident rooms ─────────
    # When multiple rooms share the exact same (x, y) the push-apart cannot
    # determine a direction to move them. Pre-place them in a grid so each
    # room has a distinct starting position before push-apart runs.
    pos_seen: dict = {}
    for idx, r in enumerate(rs):
        key = (r["x"], r["y"])
        if key not in pos_seen:
            pos_seen[key] = []
        pos_seen[key].append(idx)
    for key, group in pos_seen.items():
        if len(group) > 1:
            g_cols = math.ceil(math.sqrt(len(group)))
            for gi, gidx in enumerate(group):
                gc = gi % g_cols
                gr = gi // g_cols
                rs[gidx]["x"] = round(key[0] + gc * (rs[gidx]["width"]  + PADDING), 3)
                rs[gidx]["y"] = round(key[1] + gr * (rs[gidx]["height"] + PADDING), 3)

    # ── Step 4: Bounded push-apart ───────────────────────────────────────
    for _ in range(MAX_PASSES):
        moved = False
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                a, b = rs[i], rs[j]
                ax1, ax2 = a["x"], a["x"] + a["width"]
                ay1, ay2 = a["y"], a["y"] + a["height"]
                bx1, bx2 = b["x"], b["x"] + b["width"]
                by1, by2 = b["y"], b["y"] + b["height"]
                ox = min(ax2, bx2) - max(ax1, bx1)
                oy = min(ay2, by2) - max(ay1, by1)
                if ox <= 0 or oy <= 0:
                    continue
                moved = True
                if ox < oy:
                    shift = (ox + PADDING) / 2.0
                    if a["x"] <= b["x"]:
                        a["x"] = max(0.0,            round(a["x"] - shift, 3))
                        b["x"] = min(avail_w - b["width"], round(b["x"] + shift, 3))
                    else:
                        a["x"] = min(avail_w - a["width"], round(a["x"] + shift, 3))
                        b["x"] = max(0.0,            round(b["x"] - shift, 3))
                else:
                    shift = (oy + PADDING) / 2.0
                    if a["y"] <= b["y"]:
                        a["y"] = max(0.0,             round(a["y"] - shift, 3))
                        b["y"] = min(avail_h - b["height"], round(b["y"] + shift, 3))
                    else:
                        a["y"] = min(avail_h - a["height"], round(a["y"] + shift, 3))
                        b["y"] = max(0.0,             round(b["y"] - shift, 3))
        if not moved:
            break

    # ── Step 5: Hard clamp ───────────────────────────────────────────────
    for r in rs:
        r["x"] = max(0.0, min(r["x"], max(0.0, avail_w - r["width"])))
        r["y"] = max(0.0, min(r["y"], max(0.0, avail_h - r["height"])))
        r["x"] = round(r["x"], 3)
        r["y"] = round(r["y"], 3)

    # ── Step 6: Shift back with margin ───────────────────────────────────
    for r in rs:
        r["x"] = round(r["x"] + MARGIN, 3)
        r["y"] = round(r["y"] + MARGIN, 3)
        # Update area field if present
        if "area" in r:
            r["area"] = round(r["width"] * r["height"], 2)

    return rs
