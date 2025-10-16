from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings


class LLMClient:
    """Handles LLM model calls with error handling and retries."""

    def __init__(self) -> None:
        self.model_name = settings.model_name

    def create_model(self) -> ChatGoogleGenerativeAI | None:
        """Create the LLM model instance."""
        return ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=settings.temperature,
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
