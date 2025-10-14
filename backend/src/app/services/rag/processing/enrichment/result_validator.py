from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    is_valid: bool
    data: dict[str, Any]
    errors: list[str]


class ResultValidator:
    """Validates and cleans LLM enrichment results."""

    def __init__(self, preserve_metadata: bool = True) -> None:
        self.preserve_metadata = preserve_metadata

    def validate_and_clean(
        self,
        enriched_data: dict[str, Any],
        original_data: dict[str, Any],
    ) -> ValidationResult:
        """Validate the enriched data and preserve metadata from original."""
        errors = []

        # Preserve metadata fields if configured
        if self.preserve_metadata:
            if "schemaVersion" in original_data:
                enriched_data["schemaVersion"] = original_data["schemaVersion"]
            if "source_file" in original_data:
                enriched_data["source_file"] = original_data["source_file"]

        # Basic validation checks
        if not isinstance(enriched_data, dict):
            errors.append("Enriched data must be a dictionary")
            return ValidationResult(is_valid=False, data=original_data, errors=errors)

        # Check for required fields (basic structure validation)
        required_fields = [
            "name",
            "email",
            "phone",
            "socials",
            "education",
            "experience",
            "projects",
            "skills",
            "achievements",
        ]
        missing_fields = [
            field for field in required_fields if field not in enriched_data
        ]

        if missing_fields:
            errors.append(f"Missing required fields: {missing_fields}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            data=enriched_data,
            errors=errors,
        )
