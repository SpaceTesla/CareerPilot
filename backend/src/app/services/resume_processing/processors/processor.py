"""
Main resume processing orchestrator.
Handles the complete PDF -> JSON pipeline.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pymupdf4llm

from .extractor import GeminiEnricher, ResumeExtractor


class ResumeProcessor:
    """
    Main processor for resume files.
    Handles PDF to markdown conversion and resume extraction.
    """

    def __init__(
        self,
        extractor: ResumeExtractor | None = None,
        enricher: GeminiEnricher | None = None,
    ) -> None:
        self.extractor = extractor or ResumeExtractor()
        self.enricher = enricher or GeminiEnricher()

    def process(
        self,
        file_path: str | Path,
        enrich: bool = True,
        save_markdown: bool = False,
    ) -> dict[str, Any]:
        """
        Process a resume file and return structured JSON data.
        Automatically detects if input is PDF or markdown.

        Args:
            file_path: Path to the resume file (PDF or markdown)
            enrich: Whether to enrich the data using LLM
            save_markdown: Whether to save intermediate markdown (for PDF inputs)

        Returns:
            Dictionary containing the processed resume data
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Resume file not found: {file_path}")

        # Check if it's a PDF file
        if file_path.suffix.lower() == ".pdf":
            return self._process_pdf(file_path, enrich, save_markdown)
        else:
            return self._process_markdown(file_path, enrich)

    def _process_pdf(
        self,
        pdf_path: Path,
        enrich: bool = True,
        save_markdown: bool = False,
    ) -> dict[str, Any]:
        """Process PDF resume by converting to markdown first."""
        # Convert PDF to markdown
        markdown_text = pymupdf4llm.to_markdown(str(pdf_path))

        # Save markdown if requested
        if save_markdown:
            markdown_path = self._generate_markdown_path(pdf_path)
            markdown_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_path.write_text(markdown_text, encoding="utf-8")
            print(f"Saved markdown to: {markdown_path}")

        # Process the markdown text
        return self._process_markdown_text(
            markdown_text=markdown_text,
            source_file=str(pdf_path),
            enrich=enrich,
        )

    def _process_markdown(
        self,
        markdown_path: Path,
        enrich: bool = True,
    ) -> dict[str, Any]:
        """Process markdown resume directly."""
        # Read markdown content
        markdown_text = markdown_path.read_text(encoding="utf-8")

        # Process the text
        return self._process_markdown_text(
            markdown_text=markdown_text,
            source_file=str(markdown_path),
            enrich=enrich,
        )

    def _process_markdown_text(
        self,
        markdown_text: str,
        source_file: str,
        enrich: bool = True,
    ) -> dict[str, Any]:
        """Process markdown text and return JSON data."""
        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(markdown_text)
            temp_path = Path(f.name)

        try:
            # Extract resume data
            resume = self.extractor.from_markdown(temp_path, source_file=source_file)
            data = resume.model_dump(mode="json")

            # Enrich if requested
            if enrich:
                data = self.enricher.enrich(
                    cleaned_text=markdown_text, resume_json=data
                )

            return data
        finally:
            # Clean up temporary file
            temp_path.unlink(missing_ok=True)

    def _generate_markdown_path(self, pdf_path: Path) -> Path:
        """Generate markdown output path based on PDF file."""
        output_dir = Path("processed")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create clean filename
        base_name = pdf_path.stem.lower()
        base_name = base_name.replace(" ", "-")
        # Remove special characters
        import re

        base_name = re.sub(r"[^a-z0-9\-]+", "", base_name)

        return output_dir / f"{base_name}.md"
