import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from backend.core.job_manager import job_manager
from backend.models.schemas   import JobStatus

router = APIRouter()


@router.get("/download/{job_id}", summary="Download generated IFC file")
async def download(job_id: str):
    """
    Download the generated `.ifc` file for a completed job.
    Only available when `status == done` and `ifc_ready == true`.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.status != JobStatus.DONE:
        raise HTTPException(status_code=409, detail=f"Job not complete yet (status: {job.status})")
    if not job.ifc_path or not os.path.exists(job.ifc_path):
        raise HTTPException(status_code=500, detail="IFC file not found on server")

    filename = f"architext_{job_id[:8]}.ifc"
    return FileResponse(
        path         = job.ifc_path,
        media_type   = "application/octet-stream",
        filename     = filename,
    )


@router.get("/preview/{job_id}", summary="Get room summary JSON")
async def preview(job_id: str):
    """
    Returns the room summary (room list, areas, positions) as JSON.
    Available as soon as status is `done`.
    Useful for the frontend 2D preview renderer.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.status != JobStatus.DONE:
        raise HTTPException(status_code=409, detail=f"Job not complete yet (status: {job.status})")
    if not job.preview:
        raise HTTPException(status_code=500, detail="Preview data not available")

    return job.preview
