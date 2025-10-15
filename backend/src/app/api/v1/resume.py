import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile

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

        return data

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Resume processing failed: {str(e)}"
        ) from e

    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
