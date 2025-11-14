"""Interview preparation API routes."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.services.interview_service import interview_service

router = APIRouter(prefix="/interview", tags=["interview"])


@router.get("/prep")
async def get_interview_prep(
    user_id: str = Query(..., description="User ID"),
    role: str | None = Query(None, description="Target role for interview prep"),
) -> dict[str, Any]:
    """Get interview preparation tips."""
    try:
        result = await interview_service.get_prep_tips(user_id, role)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Interview prep failed: {str(e)}"
        ) from e


@router.get("/questions")
async def get_interview_questions(
    user_id: str = Query(..., description="User ID"),
) -> dict[str, Any]:
    """Get common interview questions based on resume."""
    try:
        result = await interview_service.get_questions(user_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Question generation failed: {str(e)}"
        ) from e


@router.get("/star-examples")
async def get_star_examples(
    user_id: str = Query(..., description="User ID"),
) -> dict[str, Any]:
    """Get STAR method examples from user's experience."""
    try:
        result = await interview_service.get_star_examples(user_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"STAR examples failed: {str(e)}"
        ) from e


