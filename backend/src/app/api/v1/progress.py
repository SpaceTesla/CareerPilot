"""Progress tracking API routes."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies.auth import enforce_user_access, get_authenticated_user_id
from app.infrastructure.database.connection import get_session
from app.infrastructure.database.repositories.analysis_history_repository import (
    AnalysisHistoryRepository,
)
from app.infrastructure.database.models import AnalysisHistory
from app.services.analysis_service import analysis_service

router = APIRouter(prefix="/progress", tags=["progress"])


def _validate_uuid(value: str, field_name: str) -> None:
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}") from exc


@router.get("/history")
async def get_progress_history(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of records to return"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Get analysis history for progress tracking."""
    try:
        _validate_uuid(user_id, "user_id")
        enforce_user_access(user_id, auth_user_id)
        with get_session() as session:
            repo = AnalysisHistoryRepository(session)
            history = repo.get_by_user(user_id)

            # Convert to dict format
            history_data = []
            for record in history[:limit]:
                history_data.append({
                    "id": record.id,
                    "profile_id": record.profile_id,
                    "overall_score": float(record.overall_score) if record.overall_score else 0,
                    "grade": record.grade,
                    "section_scores": record.section_scores_json,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                })

            return {
                "user_id": user_id,
                "history": history_data,
                "total_records": len(history),
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to load progress history: {str(e)}"
        ) from e


@router.post("/save")
async def save_analysis_snapshot(
    user_id: str = Query(..., description="User ID"),
    profile_id: str = Query(..., description="Profile ID"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Save current analysis as a snapshot for progress tracking."""
    try:
        _validate_uuid(user_id, "user_id")
        _validate_uuid(profile_id, "profile_id")
        enforce_user_access(user_id, auth_user_id)
        # Get current analysis
        overview = await analysis_service.get_overview(user_id)
        if "error" in overview:
            raise HTTPException(status_code=404, detail=overview["error"])

        with get_session() as session:
            repo = AnalysisHistoryRepository(session)

            # Extract section scores
            section_scores = {}
            if overview.get("section_analysis"):
                for section, data in overview["section_analysis"].items():
                    section_scores[section] = {
                        "score": data.get("score", 0),
                        "max_score": data.get("max_score"),
                    }

            # Create history record
            history = AnalysisHistory(
                id=str(uuid.uuid4()),
                user_id=user_id,
                profile_id=profile_id,
                overall_score=str(overview.get("overall_score", 0)),
                grade=overview.get("grade"),
                section_scores_json=section_scores,
                analysis_data_json=overview,
            )

            saved = repo.create(history)

            return {
                "id": saved.id,
                "overall_score": overview.get("overall_score", 0),
                "grade": overview.get("grade"),
                "created_at": saved.created_at.isoformat() if saved.created_at else None,
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save analysis snapshot: {str(e)}"
        ) from e


@router.get("/trends")
async def get_score_trends(
    user_id: str = Query(..., description="User ID"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Get score trends over time for visualization."""
    try:
        _validate_uuid(user_id, "user_id")
        enforce_user_access(user_id, auth_user_id)
        with get_session() as session:
            repo = AnalysisHistoryRepository(session)
            history = repo.get_by_user(user_id)

            trends = {
                "overall_scores": [],
                "dates": [],
                "grades": [],
            }

            for record in history[:20]:  # Last 20 records
                trends["overall_scores"].append(
                    float(record.overall_score) if record.overall_score else 0
                )
                trends["dates"].append(
                    record.created_at.isoformat() if record.created_at else ""
                )
                trends["grades"].append(record.grade or "")

            # Reverse to show chronological order
            trends["overall_scores"].reverse()
            trends["dates"].reverse()
            trends["grades"].reverse()

            return {
                "user_id": user_id,
                "trends": trends,
                "total_points": len(trends["overall_scores"]),
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to load score trends: {str(e)}"
        ) from e

