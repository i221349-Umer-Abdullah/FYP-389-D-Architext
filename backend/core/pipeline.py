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

# Shared GNN instance
_gnn = get_real_gnn()


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
    Move `isolated` room so it sits flush against `anchor` on the nearest side.
    Modifies isolated room's x/y in-place.
    """
    ax1, ax2 = anchor["x"], anchor["x"] + anchor["width"]
    ay1, ay2 = anchor["y"], anchor["y"] + anchor["height"]
    ix1, ix2 = isolated["x"], isolated["x"] + isolated["width"]
    iy1, iy2 = isolated["y"], isolated["y"] + isolated["height"]

    # Find which side of anchor is closest to isolated room centre
    icx = (ix1 + ix2) / 2
    icy = (iy1 + iy2) / 2

    dist_left  = abs(icx - ax1)
    dist_right = abs(icx - ax2)
    dist_top   = abs(icy - ay2)
    dist_bot   = abs(icy - ay1)

    best = min(dist_left, dist_right, dist_top, dist_bot)

    if best == dist_right:
        isolated["x"] = round(ax2, 2)
        isolated["y"] = round(ay1, 2)
    elif best == dist_left:
        isolated["x"] = round(ax1 - isolated["width"], 2)
        isolated["y"] = round(ay1, 2)
    elif best == dist_top:
        isolated["y"] = round(ay2, 2)
        isolated["x"] = round(ax1, 2)
    else:
        isolated["y"] = round(ay1 - isolated["height"], 2)
        isolated["x"] = round(ax1, 2)


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
                       generator_mode: Optional[str] = None) -> None:
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
