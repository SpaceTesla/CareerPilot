from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .llm_client import LLMClient, LLMConfig
from .prompt_builder import PromptBuilder
from .validator import ResultValidator


@dataclass
class EnrichmentConfig:
    model: str = "gemini-2.5-flash"
    temperature: float = 0.0
    api_key_env: str = "GOOGLE_API_KEY"
    preserve_metadata: bool = True


class EnrichmentOrchestrator:
    """Orchestrates the complete enrichment workflow using separate agents."""

    def __init__(self, config: EnrichmentConfig | None = None) -> None:
        self.config = config or EnrichmentConfig()

        # Initialize agents
        llm_config = LLMConfig(
            model=self.config.model,
            temperature=self.config.temperature,
            api_key_env=self.config.api_key_env,
        )
        self.llm_client = LLMClient(llm_config)
        self.prompt_builder = PromptBuilder()
        self.result_validator = ResultValidator(
            preserve_metadata=self.config.preserve_metadata
        )

    def enrich(
        self,
        cleaned_text: str,
        resume_json: dict[str, Any],
        schema_model: Any,
        source_snippet_limit: int = 16000,
    ) -> dict[str, Any]:
        """Enrich resume data using the complete agent workflow."""
        # 1. Create model and parser
        model = self.llm_client.create_model()
        if not model:
            print(
                "[EnrichmentOrchestrator] Skipped: API key not available and "
                "settings fallback failed."
            )
            return resume_json

        parser = self.llm_client.create_parser(schema_model)

        # 2. Build prompt
        prompt = self.prompt_builder.build_prompt(schema_model)
        format_instructions = parser.get_format_instructions()

        # 3. Prepare inputs
        source_snippet = cleaned_text[:source_snippet_limit]
        inputs = self.prompt_builder.prepare_inputs(
            schema_model=schema_model,
            current_extraction=resume_json,
            source_text=source_snippet,
            format_instructions=format_instructions,
        )

        # 4. Call model
        try:
            result = self.llm_client.call_model(model, prompt, inputs, parser)
            enriched_data = result.model_dump(mode="json")
        except Exception as e:
            print(f"[EnrichmentOrchestrator] Error during enrichment: {e}")
            return resume_json

        # 5. Validate and clean result
        validation_result = self.result_validator.validate_and_clean(
            enriched_data, resume_json
        )

        if not validation_result.is_valid:
            print(
                f"[EnrichmentOrchestrator] Validation errors: {validation_result.errors}"
            )
            return resume_json

        print(f"[EnrichmentOrchestrator] Enrichment applied using {self.config.model}")
        return validation_result.data
