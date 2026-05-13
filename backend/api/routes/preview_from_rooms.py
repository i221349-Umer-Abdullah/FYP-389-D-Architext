import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

router = APIRouter()

_OUTPUT_DIR = Path(__file__).resolve().parents[3] / "output" / "api_generated"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/preview-from-rooms", summary="Render 2D floor plan PNG from room data")
async def preview_from_rooms(request: Request):
    """
    Synchronously render a floor plan PNG from an edited rooms array.
    Expects JSON body: { "rooms": [...] }
    Returns the .png file directly.
    """
    body = await request.json()
    rooms = body.get("rooms", [])
    if not rooms:
        raise HTTPException(status_code=400, detail="No rooms provided")

    from backend.core.pipeline import _render_png

    room_graph = {"rooms": rooms}
    output_path = str(_OUTPUT_DIR / f"{uuid.uuid4()}.png")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: _render_png(room_graph, output_path))

    return FileResponse(
        path=output_path,
        media_type="image/png",
        filename="architext-floor-plan.png",
    )
