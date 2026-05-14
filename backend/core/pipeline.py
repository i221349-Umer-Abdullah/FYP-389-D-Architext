"""
4-Layer Pipeline Orchestrator.

Coordinates the full generation pipeline:
  Layer 1: NLP  → structured spec
  Layer 2: GNN  → room graph (mock until model trains, then real)
  Layer 3: Validate (basic rules for now)
  Layer 4: IFC export → .ifc file + room summary

The pipeline runs as a background async task and updates the Job object
throughout so the status endpoint can report real-time progress.
"""

import os
import sys
import math as _math
import re as _re
import asyncio
from pathlib import Path
from typing import Optional

# Note: sys.path is already set by backend/__init__.py which runs first.
# This redundant guard is kept for safety when pipeline.py is run standalone.
_ROOT = Path(__file__).parent.parent.parent.resolve()
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from backend.core.job_manager    import Job, JobStatus
from backend.core.nlp_adapter    import get_nlp_adapter
from backend.core.mock_gnn       import MockGNNAdapter
from backend.core.real_gnn       import get_real_gnn
from backend.core.spec_converter import normalise_spec

# Generator mode: "llm" uses the LLM adapter (default), "gnn" uses the trained GNN.
# Override with the GENERATOR_MODE environment variable.
DEFAULT_GENERATOR_MODE = os.getenv("GENERATOR_MODE", "llm")

IFC_OUTPUT_DIR = _ROOT / "output" / "api_generated"
PNG_OUTPUT_DIR = _ROOT / "output" / "api_generated"
IFC_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def _extract_plot_from_text(text: str):
    """
    Return (plot_w, plot_h) in metres if a plot size is mentioned in the text,
    otherwise return (None, None). Uses aspect ratio 1.8 (width:depth) for
    area-based units, matching the frontend plotUnits.ts conversion.
    """
    ASPECT = 1.8

    def area_to_dims(area_m2: float):
        h = _math.sqrt(area_m2 / ASPECT)
        return round(h * ASPECT, 2), round(h, 2)

    # Marla  (1 marla = 25.2929 m²)
    m = _re.search(r'(\d+(?:\.\d+)?)\s*marla', text, _re.IGNORECASE)
    if m:
        return area_to_dims(float(m.group(1)) * 25.2929)

    # Kanal  (1 kanal = 505.857 m²)
    m = _re.search(r'(\d+(?:\.\d+)?)\s*kanal', text, _re.IGNORECASE)
    if m:
        return area_to_dims(float(m.group(1)) * 505.857)

    # Square metres: "150 sqm", "150 m²", "150 sq m", "150 square metres"
    m = _re.search(
        r'(\d+(?:\.\d+)?)\s*(?:sqm|m²|sq\.?\s*m|square\s*met(?:re|er)s?)',
        text, _re.IGNORECASE)
    if m:
        return area_to_dims(float(m.group(1)))

    # Metres × metres: "10m x 8m", "10 by 8 metres", "10×8m"
    m = _re.search(
        r'(\d+(?:\.\d+)?)\s*m?\s*[x×by]\s*(\d+(?:\.\d+)?)\s*m',
        text, _re.IGNORECASE)
    if m:
        return float(m.group(1)), float(m.group(2))

    return None, None


# Shared GNN instance, loaded lazily so LLM-only workflows can run without
# requiring local GNN checkpoint files at backend startup.
_gnn = None


