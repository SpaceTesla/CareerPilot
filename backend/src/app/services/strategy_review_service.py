from __future__ import annotations

import datetime
from uuid import uuid4, UUID
from sqlalchemy import select, update

from app.core.logging import get_logger
from app.infrastructure.database.connection import SessionLocal
from app.infrastructure.database.models import (
    CareerStrategyReview,
    StrategyActionItem,
    CareerGoals,
    CareerHealthScore,
    PositionDelta,
)
from app.utils.event_bus import EventBus

logger = get_logger(__name__)


class StrategyHistoryTracker:
    """
    Tracks and evaluates historical strategy review completions.
    """

    @classmethod
    def evaluate_previous_review(cls, user_id: UUID) -> dict:
        """
        Finds the most recent completed strategy review and determines the completion rate of action items.
        """
        user_str_id = str(user_id)
        with SessionLocal() as session:
            # Find last completed strategy review
            stmt = (
                select(CareerStrategyReview)
                .where(
                    CareerStrategyReview.user_id == user_str_id,
                    CareerStrategyReview.status == "COMPLETED",
                )
                .order_by(CareerStrategyReview.completed_at.desc())
                .limit(1)
            )
            res = session.execute(stmt)
            prev_review = res.scalar_one_or_none()

            if not prev_review:
                return {"completion_rate": 1.0, "unresolved": []}

            # Query all action items for this review
            stmt_items = select(StrategyActionItem).where(StrategyActionItem.review_id == prev_review.id)
            res_items = session.execute(stmt_items)
            items = res_items.scalars().all()

            if not items:
                return {"completion_rate": 1.0, "unresolved": []}

            completed_count = sum(1 for it in items if it.status == "COMPLETED")
            total_count = len(items)

            unresolved = [
                {
                    "description": it.description,
                    "difficulty": it.difficulty,
                }
                for it in items
                if it.status != "COMPLETED"
            ]

            return {
                "completion_rate": round(completed_count / total_count, 2),
                "unresolved": unresolved,
            }


class StrategyReviewOrchestrator:
    """
    Orchestrates the monthly career strategy evaluation.
    """

    @classmethod
    async def initiate_review(cls, user_id: UUID) -> str:
        """
        Initiates a strategy review by analyzing career health, previous achievements, and target goals.
        """
        user_str_id = str(user_id)
        review_id = str(uuid4())

        # 1. Fetch user career goals
        goals_snapshot = {"target_role": "Software Engineer", "timeline_months": 12}
        with SessionLocal() as session:
            stmt = select(CareerGoals).where(CareerGoals.user_id == user_str_id)
            res = session.execute(stmt)
            goals_obj = res.scalar_one_or_none()
            if goals_obj:
                goals_snapshot = {
                    "target_role": goals_obj.target_role or "AI Platform Engineer",
                    "timeline_months": goals_obj.timeline_months or 12,
                }

        # 2. Fetch career health scores
        health_start = 70.0
        health_end = 75.0
        with SessionLocal() as session:
            stmt = select(CareerHealthScore).where(CareerHealthScore.user_id == user_str_id).order_by(CareerHealthScore.computed_at.desc()).limit(2)
            res = session.execute(stmt)
            scores = res.scalars().all()
            if len(scores) >= 2:
                health_start = float(scores[1].score)
                health_end = float(scores[0].score)
            elif len(scores) == 1:
                health_start = float(scores[0].score) - 2.0
                health_end = float(scores[0].score)

        # 3. Analyze previous review items
        history = StrategyHistoryTracker.evaluate_previous_review(user_id)
        completion_rate = history["completion_rate"]
        unresolved_items = history["unresolved"]

        # 4. Fetch position delta gaps
        gaps = ["LangGraph", "Docker"]
        with SessionLocal() as session:
            stmt = select(PositionDelta).where(PositionDelta.user_id == user_str_id).order_by(PositionDelta.computed_at.desc()).limit(1)
            res = session.execute(stmt)
            delta = res.scalar_one_or_none()
            if delta and delta.missing_skills:
                gaps = delta.missing_skills

        # 5. Formulate insights and new action items
        target_role = goals_snapshot["target_role"]
        completion_insight = ""
        if completion_rate < 1.0 and unresolved_items:
            completion_insight = f" You are still working on carrying over {len(unresolved_items)} item(s) from last month."

        insights_summary = (
            f"Your career health score is stable at {health_end}. "
            f"To reach your target role of {target_role}, we recommend focusing on resolving your remaining skill gaps: "
            f"{', '.join(gaps)}.{completion_insight}"
        )

        new_items = []
        # Carry over unresolved items
        for unres in unresolved_items:
            new_items.append(
                {
                    "description": f"Carry Over: {unres['description']}",
                    "difficulty": unres["difficulty"],
                }
            )

        # Add new gaps to study
        for gap in gaps:
            new_items.append(
                {
                    "description": f"Learn {gap} and build a proof-of-concept project.",
                    "difficulty": "MODERATE" if gap in ["LangGraph", "Docker"] else "HARD",
                }
            )

        # If no new items, generate a generic target action item
        if not new_items:
            new_items.append(
                {
                    "description": f"Optimize resume mapping for {target_role} vacancies.",
                    "difficulty": "EASY",
                }
            )

        # 6. Save review and action items to database
        await cls.save_review_outputs(UUID(review_id), user_id, goals_snapshot, health_start, health_end, insights_summary, new_items)

        # 7. Publish strategy.review.initiated event
        try:
            await EventBus.publish(
                "strategy.review.initiated",
                {
                    "event_id": str(uuid4()),
                    "event_type": "strategy.review.initiated",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
                    "payload": {
                        "review_id": review_id,
                        "user_id": user_str_id,
                    },
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish strategy.review.initiated: {e}")

        return review_id

    @classmethod
    async def save_review_outputs(
        cls,
        review_id: UUID,
        user_id: UUID,
        goals_snapshot: dict,
        health_start: float,
        health_end: float,
        insights_summary: str,
        items: list[dict],
    ) -> None:
        """
        Persists strategy review outputs and action items inside SQL tables.
        """
        review_str_id = str(review_id)
        user_str_id = str(user_id)

        with SessionLocal() as session:
            db_review = CareerStrategyReview(
                id=review_str_id,
                user_id=user_str_id,
                status="PENDING_REVIEW",
                goals_snapshot=goals_snapshot,
                health_score_start=health_start,
                health_score_end=health_end,
                insights_summary=insights_summary,
                created_at=datetime.datetime.now(datetime.timezone.utc),
            )
            session.add(db_review)

            # Insert action items
            for it in items:
                db_item = StrategyActionItem(
                    id=str(uuid4()),
                    review_id=review_str_id,
                    description=it["description"],
                    difficulty=it["difficulty"],
                    status="TODO",
                    target_date=(datetime.date.today() + datetime.timedelta(days=30)),
                    created_at=datetime.datetime.now(datetime.timezone.utc),
                    updated_at=datetime.datetime.now(datetime.timezone.utc),
                )
                session.add(db_item)

            session.commit()
            logger.info(f"Persisted strategy review outputs for review {review_str_id}")
