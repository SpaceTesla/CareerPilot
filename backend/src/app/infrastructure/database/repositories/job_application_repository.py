from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.database.models import JobApplication


class JobApplicationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, application: JobApplication) -> JobApplication:
        self.session.add(application)
        self.session.flush()
        return application

    def get_by_user(
        self, user_id: str, status: str | None = None
    ) -> list[JobApplication]:
        stmt = select(JobApplication).where(JobApplication.user_id == user_id)
        if status:
            stmt = stmt.where(JobApplication.status == status)
        stmt = stmt.order_by(JobApplication.applied_at.desc())
        return list(self.session.scalars(stmt).all())

    def get_by_id(self, application_id: str) -> JobApplication | None:
        return self.session.get(JobApplication, application_id)

    def update(
        self, application_id: str, updates: dict[str, Any]
    ) -> JobApplication | None:
        app = self.session.get(JobApplication, application_id)
        if not app:
            return None
        for k, v in updates.items():
            setattr(app, k, v)
        self.session.flush()
        return app

    def delete(self, application_id: str) -> bool:
        app = self.session.get(JobApplication, application_id)
        if not app:
            return False
        self.session.delete(app)
        self.session.flush()
        return True

    def get_by_url(self, user_id: str, job_url: str) -> JobApplication | None:
        stmt = (
            select(JobApplication)
            .where(JobApplication.user_id == user_id)
            .where(JobApplication.job_url == job_url)
        )
        return self.session.scalars(stmt).first()
