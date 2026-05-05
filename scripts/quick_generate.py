"""
Blender addon quick-generate entry point — skips NLP, uses spec JSON directly.
Called by the Blender addon as: python quick_generate.py '<spec_json>'
Prints "IFC File: <path>" to stdout when done.
"""
import sys
import asyncio
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.core.job_manager import Job
from backend.core.pipeline import _validate_and_fix, IFC_OUTPUT_DIR
from backend.models.schemas import JobStatus


async def quick_run(job: Job, spec: dict) -> None:
    from backend.core.real_gnn import get_real_gnn
    from backend.core.room_graph_to_ifc import RoomGraphToIFC

    job.update(JobStatus.PROCESSING, "Generating room layout with GNN...", 20)

    loop = asyncio.get_event_loop()
    gnn = get_real_gnn()
    room_graph = await loop.run_in_executor(None, gnn.generate, spec)

    job.update(JobStatus.PROCESSING, "Validating layout...", 60)
    room_graph = _validate_and_fix(room_graph, spec)

    job.update(JobStatus.PROCESSING, "Exporting IFC...", 80)
    adapter = RoomGraphToIFC()
    job.preview = adapter.get_room_summary(room_graph)

    ifc_path = str(IFC_OUTPUT_DIR / f"{job.job_id}.ifc")
    ifc_path = await loop.run_in_executor(
        None,
        lambda: adapter.convert(room_graph, output_path=ifc_path, project_name="Quick Generate")
    )
    job.ifc_path = ifc_path
    job.update(JobStatus.DONE, "Done", 100)


def main():
    if len(sys.argv) < 2:
        print("Usage: quick_generate.py '<spec_json>'", file=sys.stderr)
        sys.exit(1)

    try:
        spec = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON spec — {e}", file=sys.stderr)
        sys.exit(1)

    job_id = str(uuid.uuid4())
    job = Job(job_id, str(spec))

    asyncio.run(quick_run(job, spec))

    if job.ifc_path:
        print(f"IFC File: {job.ifc_path}")
        sys.exit(0)
    else:
        print(f"ERROR: {job.error or 'Pipeline failed'}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
