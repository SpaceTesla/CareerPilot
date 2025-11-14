import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile
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
            delete=False, suffix=Path(file.filename).suffix
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
