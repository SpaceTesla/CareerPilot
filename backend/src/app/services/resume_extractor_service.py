from __future__ import annotations

import io
import re

from fastapi import HTTPException
import pdfplumber
from docx import Document

from app.core.logging import get_logger

logger = get_logger(__name__)


class ResumeExtractorService:
    """
    Handles file format validation, binary text extraction (PDF/DOCX), and text normalization.
    """

    @staticmethod
    def extract_text(file_bytes: bytes, file_name: str) -> str:
        """
        Extracts raw text from PDF or DOCX file bytes.
        """
        ext = file_name.split(".")[-1].lower()

        if ext == "pdf":
            try:
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    # Check if pdf is encrypted/password protected
                    if pdf.doc.is_encrypted:
                        raise HTTPException(
                            status_code=400,
                            detail="File is encrypted or password-protected",
                        )

                    text = ""
                    for page in pdf.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"

                    return text
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error reading PDF: {e}")
                # Check for password/decryption signatures
                err_str = str(e).lower()
                if "password" in err_str or "decrypt" in err_str:
                    raise HTTPException(
                        status_code=400,
                        detail="File is encrypted or password-protected",
                    ) from e
                raise HTTPException(
                    status_code=422,
                    detail="Error parsing PDF document. Ensure it is a valid PDF.",
                ) from e

        elif ext == "docx":
            try:
                doc = Document(io.BytesIO(file_bytes))
                text = ""
                for p in doc.paragraphs:
                    if p.text:
                        text += p.text + "\n"
                return text
            except Exception as e:
                logger.error(f"Error reading DOCX: {e}")
                raise HTTPException(
                    status_code=422,
                    detail="Error parsing DOCX document. Ensure it is a valid DOCX.",
                ) from e

        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Please upload a PDF or DOCX file.",
            )

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Cleans and normalizes extracted text.
        Strips control characters, normalizes whitespace and newlines.
        """
        if not text:
            return ""

        # Remove control characters except newline and tab
        text = "".join(ch for ch in text if ch >= " " or ch in "\n\t")

        # Standardize vertical spacing (max 2 consecutive newlines)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Normalize horizontal spacing
        text = re.sub(r"[ \t]+", " ", text)

        # Remove leading/trailing line spacing
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        return text.strip()
