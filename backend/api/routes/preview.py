from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from backend.core.job_manager import job_manager

router = APIRouter()


@router.get("/preview/{job_id}", summary="Get 2D floor plan PNG")
async def preview(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if not job.preview_png:
        raise HTTPException(status_code=404, detail="Preview not ready yet")
    return FileResponse(job.preview_png, media_type="image/png")
