"""
FastAPI endpoints for resume processing.
This shows how to integrate ResumeService into your FastAPI application.
"""

from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ...services.rag.resume_service import ResumeService

router = APIRouter(prefix="/resume", tags=["resume"])

# Initialize service (you might want to use dependency injection)
resume_service = ResumeService()


class ResumeResponse(BaseModel):
    """Response model for resume processing."""

    success: bool
    data: dict[str, Any]
    message: str


@router.post("/process-file", response_model=ResumeResponse)
async def process_resume_file(
    file_path: str,
    enrich: bool = True,
    save_output: bool = False,
) -> ResumeResponse:
    """
    Process a resume file from the filesystem.
    Supports both PDF and markdown files.

    Args:
        file_path: Path to the resume file (PDF or markdown)
        enrich: Whether to use LLM enrichment
        save_output: Whether to save output to file

    Returns:
        Processed resume data as JSON
    """
    try:
        data = resume_service.process_resume(
            file_path=file_path,
            enrich=enrich,
            save_output=save_output,
        )

        return ResumeResponse(
            success=True, data=data, message="Resume processed successfully"
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/process-text", response_model=ResumeResponse)
async def process_resume_text(
    markdown_text: str,
    source_file: str | None = None,
    enrich: bool = True,
) -> ResumeResponse:
    """
    Process resume from markdown text directly.

    Args:
        markdown_text: The markdown content as string
        source_file: Optional source file name for metadata
        enrich: Whether to use LLM enrichment

    Returns:
        Processed resume data as JSON
    """
    try:
        data = resume_service.process_resume_from_text(
            markdown_text=markdown_text,
            source_file=source_file,
            enrich=enrich,
        )

        return ResumeResponse(
            success=True, data=data, message="Resume processed successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/upload", response_model=ResumeResponse)
async def upload_and_process_resume(
    file: UploadFile = File(...),
    enrich: bool = True,
) -> ResumeResponse:
    """
    Upload and process a resume file.

    Args:
        file: Uploaded file
        enrich: Whether to use LLM enrichment

    Returns:
        Processed resume data as JSON
    """
    try:
        # Read file content
        content = await file.read()
        markdown_text = content.decode("utf-8")

        # Process the resume
        data = resume_service.process_resume_from_text(
            markdown_text=markdown_text,
            source_file=file.filename,
            enrich=enrich,
        )

        return ResumeResponse(
            success=True,
            data=data,
            message="Resume uploaded and processed successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Upload processing failed: {str(e)}"
        )


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "resume-processor"}
