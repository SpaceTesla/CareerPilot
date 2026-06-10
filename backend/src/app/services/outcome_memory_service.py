"""Outcome Memory System (OMS) service for CareerPilot compounding feedback loop."""

from __future__ import annotations

import decimal
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Any, Dict, Optional, List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import (
    JobApplication,
    ApplicationOutcome,
    ApplicationStatusHistory,
)
from app.services.database_service import AsyncSessionLocal

logger = get_logger(__name__)


class OutcomeMemoryService:
    """Service to track application final outcomes, status histories, and prediction errors."""

    @classmethod
    def _get_success_value(cls, outcome: str) -> float:
        """Map final outcome to a numeric success value (0.0 to 100.0)."""
        outcome_clean = outcome.upper()
        if "REJECTED" in outcome_clean:
            return 0.0
        elif "GHOSTED" in outcome_clean:
            return 0.0
        elif "WITHDRAWN" in outcome_clean:
            return 0.0
        elif "INTERVIEW" in outcome_clean:
            return 50.0
        elif "OFFERED" in outcome_clean or "OFFER" in outcome_clean:
            return 100.0
        return 0.0

    @classmethod
    async def record_status_change(
        cls,
        application_id: str,
        new_status: str,
        rejection_reason: Optional[str] = None,
        rejection_stage: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update application status, record in status history, and calculate prediction error.
        """
        async with AsyncSessionLocal() as session:
            # 1. Fetch Job Application
            app_stmt = select(JobApplication).where(JobApplication.id == application_id)
            res = await session.execute(app_stmt)
            application = res.scalar_one_or_none()
            if not application:
                raise ValueError(f"Job application not found: {application_id}")
            
            previous_status = application.status
            application.status = new_status.lower()
            application.updated_at = datetime.utcnow()
            
            # 2. Record Status History
            history = ApplicationStatusHistory(
                id=str(uuid4()),
                application_id=application_id,
                previous_status=previous_status,
                new_status=new_status,
                changed_at=datetime.utcnow(),
            )
            session.add(history)
            
            # 3. Handle Outcome Record
            outcome_stmt = select(ApplicationOutcome).where(
                ApplicationOutcome.application_id == application_id
            )
            outcome_res = await session.execute(outcome_stmt)
            outcome = outcome_res.scalar_one_or_none()
            
            # Retrieve predicted fit score (e.g. from job application payload or default)
            # If application has opportunity_id we could fetch fit_score, otherwise default
            predicted_fit_score = 80.0
            
            # Calculate elapsed days to response
            days_to_response = None
            if application.applied_at:
                days_to_response = (datetime.utcnow() - application.applied_at).days
            
            # Calculate prediction error if terminal
            is_terminal = new_status.upper() in ["REJECTED", "OFFERED", "GHOSTED"]
            prediction_error = None
            if is_terminal:
                actual_val = cls._get_success_value(new_status)
                prediction_error = abs(predicted_fit_score - actual_val)
                
            follow_up_date = datetime.utcnow() + timedelta(days=14)
            follow_up_completed = is_terminal  # If terminal, no need for follow ups
            
            if outcome:
                outcome.final_outcome = new_status.upper()
                if rejection_reason:
                    outcome.rejection_reason = rejection_reason
                if rejection_stage:
                    outcome.rejection_stage = rejection_stage
                outcome.days_to_response = days_to_response
                outcome.prediction_error = prediction_error
                outcome.follow_up_completed = follow_up_completed
                outcome.updated_at = datetime.utcnow()
            else:
                outcome = ApplicationOutcome(
                    id=str(uuid4()),
                    application_id=application_id,
                    predicted_fit_score=predicted_fit_score,
                    final_outcome=new_status.upper(),
                    rejection_reason=rejection_reason,
                    rejection_stage=rejection_stage,
                    prediction_error=prediction_error,
                    days_to_response=days_to_response,
                    follow_up_date=follow_up_date,
                    follow_up_completed=follow_up_completed,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(outcome)
                
            await session.commit()
            
            return {
                "id": outcome.id,
                "application_id": outcome.application_id,
                "predicted_fit_score": float(outcome.predicted_fit_score),
                "final_outcome": outcome.final_outcome,
                "rejection_reason": outcome.rejection_reason,
                "rejection_stage": outcome.rejection_stage,
                "prediction_error": float(outcome.prediction_error) if outcome.prediction_error is not None else None,
                "days_to_response": outcome.days_to_response,
                "follow_up_date": outcome.follow_up_date.isoformat(),
                "follow_up_completed": outcome.follow_up_completed,
                "created_at": outcome.created_at.isoformat(),
                "updated_at": outcome.updated_at.isoformat(),
            }

    @classmethod
    async def trigger_scheduled_follow_ups(cls) -> int:
        """Find stale applications where follow-up date has passed and nudge user."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ApplicationOutcome)
                .where(ApplicationOutcome.follow_up_date <= datetime.utcnow())
                .where(ApplicationOutcome.follow_up_completed == False)
            )
            res = await session.execute(stmt)
            outcomes = res.scalars().all()
            
            count = len(outcomes)
            for outcome in outcomes:
                outcome.follow_up_completed = True
                outcome.updated_at = datetime.utcnow()
                # Publish follow-up event/notification here in a real system
                
            await session.commit()
            return count

    @classmethod
    async def auto_ghost_applications(cls) -> int:
        """Auto-mark applications in SUBMITTED state for > 45 days as GHOSTED."""
        cutoff_date = datetime.utcnow() - timedelta(days=45)
        
        async with AsyncSessionLocal() as session:
            stmt = (
                select(JobApplication)
                .where(JobApplication.status.in_(["applied", "processing", "submitted"]))
                .where(JobApplication.applied_at <= cutoff_date)
            )
            res = await session.execute(stmt)
            stale_apps = res.scalars().all()
            
            count = len(stale_apps)
            for app in stale_apps:
                # Use record_status_change helper to log correctly
                await cls.record_status_change(app.id, "GHOSTED")
                
            return count
