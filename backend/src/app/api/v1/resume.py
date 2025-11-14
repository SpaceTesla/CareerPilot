import os
import tempfile
from pathlib import Path as PathLib
from typing import Any

from fastapi import APIRouter, HTTPException, Query, UploadFile
from fastapi.params import Path
from sqlalchemy.orm import Session

from ...infrastructure.database.connection import get_session
from ...infrastructure.database.models import ResumeProfile
from ...infrastructure.database.repositories.conversation_repository import (
    ConversationRepository,
)
from ...infrastructure.database.repositories.resume_repository import (
    ResumeRepository,
)
from ...infrastructure.database.repositories.user_repository import UserRepository
from ...services.resume_processing.resume_service import ResumeService

router = APIRouter(prefix="/resume", tags=["resume"])

# Initialize service
resume_service = ResumeService()


@router.post("/upload")
async def upload_and_process_resume(
    file: UploadFile,
    enrich: bool = True,
) -> dict[str, Any]:
    """
    Upload and process a resume file.

    Returns the processed resume data as JSON directly.
    Later this will be saved to database.

    Args:
        file: Uploaded file (PDF or markdown)
        enrich: Whether to use LLM enrichment (default: True)

    Returns:
        Processed resume data as JSON
    """
    temp_file_path = None

    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=PathLib(file.filename).suffix
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Process the resume using the proper method that handles PDFs and markdown
        data = resume_service.process_resume(
            file_path=temp_file_path,
            enrich=enrich,
            save_output=False,
        )

        # Persist to Postgres
        with get_session() as session:  # type: Session
            user_id, profile_id = _persist_resume_json(session, data)
            session_id = _ensure_session(session, user_id)

        # Return identifiers along with processed resume
        return {
            "user_id": user_id,
            "profile_id": profile_id,
            "session_id": session_id,
            "data": data,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Resume processing failed: {str(e)}"
        ) from e

    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def _persist_resume_json(session: Session, data: dict[str, Any]) -> tuple[str, str]:
    """Save resume JSON; return (user_id, profile_id)."""
    user_repo = UserRepository(session)
    resume_repo = ResumeRepository(session)

    email = data.get("email") or "unknown@example.com"
    user = user_repo.get_or_create_by_email(email)

    import uuid

    profile = ResumeProfile(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name=data.get("name"),
        email=data.get("email"),
        phone=data.get("phone"),
        location=data.get("location"),
        socials_json=data.get("socials"),
        summary=data.get("summary"),
        raw_data=data,
    )
    resume_repo.create_profile(profile)
    return user.id, profile.id


def _ensure_session(session: Session, user_id: str) -> str:
    """Create a new conversation session for the user and return its ID."""
    conv_repo = ConversationRepository(session)
    conversation = conv_repo.create_conversation(user_id=user_id)
    return conversation.id


@router.get("/user/{user_id}")
async def get_resume_by_user(user_id: str = Path(..., description="User ID")) -> dict[str, Any]:
    """Get the latest resume data by user ID."""
    try:
        with get_session() as session:  # type: Session
            repo = ResumeRepository(session)
            profiles = repo.get_by_user(user_id)
            if not profiles:
                raise HTTPException(status_code=404, detail="No resume profile found for this user")

            # Get the most recent profile
            profile = sorted(profiles, key=lambda p: p.updated_at or p.created_at, reverse=True)[0]

            return {
                "id": profile.id,
                "user_id": profile.user_id,
                "name": profile.name,
                "email": profile.email,
                "phone": profile.phone,
                "location": profile.location,
                "socials": profile.socials_json,
                "summary": profile.summary,
                "raw_data": profile.raw_data,
                "created_at": profile.created_at.isoformat() if profile.created_at else None,
                "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve resume: {str(e)}"
        ) from e


