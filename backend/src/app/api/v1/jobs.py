"""Job recommendations API routes."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.services.job_matching_service import job_matching_service
from app.services.ats_service import ats_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/recommendations")
async def get_job_recommendations(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of recommendations"),
) -> dict[str, Any]:
    """Get personalized job recommendations using Tavily."""
    try:
        result = await job_matching_service.get_recommendations(user_id, limit)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Job recommendations failed: {str(e)}"
        ) from e


@router.get("/salary-insights")
async def get_salary_insights(
    user_id: str = Query(..., description="User ID"),
    location: str | None = Query(None, description="Location for salary data"),
) -> dict[str, Any]:
    """Get salary insights based on skills and experience."""
    try:
        result = await job_matching_service.get_salary_insights(user_id, location)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Salary insights failed: {str(e)}"
        ) from e


@router.get("/keywords")
async def get_keywords(
    user_id: str = Query(..., description="User ID"),
    target_role: str | None = Query(None, description="Target role for keyword suggestions"),
) -> dict[str, Any]:
    """Get missing keywords for ATS optimization."""
    try:
        result = await ats_service.get_missing_keywords(user_id, target_role)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Keyword analysis failed: {str(e)}"
        ) from e


