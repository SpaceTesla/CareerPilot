"""API endpoints for user session management."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Path

from app.api.dependencies.auth import enforce_user_access, get_authenticated_user_id
from app.core.logging import get_logger
from app.infrastructure.database.connection import get_session
from app.infrastructure.database.repositories.session_repository import SessionRepository
from app.services.analysis_service import analysis_service

logger = get_logger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/")
async def list_sessions(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(20, description="Maximum number of sessions to return"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """List all resume sessions for a user."""
    try:
        enforce_user_access(user_id, auth_user_id)
        with get_session() as session:
            repo = SessionRepository(session)
            sessions = repo.list_sessions_with_profiles(user_id, limit)

            return {
                "sessions": sessions,
                "total": len(sessions),
            }
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list sessions: {str(e)}"
        ) from e


@router.get("/active")
async def get_active_session(
    user_id: str = Query(..., description="User ID"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Get the currently active session for a user."""
    try:
        enforce_user_access(user_id, auth_user_id)
        with get_session() as session:
            repo = SessionRepository(session)
            active_session = repo.get_active_session(user_id)

            if not active_session:
                return {"session": None}

            session_data = repo.get_session_with_profile(active_session.id)
            return {"session": session_data}
    except Exception as e:
        logger.error(f"Failed to get active session: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get active session: {str(e)}"
        ) from e


@router.get("/{session_id}")
async def get_session_details(
    session_id: str = Path(..., description="Session ID"),
    user_id: str = Query(..., description="User ID"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Get details of a specific session."""
    try:
        enforce_user_access(user_id, auth_user_id)
        with get_session() as session:
            repo = SessionRepository(session)
            session_data = repo.get_session_with_profile(session_id)

            if not session_data:
                raise HTTPException(status_code=404, detail="Session not found")
            if session_data["user_id"] != user_id:
                raise HTTPException(status_code=403, detail="Access denied")

            return session_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session details: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get session details: {str(e)}"
        ) from e


@router.post("/switch/{session_id}")
async def switch_session(
    session_id: str = Path(..., description="Session ID to switch to"),
    user_id: str = Query(..., description="User ID"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Switch to a different resume session."""
    try:
        enforce_user_access(user_id, auth_user_id)
        with get_session() as session:
            repo = SessionRepository(session)
            switched_session = repo.switch_session(session_id, user_id)

            if not switched_session:
                raise HTTPException(
                    status_code=404, detail="Session not found or access denied"
                )

            session_data = repo.get_session_with_profile(switched_session.id)
            return {
                "success": True,
                "message": "Session switched successfully",
                "session": session_data,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to switch session: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to switch session: {str(e)}"
        ) from e


@router.post("/")
async def create_session(
    user_id: str = Query(..., description="User ID"),
    profile_id: str = Query(..., description="Profile ID"),
    name: str | None = Query(None, description="Session name"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Create a new session for a resume profile."""
    try:
        enforce_user_access(user_id, auth_user_id)
        with get_session() as session:
            repo = SessionRepository(session)
            new_session = repo.create_session(user_id, profile_id, name)

            return {
                "success": True,
                "session_id": new_session.id,
                "profile_id": new_session.profile_id,
                "name": new_session.name,
                "is_active": new_session.is_active,
            }
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create session: {str(e)}"
        ) from e


@router.delete("/{session_id}")
async def delete_session(
    session_id: str = Path(..., description="Session ID to delete"),
    user_id: str = Query(..., description="User ID"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Delete a session."""
    try:
        enforce_user_access(user_id, auth_user_id)
        with get_session() as session:
            repo = SessionRepository(session)
            deleted = repo.delete_session(session_id, user_id)

            if not deleted:
                raise HTTPException(status_code=404, detail="Session not found")

            return {"success": True, "message": "Session deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete session: {str(e)}"
        ) from e


@router.get("/scores/trends")
async def get_session_score_trends(
    user_id: str = Query(..., description="User ID"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Get score trends across all resume sessions for visualization."""
    try:
        enforce_user_access(user_id, auth_user_id)
        with get_session() as db_session:
            repo = SessionRepository(db_session)
            sessions = repo.get_by_user(user_id, limit=10)

            if len(sessions) < 1:
                return {
                    "user_id": user_id,
                    "has_multiple_sessions": False,
                    "trends": [],
                    "total_sessions": 0,
                }

            trends = []
            for user_session in sessions:
                # Get the analysis overview for each session's profile
                try:
                    overview = await analysis_service.get_overview_for_profile(
                        user_session.profile_id
                    )
                    if overview and "error" not in overview:
                        trends.append({
                            "session_id": user_session.id,
                            "session_name": user_session.name or "Unnamed Resume",
                            "profile_id": user_session.profile_id,
                            "overall_score": overview.get("overall_score", 0),
                            "grade": overview.get("grade", "N/A"),
                            "created_at": user_session.created_at.isoformat() if user_session.created_at else None,
                            "is_active": user_session.is_active,
                        })
                except Exception as e:
                    logger.warning(f"Failed to get overview for session {user_session.id}: {e}")
                    continue

            # Sort by created_at ascending (oldest first for chart)
            trends.sort(key=lambda x: x["created_at"] or "")

            return {
                "user_id": user_id,
                "has_multiple_sessions": len(trends) > 1,
                "trends": trends,
                "total_sessions": len(trends),
            }
    except Exception as e:
        logger.error(f"Failed to get session score trends: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get session score trends: {str(e)}"
        ) from e
