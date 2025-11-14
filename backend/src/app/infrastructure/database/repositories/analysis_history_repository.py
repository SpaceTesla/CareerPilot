"""Repository for analysis history."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.infrastructure.database.models import AnalysisHistory


class AnalysisHistoryRepository:
    """Repository for managing analysis history records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, history: AnalysisHistory) -> AnalysisHistory:
        """Create a new analysis history record."""
        self.session.add(history)
        self.session.commit()
        self.session.refresh(history)
        return history

    def get_by_user(self, user_id: str) -> list[AnalysisHistory]:
        """Get all analysis history for a user, ordered by most recent."""
        return (
            self.session.query(AnalysisHistory)
            .filter(AnalysisHistory.user_id == user_id)
            .order_by(AnalysisHistory.created_at.desc())
            .all()
        )

    def get_by_profile(self, profile_id: str) -> list[AnalysisHistory]:
        """Get all analysis history for a profile."""
        return (
            self.session.query(AnalysisHistory)
            .filter(AnalysisHistory.profile_id == profile_id)
            .order_by(AnalysisHistory.created_at.desc())
            .all()
        )

    def get_latest(self, user_id: str) -> AnalysisHistory | None:
        """Get the most recent analysis for a user."""
        return (
            self.session.query(AnalysisHistory)
            .filter(AnalysisHistory.user_id == user_id)
            .order_by(AnalysisHistory.created_at.desc())
            .first()
        )

