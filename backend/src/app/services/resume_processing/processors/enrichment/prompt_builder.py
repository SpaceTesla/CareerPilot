from __future__ import annotations

import json as _json
from dataclasses import dataclass
from typing import Any

from langchain_core.prompts import ChatPromptTemplate


@dataclass
class PromptConfig:
    system_template: str
    user_template: str


class PromptBuilder:
    """Builds prompts for LLM enrichment with schema validation."""

    def __init__(self, config: PromptConfig | None = None) -> None:
        self.config = config or self._default_config()

    def _default_config(self) -> PromptConfig:
        return PromptConfig(
            system_template=(
                "You are a resume normalizer. Return ONLY a valid JSON object that "
                "matches the provided schema. Fix segmentation for experience (role, "
                "company, period, details), clean markdown/bold artifacts, and do not "
                "hallucinate. If unknown, leave as null or empty arrays."
            ),
            user_template=(
                "SCHEMA (Pydantic JSON schema):\n{schema}\n\n"
                "CURRENT_EXTRACTION (noisy; fix it, keep truth consistent with "
                "source):\n{current}\n\nSOURCE_TEXT (ground truth; use to correct "
                "splits and fill missing values):\n{source}\n\n{format_instructions}"
            ),
        )

    def build_prompt(self, schema_model: Any) -> ChatPromptTemplate:
        """Build the complete prompt template for enrichment."""
        return ChatPromptTemplate.from_messages(
            [
                ("system", self.config.system_template),
                ("user", self.config.user_template),
            ]
        )

    def prepare_inputs(
        self,
        schema_model: Any,
        current_extraction: dict[str, Any],
        source_text: str,
        format_instructions: str,
    ) -> dict[str, Any]:
        """Prepare inputs for the prompt."""
        return {
            "schema": _json.dumps(schema_model.model_json_schema(), ensure_ascii=False),
            "current": _json.dumps(current_extraction, ensure_ascii=False),
            "source": source_text,
            "format_instructions": format_instructions,
        }
