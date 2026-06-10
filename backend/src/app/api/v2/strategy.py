from __future__ import annotations

from uuid import UUID, uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.infrastructure.database.models import User, UserDigest, CareerStrategyReview, StrategyActionItem
from app.services.database_service import DatabaseService
from app.utils.event_bus import EventBus
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.get("/digests", response_model=dict)
async def get_digests(
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """
    Retrieves the current user's weekly digest history.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    stmt = (
        select(UserDigest)
        .where(UserDigest.user_id == current_user.id)
        .order_by(UserDigest.created_at.desc())
    )
    res = await db.execute(stmt)
    digests = res.scalars().all()

    return {
        "digests": [
            {
                "id": d.id,
                "sent_at": d.sent_at.isoformat() if d.sent_at else None,
                "health_score": d.health_score_snapshot,
                "delivery_status": d.delivery_status,
            }
            for d in digests
        ]
    }


@router.get("/digests/{digest_id}", response_model=dict)
async def get_digest_details(
    digest_id: str,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """
    Returns complete details of a specific digest.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    digest = await db.get(UserDigest, digest_id)
    if not digest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Digest not found.",
        )

    # Security check: ensure digest belongs to the logged-in user
    if digest.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    return {
        "id": digest.id,
        "sent_at": digest.sent_at.isoformat() if digest.sent_at else None,
        "content": {
            "health_score": digest.health_score_snapshot,
            "market_insights": digest.market_insight_summary,
            "position_delta": digest.position_delta_snapshot,
            "recommendations": digest.recommendations_snapshot.get("jobs", []),
        },
        "delivery_status": digest.delivery_status,
    }


@router.get("/reviews", response_model=dict)
async def get_reviews(
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """
    Retrieves the current user's career strategy review history.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    stmt = (
        select(CareerStrategyReview)
        .where(CareerStrategyReview.user_id == current_user.id)
        .order_by(CareerStrategyReview.created_at.desc())
    )
    res = await db.execute(stmt)
    reviews = res.scalars().all()

    return {
        "reviews": [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat(),
                "status": r.status,
                "health_score_start": float(r.health_score_start),
                "health_score_end": float(r.health_score_end),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in reviews
        ]
    }


@router.get("/reviews/{review_id}", response_model=dict)
async def get_review_details(
    review_id: str,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """
    Returns complete details of a specific strategy review, including action items.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    review = await db.get(CareerStrategyReview, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy review not found.",
        )

    if review.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    # Query action items
    stmt = select(StrategyActionItem).where(StrategyActionItem.review_id == review_id)
    res = await db.execute(stmt)
    action_items = res.scalars().all()

    return {
        "id": review.id,
        "status": review.status,
        "goals": review.goals_snapshot,
        "metrics": {
            "health_score_start": float(review.health_score_start),
            "current_health_score": float(review.health_score_end),
        },
        "insights_summary": review.insights_summary,
        "action_items": [
            {
                "id": item.id,
                "description": item.description,
                "difficulty": item.difficulty,
                "status": item.status,
                "target_date": item.target_date.isoformat() if item.target_date else None,
            }
            for item in action_items
        ],
    }


@router.post("/reviews/{review_id}/complete", response_model=dict)
async def complete_review(
    review_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """
    Completes a strategy review, updates status, and emits events.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    review = await db.get(CareerStrategyReview, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy review not found.",
        )

    if review.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    feedback_text = payload.get("feedback_text", "")
    accept_action_items = payload.get("accept_action_items", True)

    review.status = "COMPLETED"
    review.feedback_text = feedback_text
    review.completed_at = datetime.utcnow()

    if not accept_action_items:
        # Cancel all action items if user rejects them
        stmt_cancel = (
            update(StrategyActionItem)
            .where(StrategyActionItem.review_id == review_id)
            .values(status="CANCELLED", updated_at=datetime.utcnow())
        )
        await db.execute(stmt_cancel)

    await db.flush()

    # Emit completed event
    try:
        delta = float(review.health_score_end - review.health_score_start)
        await EventBus.publish(
            "strategy.review.completed",
            {
                "event_id": str(uuid4()),
                "event_type": "strategy.review.completed",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "payload": {
                    "review_id": review_id,
                    "user_id": current_user.id,
                    "health_score_delta": delta,
                },
            },
        )
    except Exception as e:
        logger.error(f"Failed to publish strategy.review.completed: {e}")

    return {
        "id": review.id,
        "status": review.status,
        "completed_at": review.completed_at.isoformat(),
    }


@router.patch("/reviews/action-items/{item_id}", response_model=dict)
async def update_action_item(
    item_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """
    Updates the status of a specific action item.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    item = await db.get(StrategyActionItem, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action item not found.",
        )

    # Verify ownership by checking the parent review
    stmt_review = select(CareerStrategyReview).where(CareerStrategyReview.id == item.review_id)
    res_review = await db.execute(stmt_review)
    review = res_review.scalar_one_or_none()
    if not review or review.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    new_status = payload.get("status", "TODO")
    item.status = new_status
    item.updated_at = datetime.utcnow()
    if new_status == "COMPLETED":
        item.completed_at = datetime.utcnow()

    await db.flush()

    return {
        "id": item.id,
        "status": item.status,
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
    }
