from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.database.models import RecommendationFeedback


class RecommendationFeedbackRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, feedback: RecommendationFeedback) -> RecommendationFeedback:
        """Insert or update feedback for a given user+item_type+item_identifier."""
        existing = self.get_by_item(
            feedback.user_id, feedback.item_type, feedback.item_identifier
        )
        if existing:
            existing.feedback = feedback.feedback
            existing.is_helpful = feedback.is_helpful
            self.session.flush()
            return existing
        self.session.add(feedback)
        self.session.flush()
        return feedback

    def get_by_user(
        self, user_id: str, item_type: str | None = None
    ) -> list[RecommendationFeedback]:
        stmt = select(RecommendationFeedback).where(
            RecommendationFeedback.user_id == user_id
        )
        if item_type:
            stmt = stmt.where(RecommendationFeedback.item_type == item_type)
        stmt = stmt.order_by(RecommendationFeedback.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def get_by_item(
        self, user_id: str, item_type: str, item_identifier: str
    ) -> RecommendationFeedback | None:
        stmt = (
            select(RecommendationFeedback)
            .where(RecommendationFeedback.user_id == user_id)
            .where(RecommendationFeedback.item_type == item_type)
            .where(RecommendationFeedback.item_identifier == item_identifier)
        )
        return self.session.scalars(stmt).first()

    def get_helpful_identifiers(self, user_id: str, item_type: str) -> set[str]:
        """Return set of item identifiers the user found helpful."""
        rows = self.get_by_user(user_id, item_type)
        return {r.item_identifier for r in rows if r.is_helpful}

    def get_not_helpful_identifiers(self, user_id: str, item_type: str) -> set[str]:
        """Return set of item identifiers the user found not helpful."""
        rows = self.get_by_user(user_id, item_type)
        return {r.item_identifier for r in rows if not r.is_helpful}
