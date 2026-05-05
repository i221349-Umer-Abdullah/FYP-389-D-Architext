"""
Blender addon entry point — wraps the async LLM pipeline for subprocess use.
Called by the Blender addon as: python run_pipeline.py "<prompt>"
Prints "IFC File: <path>" to stdout when done.
"""
import sys
import asyncio
import uuid
from pathlib import Path

# Resolve project root (two levels above scripts/)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.core.job_manager import Job
from backend.core.pipeline import run_pipeline


def main():
    if len(sys.argv) < 2:
        print("Usage: run_pipeline.py <prompt>", file=sys.stderr)
        sys.exit(1)

    prompt = sys.argv[1]
    job_id = str(uuid.uuid4())
    job = Job(job_id, prompt)

    asyncio.run(run_pipeline(job, generator_mode="llm"))

    if job.ifc_path:
        print(f"IFC File: {job.ifc_path}")
        sys.exit(0)
    else:
        print(f"ERROR: {job.error or 'Pipeline failed'}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
