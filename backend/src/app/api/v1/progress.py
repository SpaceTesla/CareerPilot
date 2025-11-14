"""Progress tracking API routes."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.infrastructure.database.connection import get_session
from app.infrastructure.database.repositories.analysis_history_repository import (
    AnalysisHistoryRepository,
)
from app.infrastructure.database.models import AnalysisHistory
from app.services.analysis_service import analysis_service
import uuid

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/history")
async def get_progress_history(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of records to return"),
) -> dict[str, Any]:
    """Get analysis history for progress tracking."""
    try:
        with get_session() as session:
            # Check if table exists
            from sqlalchemy import inspect
            inspector = inspect(session.bind)
            if "analysis_history" not in inspector.get_table_names():
                # Table doesn't exist yet, return empty history
                return {
                    "user_id": user_id,
                    "history": [],
                    "total_records": 0,
                }
            
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
    except Exception as e:
        # Return empty history instead of error if table doesn't exist
        return {
            "user_id": user_id,
            "history": [],
            "total_records": 0,
        }


@router.post("/save")
async def save_analysis_snapshot(
    user_id: str = Query(..., description="User ID"),
    profile_id: str = Query(..., description="Profile ID"),
) -> dict[str, Any]:
    """Save current analysis as a snapshot for progress tracking."""
    try:
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
) -> dict[str, Any]:
    """Get score trends over time for visualization."""
    try:
        with get_session() as session:
            # Check if table exists
            from sqlalchemy import inspect
            inspector = inspect(session.bind)
            if "analysis_history" not in inspector.get_table_names():
                # Table doesn't exist yet, return empty trends
                return {
                    "user_id": user_id,
                    "trends": {
                        "overall_scores": [],
                        "dates": [],
                        "grades": [],
                    },
                    "total_points": 0,
                }
            
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
    except Exception as e:
        # Return empty trends instead of error
        return {
            "user_id": user_id,
            "trends": {
                "overall_scores": [],
                "dates": [],
                "grades": [],
            },
            "total_points": 0,
        }

