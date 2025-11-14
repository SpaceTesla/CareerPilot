"""Course recommendations API routes."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.services.agent.tools.course_recommendation_tools import (
    recommend_courses_with_context_tool,
)

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("/recommendations")
async def get_course_recommendations(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(10, ge=1, le=20, description="Maximum number of recommendations"),
) -> dict[str, Any]:
    """Get personalized course recommendations based on resume."""
    try:
        result = await recommend_courses_with_context_tool(user_id)

        if "error" in result:
            # Return empty courses instead of error
            return {
                "courses": [],
                "total": 0,
                "role_focus": result.get("user_profile", {}).get("primary_role", "General"),
            }

        # The tool returns recommendations in a "recommendations" key
        recommendations = result.get("recommendations", [])
        user_profile = result.get("user_profile", {})
        
        if isinstance(recommendations, list) and len(recommendations) > 0:
            # Map the recommendations to the expected format
            courses = []
            for rec in recommendations[:limit]:
                courses.append({
                    "title": rec.get("title", ""),
                    "description": rec.get("description", ""),
                    "url": rec.get("url", ""),
                    "provider": rec.get("platform", "Online Platform"),
                })
            
            return {
                "courses": courses,
                "total": len(recommendations),
                "role_focus": user_profile.get("primary_role", "General"),
            }
        else:
            # No recommendations found
            return {
                "courses": [],
                "total": 0,
                "role_focus": user_profile.get("primary_role", "General"),
                "message": "No course recommendations found. Try again later or ask the chat agent for suggestions.",
            }
    except Exception as e:
        # Return empty courses instead of error
        return {
            "courses": [],
            "total": 0,
            "role_focus": "General",
            "message": f"Unable to fetch course recommendations: {str(e)}",
        }

