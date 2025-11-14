"""Analysis API routes."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.services.analysis_service import analysis_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/overview")
async def get_analysis_overview(
    user_id: str = Query(..., description="User ID"),
) -> dict[str, Any]:
    """Get complete analysis overview including scores, strengths, and weaknesses."""
    try:
        result = await analysis_service.get_overview(user_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}") from e


@router.get("/ats-score")
async def get_ats_score(
    user_id: str = Query(..., description="User ID"),
) -> dict[str, Any]:
    """Get ATS optimization score and keyword analysis."""
    try:
        from app.services.ats_service import ats_service

        result = await ats_service.get_ats_score(user_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"ATS analysis failed: {str(e)}"
        ) from e


@router.get("/skills-gap")
async def get_skills_gap(
    user_id: str = Query(..., description="User ID"),
    target_role: str | None = Query(None, description="Target role for gap analysis"),
) -> dict[str, Any]:
    """Analyze skills gap for target role."""
    try:
        result = await analysis_service.get_skills_gap(user_id, target_role)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Skills gap analysis failed: {str(e)}"
        ) from e


@router.get("/job-match")
async def get_job_match(
    user_id: str = Query(..., description="User ID"),
    role: str | None = Query(None, description="Target role for matching"),
) -> dict[str, Any]:
    """Get job matching score for specific role."""
    try:
        result = await analysis_service.get_job_match(user_id, role)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Job matching failed: {str(e)}"
        ) from e


@router.get("/career-path")
async def get_career_path(
    user_id: str = Query(..., description="User ID"),
) -> dict[str, Any]:
    """Get career path recommendations based on current profile."""
    try:
        result = await analysis_service.get_career_path(user_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Career path analysis failed: {str(e)}"
        ) from e
