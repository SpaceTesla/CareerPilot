import re

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(".env.local")


class Models:
    """Available Gemini models - use like settings.models.FLASH_LITE"""

    FLASH_LITE = "gemini-2.5-flash-lite"
    FLASH = "gemini-2.5-flash"
    PRO = "gemini-2.5-pro"


class Settings(BaseSettings):
    app_name: str = Field(default="CareerPilot", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")

    tavily_api_key: str = Field(..., description="Tavily API key")
    
    # Job search API (JSearch from RapidAPI - optional, falls back to Tavily if not set)
    jsearch_api_key: str | None = Field(
        default=None, description="JSearch API key from RapidAPI (optional)"
    )
    jsearch_api_host: str = Field(
        default="jsearch.p.rapidapi.com", description="JSearch API host"
    )

    google_api_key: str = Field(..., description="Google API key for Gemini")
    model_name: str = Field(default=Models.FLASH, description="Gemini model to use")
    temperature: float = Field(
        default=0.0, ge=0.0, le=2.0, description="Model temperature (0-2)"
    )

    max_tokens: int | None = Field(
        default=None, description="Maximum tokens to generate"
    )
    timeout: int = Field(default=30, ge=1, description="Request timeout in seconds")

    # Database configuration
    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/careerpilot",
        description="SQLAlchemy Database URL",
    )
    pgvector_enabled: bool = Field(
        default=True, description="Enable pgvector extension for embeddings"
    )
    
    # CORS configuration
    cors_origins: str = Field(
        default="*",
        description="CORS allowed origins (comma-separated, use * for all)",
    )

    @field_validator("google_api_key")
    @classmethod
    def validate_google_api_key(cls, v: str) -> str:
        """Validate Google API key format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Google API key cannot be empty")

        # Basic format validation for Google API keys
        if not re.match(r"^[A-Za-z0-9_-]{20,}$", v.strip()):
            raise ValueError("Invalid Google API key format")

        return v.strip()

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name is one of the supported models."""
        valid_models = [Models.FLASH_LITE, Models.FLASH, Models.PRO]
        if v not in valid_models:
            raise ValueError(f"Model must be one of: {', '.join(valid_models)}")
        return v

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from env file
    )


settings = Settings()
models = Models()
