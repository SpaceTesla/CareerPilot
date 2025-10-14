"""
High-level service for resume processing with API-friendly interface.
Orchestrates resume processing and handles file operations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .processing.resume_processor import ResumeProcessor


class ResumeService:
    """
    High-level service for resume processing with API-friendly interface.
    Orchestrates resume processing and handles file operations.
    """

    def __init__(
        self,
        processor: ResumeProcessor | None = None,
    ) -> None:
        self.processor = processor or ResumeProcessor()

    def process_resume(
        self,
        file_path: str | Path,
        enrich: bool = True,
        save_output: bool = False,
        output_path: str | Path | None = None,
        save_markdown: bool = False,
    ) -> dict[str, Any]:
        """
        Process a resume file and return structured JSON data.
        Automatically detects if input is PDF or markdown.

        Args:
            file_path: Path to the resume file (PDF or markdown)
            enrich: Whether to enrich the data using LLM
            save_output: Whether to save the output to a file
            output_path: Custom output path (auto-generated if not provided)
            save_markdown: Whether to save intermediate markdown (for PDF inputs)

        Returns:
            Dictionary containing the processed resume data
        """
        # Process the resume using the processor
        data = self.processor.process(
            file_path=file_path,
            enrich=enrich,
            save_markdown=save_markdown,
        )

        # Save output if requested
        if save_output:
            output_path = output_path or self._generate_output_path(Path(file_path))
            self._save_json(data, output_path)

        return data

    def process_resume_from_text(
        self,
        markdown_text: str,
        source_file: str | None = None,
        enrich: bool = True,
    ) -> dict[str, Any]:
        """
        Process resume from markdown text directly.

        Args:
            markdown_text: The markdown content as string
            source_file: Optional source file name for metadata
            enrich: Whether to enrich the data using LLM

        Returns:
            Dictionary containing the processed resume data
        """
        # Create temporary file for processing
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(markdown_text)
            temp_path = Path(f.name)

        try:
            return self.process_resume(
                temp_path,
                enrich=enrich,
                save_output=False,
                source_file=source_file,
            )
        finally:
            # Clean up temporary file
            temp_path.unlink(missing_ok=True)

    def _generate_output_path(self, input_path: Path) -> Path:
        """Generate output path based on input file."""
        output_dir = Path("processed")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create clean filename
        base_name = input_path.stem.lower()
        base_name = base_name.replace(" ", "-")
        # Remove special characters
        import re

        base_name = re.sub(r"[^a-z0-9\-]+", "", base_name)

        return output_dir / f"{base_name}.resume.v1.json"

    def _save_json(self, data: dict[str, Any], output_path: Path) -> None:
        """Save data to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        output_path.write_text(json_str, encoding="utf-8")
        print(f"Saved resume data to: {output_path}")
