from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.infrastructure.database.models import ResumeProcessingJob


class ResumeJobRepository:
    """Repository for asynchronous resume processing jobs."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, job_id: str) -> ResumeProcessingJob | None:
        return self.session.get(ResumeProcessingJob, job_id)

    def create(self, job: ResumeProcessingJob) -> ResumeProcessingJob:
        self.session.add(job)
        self.session.flush()
        return job

    def mark_started(self, job: ResumeProcessingJob) -> ResumeProcessingJob:
        job.status = "processing"
        job.progress = 20
        job.message = "Processing resume"
        job.started_at = datetime.utcnow()
        self.session.flush()
        return job

    def mark_completed(
        self,
        job: ResumeProcessingJob,
        *,
        resolved_user_id: str,
        profile_id: str,
        session_id: str,
        resume_session_id: str,
    ) -> ResumeProcessingJob:
        job.status = "completed"
        job.progress = 100
        job.message = "Resume processed"
        job.error = None
        job.resolved_user_id = resolved_user_id
        job.profile_id = profile_id
        job.session_id = session_id
        job.resume_session_id = resume_session_id
        job.completed_at = datetime.utcnow()
        self.session.flush()
        return job

    def mark_failed(self, job: ResumeProcessingJob, error: str) -> ResumeProcessingJob:
        job.status = "failed"
        job.progress = 100
        job.message = "Resume processing failed"
        job.error = error[:1000]
        job.completed_at = datetime.utcnow()
        self.session.flush()
        return job