def _validate_and_fix(room_graph: dict, spec: dict) -> dict:
    """
    Layer 3 — Smart Validator.
    1. Enforce minimum room sizes.
    2. Push overlapping rooms apart (iterative, max 25 passes).
    3. Inject missing required room types from spec.
    """
    rooms = room_graph.get("rooms", [])

    # 1. Minimum room sizes
    MIN_SIZES = {
        "bedroom": (2.5, 2.5), "bathroom": (1.5, 1.5),
        "living":  (3.0, 3.0), "kitchen":  (2.0, 2.0),
        "balcony": (1.5, 1.5), "parking":  (2.5, 5.0),
        "garden":  (3.0, 3.0), "storage":  (1.0, 1.0),
    }
    for r in rooms:
        rtype = r.get("type", "other")
        min_w, min_h = MIN_SIZES.get(rtype, (1.0, 1.0))
        r["width"]  = max(r.get("width",  min_w), min_w)
        r["height"] = max(r.get("height", min_h), min_h)

    # 2. Push-apart: iteratively resolve overlaps
    MAX_PASSES = 60
    PADDING    = 0.05  # minimal gap — rooms should nearly share walls
    for _ in range(MAX_PASSES):
        moved = False
        for i in range(len(rooms)):
            for j in range(i + 1, len(rooms)):
                a, b = rooms[i], rooms[j]
                ax1, ax2 = a["x"], a["x"] + a["width"]
                ay1, ay2 = a["y"], a["y"] + a["height"]
                bx1, bx2 = b["x"], b["x"] + b["width"]
                by1, by2 = b["y"], b["y"] + b["height"]
                ox = min(ax2, bx2) - max(ax1, bx1)
                oy = min(ay2, by2) - max(ay1, by1)
                if ox <= 0 or oy <= 0:
                    continue
                if ox < oy:
                    shift = (ox + PADDING) / 2.0
                    if a["x"] < b["x"]:
                        a["x"] = round(a["x"] - shift, 2)
                        b["x"] = round(b["x"] + shift, 2)
                    else:
                        a["x"] = round(a["x"] + shift, 2)
                        b["x"] = round(b["x"] - shift, 2)
                else:
                    shift = (oy + PADDING) / 2.0
                    if a["y"] < b["y"]:
                        a["y"] = round(a["y"] - shift, 2)
                        b["y"] = round(b["y"] + shift, 2)
                    else:
                        a["y"] = round(a["y"] + shift, 2)
                        b["y"] = round(b["y"] - shift, 2)
                moved = True
        if not moved:
            break

    # 3. Inject missing spec-required room types
    present = {r["type"] for r in rooms}
    DEFAULTS = [
        ("bedroom",  9.0, 3.0, 3.0),
        ("bathroom", 4.5, 1.8, 2.5),
        ("living",  15.0, 4.0, 3.75),
        ("kitchen",  9.0, 3.0, 3.0),
    ]
    max_x    = max((r["x"] + r["width"] for r in rooms), default=0.0)
    insert_y = 0.0
    for rtype, area, w, h in DEFAULTS:
        if int(spec.get(rtype, 0)) > 0 and rtype not in present:
            rooms.append({
                "id": f"{rtype}_injected", "type": rtype,
                "x": round(max_x + 0.5, 2), "y": round(insert_y, 2),
                "width": w, "height": h, "area": area,
            })
            insert_y += h + 0.5

    # 3b. Close gaps introduced by the LLM before testing connectivity
    rooms = _close_gaps(rooms, max_gap=8.0)

    # 4. Connectivity enforcement — every room must share an edge with at least one other
    if len(rooms) > 1:
        # Build undirected adjacency graph (index-based)
        n = len(rooms)
        adj: list[set] = [set() for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                if _rooms_are_adjacent(rooms[i], rooms[j]):
                    adj[i].add(j)
                    adj[j].add(i)

        # BFS to find all connected components
        visited  = [False] * n
        clusters = []
        for start in range(n):
            if not visited[start]:
                queue   = [start]
                cluster = []
                while queue:
                    node = queue.pop(0)
                    if visited[node]:
                        continue
                    visited[node] = True
                    cluster.append(node)
                    queue.extend(adj[node] - set([node]))
                clusters.append(cluster)

        # Main cluster = largest component
        main_cluster = max(clusters, key=len)
        main_indices = set(main_cluster)

        # Snap isolated rooms to the nearest room in the main cluster
        for cluster in clusters:
            if cluster == main_cluster:
                continue
            for iso_idx in cluster:
                # Find nearest main-cluster room by centre distance
                iso = rooms[iso_idx]
                icx = iso["x"] + iso["width"]  / 2
                icy = iso["y"] + iso["height"] / 2
                best_anchor = min(
                    main_indices,
                    key=lambda k: (
                        (rooms[k]["x"] + rooms[k]["width"]  / 2 - icx) ** 2 +
                        (rooms[k]["y"] + rooms[k]["height"] / 2 - icy) ** 2
                    )
                )
                _snap_to_adjacent(iso, rooms[best_anchor])
                # Add to main cluster so subsequent rooms can snap to it
                main_indices.add(iso_idx)

    # 4b. Close any residual gaps left after snapping
    rooms = _close_gaps(rooms, max_gap=2.0)

    # 5. Normalize: shift all rooms so minimum x and y are ≥ 0.
    #    Prevents negative-coordinate rooms from being clamped to 0 in downstream
    #    consumers (e.g. room_graph_to_ifc._validate), which causes 3D overlap.
    if rooms:
        min_x = min(r["x"] for r in rooms)
        min_y = min(r["y"] for r in rooms)
        if min_x < 0:
            for r in rooms:
                r["x"] = round(r["x"] - min_x, 2)
        if min_y < 0:
            for r in rooms:
                r["y"] = round(r["y"] - min_y, 2)

    room_graph["rooms"] = rooms
    return room_graph


def _rooms_are_adjacent(a: dict, b: dict, tol: float = 0.6) -> bool:
    """
    Two rooms are considered adjacent if their edges are within `tol` metres
    AND their interiors overlap in the perpendicular axis (they actually share wall).
    """
    ax1, ax2 = a["x"], a["x"] + a["width"]
    ay1, ay2 = a["y"], a["y"] + a["height"]
    bx1, bx2 = b["x"], b["x"] + b["width"]
    by1, by2 = b["y"], b["y"] + b["height"]

    # Check left/right adjacency: x-edges within tol, y-ranges overlap
    x_close = (abs(ax2 - bx1) <= tol) or (abs(bx2 - ax1) <= tol)
    y_overlap = min(ay2, by2) - max(ay1, by1) > 0
    if x_close and y_overlap:
        return True

    # Check top/bottom adjacency: y-edges within tol, x-ranges overlap
    y_close = (abs(ay2 - by1) <= tol) or (abs(by2 - ay1) <= tol)
    x_overlap = min(ax2, bx2) - max(ax1, bx1) > 0
    if y_close and x_overlap:
        return True

    return False


def _snap_to_adjacent(isolated: dict, anchor: dict) -> None:
    """
    Move `isolated` room flush against `anchor` using the axis with the smaller gap.
    When x-ranges overlap, snap vertically; when y-ranges overlap, snap horizontally;
    otherwise snap on whichever axis has the smaller gap.
    """
    ax1, ax2 = anchor["x"],   anchor["x"]   + anchor["width"]
    ay1, ay2 = anchor["y"],   anchor["y"]   + anchor["height"]
    ix1, ix2 = isolated["x"], isolated["x"] + isolated["width"]
    iy1, iy2 = isolated["y"], isolated["y"] + isolated["height"]

    x_overlap = min(ix2, ax2) - max(ix1, ax1)
    y_overlap = min(iy2, ay2) - max(iy1, ay1)

    if x_overlap > 0:
        # Rooms share an x-band → snap vertically (up or down)
        if iy1 >= ay2:
            isolated["y"] = round(ay2, 2)
        else:
            isolated["y"] = round(ay1 - isolated["height"], 2)
    elif y_overlap > 0:
        # Rooms share a y-band → snap horizontally (left or right)
        if ix1 >= ax2:
            isolated["x"] = round(ax2, 2)
        else:
            isolated["x"] = round(ax1 - isolated["width"], 2)
    else:
        # Diagonal — snap on the axis with the smaller gap, align other axis to anchor edge
        h_gap = max(ix1 - ax2, ax1 - ix2)
        v_gap = max(iy1 - ay2, ay1 - iy2)
        if h_gap <= v_gap:
            isolated["x"] = round(ax2, 2) if ix1 >= ax2 else round(ax1 - isolated["width"], 2)
            isolated["y"] = round(ay1, 2)
        else:
            isolated["y"] = round(ay2, 2) if iy1 >= ay2 else round(ay1 - isolated["height"], 2)
            isolated["x"] = round(ax1, 2)


def _close_gaps(rooms: list, max_gap: float = 3.0) -> list:
    """
    Slide rooms flush against each other to eliminate internal gaps introduced
    by the LLM.  Only moves a room toward a neighbour when:
      - They share significant overlap on the perpendicular axis (≥ 0.3 m)
      - The gap on the snap axis is ≤ max_gap
      - The move would not create an overlap with any other room
    Runs in alternating x / y passes until stable (max 30 iterations).
    """
    if len(rooms) < 2:
        return rooms

    TOUCH = 0.05  # gap threshold considered "already touching"

    def true_overlap(r, others):
        rx1, rx2 = r["x"], r["x"] + r["width"]
        ry1, ry2 = r["y"], r["y"] + r["height"]
        for o in others:
            if o is r:
                continue
            ox1, ox2 = o["x"], o["x"] + o["width"]
            oy1, oy2 = o["y"], o["y"] + o["height"]
            if (rx2 - ox1 > TOUCH and ox2 - rx1 > TOUCH and
                    ry2 - oy1 > TOUCH and oy2 - ry1 > TOUCH):
                return True
        return False

    for _ in range(30):
        moved = False

        # ── Y-axis: slide rooms downward (toward lower y) ────────────────────
        for r in sorted(rooms, key=lambda r: r["y"]):
            ry1 = r["y"]
            rx1, rx2 = r["x"], r["x"] + r["width"]
            best_top = None          # highest y-top among valid lower neighbours
            for o in rooms:
                if o is r:
                    continue
                oy2 = o["y"] + o["height"]
                ox1, ox2 = o["x"], o["x"] + o["width"]
                x_ov = min(rx2, ox2) - max(rx1, ox1)
                if x_ov >= 0.3 and oy2 <= ry1 + 0.01:
                    gap = ry1 - oy2
                    if gap <= max_gap:
                        best_top = oy2 if best_top is None else max(best_top, oy2)
            if best_top is not None and ry1 - best_top > TOUCH:
                old = r["y"]
                r["y"] = round(best_top, 2)
                if true_overlap(r, rooms):
                    r["y"] = old
                else:
                    moved = True

        # ── X-axis: slide rooms leftward (toward lower x) ────────────────────
        for r in sorted(rooms, key=lambda r: r["x"]):
            rx1 = r["x"]
            ry1, ry2 = r["y"], r["y"] + r["height"]
            best_right = None
            for o in rooms:
                if o is r:
                    continue
                ox2 = o["x"] + o["width"]
                oy1, oy2 = o["y"], o["y"] + o["height"]
                y_ov = min(ry2, oy2) - max(ry1, oy1)
                if y_ov >= 0.3 and ox2 <= rx1 + 0.01:
                    gap = rx1 - ox2
                    if gap <= max_gap:
                        best_right = ox2 if best_right is None else max(best_right, ox2)
            if best_right is not None and rx1 - best_right > TOUCH:
                old = r["x"]
                r["x"] = round(best_right, 2)
                if true_overlap(r, rooms):
                    r["x"] = old
                else:
                    moved = True

        if not moved:
            break

    return rooms


_ROOM_COLOURS = {
    "living": "#AED6F1", "kitchen": "#A9DFBF", "dining": "#D5F5E3",
    "bedroom": "#F9E79F", "bathroom": "#FADBD8", "hallway": "#D7DBDD",
    "balcony": "#A9CCE3", "garden": "#82E0AA", "parking": "#CCD1D1",
    "storage": "#D2B4DE", "stair": "#F0B27A", "veranda": "#85C1E9",
    "other": "#EAECEE",
}


def _render_png(room_graph: dict, output_path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches

    rooms = room_graph.get("rooms", [])
    if not rooms:
        return

    fig, ax = plt.subplots(figsize=(8, 8))
    xs = [r["x"] for r in rooms]
    ys = [r["y"] for r in rooms]
    xe = [r["x"] + r["width"] for r in rooms]
    ye = [r["y"] + r["height"] for r in rooms]

    margin = 1.0
    ax.set_xlim(min(xs) - margin, max(xe) + margin)
    ax.set_ylim(min(ys) - margin, max(ye) + margin)
    ax.set_aspect("equal")
    ax.grid(True, linestyle="--", alpha=0.3, color="#999")
    ax.set_xlabel("metres", fontsize=8)
    ax.set_ylabel("metres", fontsize=8)

    for r in rooms:
        rtype = r.get("type", "other")
        colour = _ROOM_COLOURS.get(rtype, "#EAECEE")
        rect = patches.Rectangle(
            (r["x"], r["y"]), r["width"], r["height"],
            linewidth=1.5, edgecolor="#333", facecolor=colour, alpha=0.85,
        )
        ax.add_patch(rect)
        label = rtype.replace("_", " ").title()
        area = round(r.get("area", r["width"] * r["height"]), 1)
        ax.text(
            r["x"] + r["width"] / 2, r["y"] + r["height"] / 2,
            f"{label}\n{area} m\u00b2",
            ha="center", va="center", fontsize=7.5, fontweight="bold", color="#222",
        )

    total = sum(r.get("area", r["width"] * r["height"]) for r in rooms)
    ax.set_title(f"{len(rooms)} rooms  \u00b7  {round(total, 1)} m\u00b2", fontsize=10)
    plt.tight_layout()
    plt.savefig(output_path, dpi=130, bbox_inches="tight")
    plt.close(fig)


async def run_pipeline(job: Job, project_name: Optional[str] = None,
                       generator_mode: Optional[str] = None,
                       plot_width: Optional[float] = None,
                       plot_height: Optional[float] = None) -> None:
    """
    Run the full 4-layer pipeline for a given job.
    Updates job.status, job.progress, and job.preview throughout.

    generator_mode: "llm" (default) or "gnn"
      "llm" — LLM API generates rooms directly from the text prompt (Layers 1+2 combined)
      "gnn" — Original T5 NLP + StructuralGNN path
    """
    mode = (generator_mode or DEFAULT_GENERATOR_MODE).lower()

    try:
        if mode == "llm":
            # ── LLM path: Layers 1 + 2 combined ───────────────────────────────
            job.update(JobStatus.PROCESSING, "Generating layout with LLM...", 10)
            await asyncio.sleep(0)

            from backend.core.llm_adapter import generate_room_layout, spec_from_room_graph
            room_graph = await generate_room_layout(job.text)
            spec       = spec_from_room_graph(room_graph)
            job.spec   = spec

            job.update(JobStatus.PROCESSING, "LLM layout generated", 60)
            await asyncio.sleep(0)

        else:
            # ── GNN path: T5 NLP (Layer 1) + StructuralGNN (Layer 2) ──────────
            global _gnn
            if _gnn is None:
                _gnn = get_real_gnn()

            job.update(JobStatus.PROCESSING, "Layer 1: Parsing natural language...", 10)
            await asyncio.sleep(0)

            nlp  = get_nlp_adapter()
            raw  = nlp.parse(job.text)
            from backend.core.spec_converter import normalise_spec
            spec = normalise_spec(raw)
            job.spec = spec

            job.update(JobStatus.PROCESSING, "Layer 1 complete — spec extracted", 25)
            await asyncio.sleep(0)

            job.update(JobStatus.PROCESSING, "Layer 2: Generating room layout with GNN...", 40)
            await asyncio.sleep(0)

            loop       = asyncio.get_event_loop()
            room_graph = await loop.run_in_executor(None, _gnn.generate, spec)

            job.update(JobStatus.PROCESSING, "Layer 2 complete — room graph generated", 60)
            await asyncio.sleep(0)

        # ── Layer 3: Validate ──────────────────────────────────────────────────
        job.update(JobStatus.PROCESSING, "Layer 3: Validating layout...", 70)
        await asyncio.sleep(0)

        room_graph = _validate_and_fix(room_graph, spec)

        # ── Layer 3.5: Plot constraint fitting ────────────────────────────────
        # If no explicit dimensions, try to extract from the prompt text
        if not (plot_width and plot_height):
            _pw, _ph = _extract_plot_from_text(job.text)
            if _pw and _ph:
                plot_width, plot_height = _pw, _ph

        if plot_width and plot_height:
            job.update(JobStatus.PROCESSING, "Fitting layout to plot dimensions...", 75)
            await asyncio.sleep(0)
            from backend.core.plot_fitter import fit_rooms_to_plot
            fitted = fit_rooms_to_plot(room_graph["rooms"], plot_width, plot_height)
            room_graph["rooms"] = fitted

        # Lazy import of adapter (backend/core/room_graph_to_ifc.py)
        from backend.core.room_graph_to_ifc import RoomGraphToIFC
        adapter = RoomGraphToIFC()
        summary = adapter.get_room_summary(room_graph)
        job.preview = summary

        job.update(JobStatus.PROCESSING, "Layer 3 complete — layout validated", 80)
        await asyncio.sleep(0)

        # ── Layer 4a: 2D PNG Preview ───────────────────────────────────────────
        job.update(JobStatus.PROCESSING, "Rendering 2D floor plan...", 85)
        await asyncio.sleep(0)

        png_path = str(PNG_OUTPUT_DIR / f"{job.job_id}.png")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: _render_png(room_graph, png_path))
        job.preview_png = png_path

        # ── Layer 4b: IFC Export ───────────────────────────────────────────────
        job.update(JobStatus.PROCESSING, "Layer 4: Generating IFC file...", 90)
        await asyncio.sleep(0)

        pname    = project_name or f"AI {spec.get('unit_type','Building').title()}"
        ifc_path = str(IFC_OUTPUT_DIR / f"{job.job_id}.ifc")

        ifc_path = await loop.run_in_executor(
            None,
            lambda: adapter.convert(room_graph, output_path=ifc_path, project_name=pname)
        )
        job.ifc_path = ifc_path

        job.update(JobStatus.DONE, "Pipeline complete — IFC ready for download", 100)

    except Exception as e:
        import traceback
        job.error = str(e)
        job.update(JobStatus.FAILED, f"Pipeline failed: {e}", job.progress)
        traceback.print_exc()
