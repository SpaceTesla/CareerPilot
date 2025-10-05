from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv(".env.local")


class Models:
    """Available Gemini models - use like settings.models.FLASH_LITE"""

    FLASH_LITE = "gemini-2.5-flash-lite"
    FLASH = "gemini-2.5-flash"
    PRO = "gemini-2.5-pro"


class Settings(BaseSettings):
    google_api_key: str = Field(..., description="Google API key for Gemini")
    model_name: str = Field(default=Models.FLASH, description="Gemini model to use")
    temperature: float = Field(
        default=0.0, ge=0.0, le=2.0, description="Model temperature (0-2)"
    )

    max_tokens: int | None = Field(
        default=None, description="Maximum tokens to generate"
    )
    timeout: int = Field(default=30, ge=1, description="Request timeout in seconds")

    class Config:
        env_file = ".env.local"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
models = Models()
