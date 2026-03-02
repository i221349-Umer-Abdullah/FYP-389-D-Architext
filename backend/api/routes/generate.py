from fastapi import APIRouter, BackgroundTasks, HTTPException
from backend.models.schemas import GenerateRequest, GenerateResponse, JobStatus
from backend.core.job_manager import job_manager
from backend.core.pipeline    import run_pipeline

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse, summary="Start floorplan generation")
async def generate(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Submit a natural language description for floorplan generation.

    Returns a `job_id` immediately. Poll `/api/status/{job_id}` to track progress
    and retrieve the result once status is `done`.
    """
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")

    job = job_manager.create_job(request.text)

    # Kick off pipeline as a background task
    background_tasks.add_task(run_pipeline, job, request.project_name)

    return GenerateResponse(
        job_id  = job.job_id,
        status  = JobStatus.PENDING,
        message = "Generation started — poll /api/status/{job_id} for updates",
    )
