from fastapi import APIRouter, HTTPException
from backend.models.schemas import StatusResponse, FloorplanPreview, RoomSummary
from backend.core.job_manager import job_manager

router = APIRouter()


@router.get("/status/{job_id}", response_model=StatusResponse, summary="Check generation status")
async def status(job_id: str):
    """
    Poll this endpoint after calling `/api/generate`.

    Progress moves:  pending → processing (10→90%) → done / failed

    When `status == done`:
      - `preview` contains room list and area summary
      - `ifc_ready == true` — call `/api/download/{job_id}` for the file
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    preview = None
    if job.preview:
        rooms = [RoomSummary(**r) for r in job.preview.get("rooms", [])]
        preview = FloorplanPreview(
            room_count    = job.preview.get("room_count", 0),
            total_area_m2 = job.preview.get("total_area_m2", 0.0),
            rooms         = rooms,
            metadata      = job.preview.get("metadata", {}),
        )

    return StatusResponse(
        job_id    = job.job_id,
        status    = job.status,
        message   = job.message,
        progress  = job.progress,
        spec      = job.spec,
        preview   = preview,
        ifc_ready = job.ifc_path is not None,
        error     = job.error,
    )
