"""Interview preparation API routes."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.interview_service import interview_service

router = APIRouter(prefix="/interview", tags=["interview"])


class EvaluateAnswerRequest(BaseModel):
    user_id: str
    question: str
    answer: str
    question_type: str | None = None


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


@router.post("/evaluate-answer")
async def evaluate_answer(request: EvaluateAnswerRequest) -> dict[str, Any]:
    """Evaluate user's answer with AI feedback."""
    try:
        result = await interview_service.evaluate_answer(
            request.user_id,
            request.question,
            request.answer,
            request.question_type,
        )
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Answer evaluation failed: {str(e)}"
        ) from e


@router.get("/questions-by-category")
async def get_questions_by_category(
    user_id: str = Query(..., description="User ID"),
    category: str | None = Query(None, description="Question category (technical, behavioral, situational)"),
) -> dict[str, Any]:
    """Get interview questions by category."""
    try:
        result = await interview_service.get_questions_by_category(user_id, category)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Question generation failed: {str(e)}"
        ) from e