@router.get("/{profile_id}")
async def get_resume_profile(profile_id: str = Path(..., description="Profile ID")) -> dict[str, Any]:
    """Get full resume data by profile ID."""
    try:
        with get_session() as session:  # type: Session
            repo = ResumeRepository(session)
            profile = repo.get_by_id(profile_id)
            if not profile:
                raise HTTPException(status_code=404, detail="Resume profile not found")

            return {
                "id": profile.id,
                "user_id": profile.user_id,
                "name": profile.name,
                "email": profile.email,
                "phone": profile.phone,
                "location": profile.location,
                "socials": profile.socials_json,
                "summary": profile.summary,
                "raw_data": profile.raw_data,
                "created_at": profile.created_at.isoformat() if profile.created_at else None,
                "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve resume: {str(e)}"
        ) from e


@router.post("/{profile_id}/export")
async def export_resume(
    profile_id: str = Path(..., description="Profile ID"),
    format: str = Query("pdf", description="Export format (pdf or json)"),
) -> dict[str, Any]:
    """Export resume as PDF or JSON."""
    try:
        with get_session() as session:  # type: Session
            repo = ResumeRepository(session)
            profile = repo.get_by_id(profile_id)
            if not profile:
                raise HTTPException(status_code=404, detail="Resume profile not found")

            if format.lower() == "json":
                return {
                    "format": "json",
                    "data": {
                        "name": profile.name,
                        "email": profile.email,
                        "phone": profile.phone,
                        "location": profile.location,
                        "socials": profile.socials_json,
                        "summary": profile.summary,
                        "raw_data": profile.raw_data,
                    },
                }
            elif format.lower() == "pdf":
                # For now, return a message indicating PDF export would be implemented
                # In production, use a library like reportlab or weasyprint
                return {
                    "format": "pdf",
                    "message": "PDF export is not yet implemented. Use JSON format for now.",
                    "data_available": True,
                }
            else:
                raise HTTPException(
                    status_code=400, detail=f"Unsupported format: {format}. Use 'pdf' or 'json'"
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Export failed: {str(e)}"
        ) from e


@router.get("/{profile_id}/comparison")
async def compare_resume(
    profile_id: str = Path(..., description="Profile ID"),
) -> dict[str, Any]:
    """Compare resume with industry standards."""
    try:
        with get_session() as session:  # type: Session
            repo = ResumeRepository(session)
            profile = repo.get_by_id(profile_id)
            if not profile:
                raise HTTPException(status_code=404, detail="Resume profile not found")

            raw_data = profile.raw_data or {}
            skills = raw_data.get("skills", {})
            experience = raw_data.get("experience", [])
            education = raw_data.get("education", [])

            # Industry standards
            industry_standards = {
                "skills": {
                    "average_count": 15,
                    "recommended_categories": 3,  # languages, frameworks, tools
                },
                "experience": {
                    "average_positions": 3,
                    "recommended_bullets_per_position": 3,
                },
                "education": {
                    "average_degrees": 1,
                    "recommended_gpa_included": True,
                },
                "contact_info": {
                    "required_fields": ["name", "email", "phone", "location"],
                },
            }

            # Compare against standards
            total_skills = (
                len(skills.get("languages", []))
                + len(skills.get("frameworks", []))
                + len(skills.get("tools", []))
            )

            comparison = {
                "skills": {
                    "your_count": total_skills,
                    "industry_average": industry_standards["skills"]["average_count"],
                    "status": "above_average" if total_skills >= 15 else "below_average",
                },
                "experience": {
                    "your_count": len(experience),
                    "industry_average": industry_standards["experience"]["average_positions"],
                    "status": "above_average" if len(experience) >= 3 else "below_average",
                },
                "education": {
                    "your_count": len(education),
                    "industry_average": industry_standards["education"]["average_degrees"],
                    "status": "meets_standard" if len(education) >= 1 else "below_average",
                },
                "contact_completeness": {
                    "your_score": sum(
                        1
                        for field in ["name", "email", "phone", "location"]
                        if getattr(profile, field, None)
                    ),
                    "required": len(industry_standards["contact_info"]["required_fields"]),
                    "status": "complete"
                    if sum(
                        1
                        for field in ["name", "email", "phone", "location"]
                        if getattr(profile, field, None)
                    )
                    >= 3
                    else "incomplete",
                },
            }

            return {
                "profile_id": profile_id,
                "comparison": comparison,
                "industry_standards": industry_standards,
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Comparison failed: {str(e)}"
        ) from e
