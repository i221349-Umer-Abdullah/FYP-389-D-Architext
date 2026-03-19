import sys
from pathlib import Path
import asyncio

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))

from backend.core.job_manager import Job
from backend.core.pipeline import run_pipeline

async def main():
    job = Job("test_cvae_001", "3 bedroom modern house with 2 bathrooms, an open kitchen, living room, and a small garden")
    print(f"Starting pipeline for: '{job.text}'\n")
    await run_pipeline(job)
    
    print(f"\nFinal Status: {job.status}")
    if job.error:
        print(f"Error: {job.error}")
    else:
        print("\nRoom Summary:")
        if job.preview:
            print(job.preview)
        print(f"\nIFC File successfully written to: {job.ifc_path}")

if __name__ == "__main__":
    asyncio.run(main())
