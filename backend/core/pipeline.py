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
from backend.core.spec_converter import normalise_spec

IFC_OUTPUT_DIR = _ROOT / "output" / "api_generated"
IFC_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Shared mock GNN instance (swap for real GNN after training)
_mock_gnn = MockGNNAdapter()


def _validate_and_fix(room_graph: dict, spec: dict) -> dict:
    """
    Layer 3 — lightweight rule-based validation.
    Full Smart Validator to be built later; this enforces minimum viability.
    """
    rooms = room_graph.get("rooms", [])
    MIN_SIZES = {
        "bedroom": (2.5, 2.5), "bathroom": (1.5, 1.5),
        "living":  (3.0, 3.0), "kitchen":  (2.0, 2.0),
    }
    for r in rooms:
        rtype = r.get("type", "other")
        min_w, min_h = MIN_SIZES.get(rtype, (1.0, 1.0))
        r["width"]  = max(r.get("width",  min_w), min_w)
        r["height"] = max(r.get("height", min_h), min_h)

    room_graph["rooms"] = rooms
    return room_graph


async def run_pipeline(job: Job, project_name: Optional[str] = None) -> None:
    """
    Run the full 4-layer pipeline for a given job.
    Updates job.status, job.progress, and job.preview throughout.
    """
    try:
        # ── Layer 1: NLP ───────────────────────────────────────────────────────
        job.update(JobStatus.PROCESSING, "Layer 1: Parsing natural language...", 10)
        await asyncio.sleep(0)

        nlp  = get_nlp_adapter()
        raw  = nlp.parse(job.text)
        from backend.core.spec_converter import normalise_spec
        spec = normalise_spec(raw)
        job.spec = spec

        job.update(JobStatus.PROCESSING, "Layer 1 complete — spec extracted", 25)
        await asyncio.sleep(0)

        # ── Layer 2: GNN (mock or real) ────────────────────────────────────────
        job.update(JobStatus.PROCESSING, "Layer 2: Generating room layout...", 40)
        await asyncio.sleep(0)

        loop       = asyncio.get_event_loop()
        room_graph = await loop.run_in_executor(None, _mock_gnn.generate, spec)

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

        # ── Layer 4: IFC Export ────────────────────────────────────────────────
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
