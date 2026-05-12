"""Recommendation feedback API routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.dependencies.auth import enforce_user_access, get_authenticated_user_id
from app.infrastructure.database.connection import get_session
from app.infrastructure.database.models import RecommendationFeedback
from app.infrastructure.database.repositories.recommendation_feedback_repository import (
    RecommendationFeedbackRepository,
)

router = APIRouter(prefix="/feedback", tags=["feedback"])

ITEM_TYPES = {"job", "course"}
FEEDBACK_VALUES = {"helpful", "not_helpful"}


def _validate_uuid(value: str, field_name: str) -> None:
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}") from exc


def _serialize(fb: RecommendationFeedback) -> dict[str, Any]:
    return {
        "id": fb.id,
        "user_id": fb.user_id,
        "item_type": fb.item_type,
        "item_identifier": fb.item_identifier,
        "feedback": fb.feedback,
        "is_helpful": fb.is_helpful,
        "created_at": fb.created_at.isoformat() if fb.created_at else None,
        "updated_at": fb.updated_at.isoformat() if fb.updated_at else None,
    }


class SubmitFeedbackRequest(BaseModel):
    user_id: str
    item_type: str  # job | course
    item_identifier: str  # URL or title
    feedback: str  # helpful | not_helpful


@router.post("")
async def submit_feedback(
    body: SubmitFeedbackRequest,
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Submit or update thumbs feedback for a job or course recommendation."""
    _validate_uuid(body.user_id, "user_id")
    enforce_user_access(body.user_id, auth_user_id)

    if body.item_type not in ITEM_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"item_type must be one of: {', '.join(sorted(ITEM_TYPES))}",
        )
    if body.feedback not in FEEDBACK_VALUES:
        raise HTTPException(
            status_code=400,
            detail=f"feedback must be one of: {', '.join(sorted(FEEDBACK_VALUES))}",
        )

    is_helpful = body.feedback == "helpful"
    fb_id = str(uuid.uuid4())

    with get_session() as session:
        repo = RecommendationFeedbackRepository(session)
        feedback = RecommendationFeedback(
            id=fb_id,
            user_id=body.user_id,
            item_type=body.item_type,
            item_identifier=body.item_identifier,
            feedback=body.feedback,
            is_helpful=is_helpful,
        )
        saved = repo.upsert(feedback)
        return _serialize(saved)


@router.get("")
async def list_feedback(
    user_id: str = Query(..., description="User ID"),
    item_type: str | None = Query(None, description="Filter by item_type (job|course)"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Get all feedback signals for a user."""
    _validate_uuid(user_id, "user_id")
    enforce_user_access(user_id, auth_user_id)

    if item_type and item_type not in ITEM_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"item_type must be one of: {', '.join(sorted(ITEM_TYPES))}",
        )

    with get_session() as session:
        repo = RecommendationFeedbackRepository(session)
        feedback_list = repo.get_by_user(user_id, item_type)
        return {
            "feedback": [_serialize(fb) for fb in feedback_list],
            "total": len(feedback_list),
        }


@router.delete("")
async def delete_feedback(
    user_id: str = Query(..., description="User ID"),
    item_type: str = Query(..., description="Item type"),
    item_identifier: str = Query(..., description="Item identifier"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Remove feedback for a specific item (toggle off)."""
    _validate_uuid(user_id, "user_id")
    enforce_user_access(user_id, auth_user_id)

    with get_session() as session:
        repo = RecommendationFeedbackRepository(session)
        existing = repo.get_by_item(user_id, item_type, item_identifier)
        if not existing:
            raise HTTPException(status_code=404, detail="Feedback not found")
        session.delete(existing)
        return {"deleted": True}
