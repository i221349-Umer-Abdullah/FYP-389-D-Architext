"""
In-memory job manager for async generation requests.

Each generation job goes through status transitions:
  pending → processing → done / failed

For production this would use Redis or a DB, but for dev an
in-memory dict is perfectly fine.
"""

import uuid
import asyncio
import datetime
from typing import Dict, Optional
from backend.models.schemas import JobStatus


class Job:
    def __init__(self, job_id: str, text: str):
        self.job_id      = job_id
        self.text        = text
        self.status      = JobStatus.PENDING
        self.progress    = 0
        self.message     = "Queued"
        self.spec        = None   # Layer 1 output
        self.preview     = None   # Layer 2+3 output (room summary)
        self.ifc_path    = None   # Path to generated .ifc file
        self.preview_png = None   # Path to generated 2D preview PNG
        self.error       = None
        self.created_at  = datetime.datetime.utcnow()
        self.updated_at  = datetime.datetime.utcnow()

    def update(self, status: JobStatus, message: str, progress: int):
        self.status     = status
        self.message    = message
        self.progress   = progress
        self.updated_at = datetime.datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "job_id":    self.job_id,
            "status":    self.status,
            "progress":  self.progress,
            "message":   self.message,
            "spec":      self.spec,
            "preview":   self.preview,
            "ifc_ready": self.ifc_path is not None,
            "error":     self.error,
        }


class JobManager:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = asyncio.Lock()

    def create_job(self, text: str) -> Job:
        job_id = str(uuid.uuid4())
        job    = Job(job_id, text)
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove jobs older than max_age_hours to prevent memory leak."""
        async with self._lock:
            now    = datetime.datetime.utcnow()
            cutoff = datetime.timedelta(hours=max_age_hours)
            stale  = [
                jid for jid, job in self._jobs.items()
                if (now - job.created_at) > cutoff
            ]
            for jid in stale:
                del self._jobs[jid]


# Singleton — imported by routes
job_manager = JobManager()
