"""Job tracking service for background analysis tasks."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4
import threading


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    id: UUID
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    current_step: str | None = None
    progress: dict = field(default_factory=dict)
    result: dict | None = None
    error: str | None = None


class JobStore:
    """Thread-safe in-memory job storage."""

    def __init__(self):
        self._jobs: dict[UUID, Job] = {}
        self._lock = threading.Lock()

    def create_job(self) -> Job:
        """Create a new job and return it."""
        job = Job(
            id=uuid4(),
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get_job(self, job_id: UUID) -> Job | None:
        """Get a job by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def update_job(
        self,
        job_id: UUID,
        status: JobStatus | None = None,
        current_step: str | None = None,
        progress: dict | None = None,
        result: dict | None = None,
        error: str | None = None,
    ) -> Job | None:
        """Update a job's status and data."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            if status is not None:
                job.status = status
            if current_step is not None:
                job.current_step = current_step
            if progress is not None:
                job.progress.update(progress)
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error

            job.updated_at = datetime.utcnow()
            return job

    def delete_job(self, job_id: UUID) -> bool:
        """Delete a job."""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                return True
            return False

    def list_jobs(self, limit: int = 100) -> list[Job]:
        """List recent jobs."""
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
            return jobs[:limit]


# Global job store instance
job_store = JobStore()
