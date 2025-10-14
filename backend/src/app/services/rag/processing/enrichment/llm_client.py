from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI


@dataclass
class LLMConfig:
    model: str = "gemini-1.5-flash"
    temperature: float = 0.0
    api_key_env: str = "GOOGLE_API_KEY"


class LLMClient:
    """Handles LLM model calls with error handling and retries."""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig()

    def _get_api_key(self) -> str | None:
        """Get API key from environment or settings fallback."""
        api_key = os.getenv(self.config.api_key_env)
        if not api_key:
            try:
                from app.core.config import settings  # type: ignore

                api_key = settings.google_api_key
                if self.config.model == "gemini-1.5-flash" and getattr(
                    settings, "model_name", None
                ):
                    self.config.model = settings.model_name
            except Exception:
                api_key = None
        return api_key

    def create_model(self) -> ChatGoogleGenerativeAI | None:
        """Create the LLM model instance."""
        api_key = self._get_api_key()
        if not api_key:
            return None

        return ChatGoogleGenerativeAI(
            model=self.config.model,
            temperature=self.config.temperature,
            convert_system_message_to_human=True,
        )

    def create_parser(self, schema_model: Any) -> PydanticOutputParser:
        """Create parser for the given schema."""
        return PydanticOutputParser(pydantic_object=schema_model)

    def call_model(
        self,
        model: ChatGoogleGenerativeAI,
        prompt: ChatPromptTemplate,
        inputs: dict[str, Any],
        parser: PydanticOutputParser,
    ) -> Any:
        """Execute the model call with the given prompt and inputs."""
        chain = prompt | model | parser
        return chain.invoke(inputs)
