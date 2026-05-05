import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

router = APIRouter()

_OUTPUT_DIR = Path(__file__).resolve().parents[3] / "output" / "api_generated"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/ifc-from-rooms", summary="Generate IFC directly from room data")
async def ifc_from_rooms(request: Request):
    """
    Synchronously convert a rooms array to an IFC file.
    Expects JSON body: { "rooms": [...], "prompt": "..." }
    Returns the .ifc file directly (no job/polling needed).
    """
    body = await request.json()
    rooms = body.get("rooms", [])
    if not rooms:
        raise HTTPException(status_code=400, detail="No rooms provided")

    prompt = body.get("prompt", "Generated Floor Plan")
    project_name = prompt[:60] if prompt else "Generated Floor Plan"

    from backend.core.room_graph_to_ifc import RoomGraphToIFC

    room_graph = {"rooms": rooms}
    adapter = RoomGraphToIFC()
    output_path = str(_OUTPUT_DIR / f"{uuid.uuid4()}.ifc")

    loop = asyncio.get_event_loop()
    ifc_path = await loop.run_in_executor(
        None,
        lambda: adapter.convert(room_graph, output_path=output_path, project_name=project_name),
    )

    return FileResponse(
        path=ifc_path,
        media_type="application/octet-stream",
        filename="architext-floor-plan.ifc",
    )
