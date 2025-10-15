from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.database.models import ResumeProfile


class ResumeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_profile(self, profile: ResumeProfile) -> ResumeProfile:
        self.session.add(profile)
        self.session.flush()
        return profile

    def get_by_user(self, user_id: str) -> list[ResumeProfile]:
        stmt = select(ResumeProfile).where(ResumeProfile.user_id == user_id)
        return list(self.session.scalars(stmt).all())

    def update_profile(
        self, profile_id: str, updates: dict[str, Any]
    ) -> ResumeProfile | None:
        profile = self.session.get(ResumeProfile, profile_id)
        if not profile:
            return None
        for k, v in updates.items():
            setattr(profile, k, v)
        self.session.flush()
        return profile
