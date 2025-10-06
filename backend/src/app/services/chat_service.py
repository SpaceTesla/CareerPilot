from datetime import datetime

from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import models, settings
from app.core.logging import get_logger
from app.schemas.chat import ChatResponse

logger = get_logger(__name__)


class ChatService:
    def __init__(self):
        self.model_used = models.FLASH
        self.chat = ChatGoogleGenerativeAI(
            model=self.model_used,
            temperature=settings.temperature,
        )
        self.system_prompt = SystemMessage(
            content="""You are a cool assistant and you talk Gen Z."""
        )

    async def process_message(self, message: str) -> ChatResponse:
        """
        Process a chat message and return a structured response.

        Args:
            message: The user message to process

        Returns:
            ChatResponse: Structured response with message,
            model, timestamp, and success status
        """
        try:
            logger.info(f"Processing chat request: {message[:10]}...")

            response = self.chat.invoke([self.system_prompt, message])

            logger.info(
                f"Chat response using {self.model_used}: {response.content[:10]}..."
            )

            return ChatResponse(
                message=str(response.content),
                model=self.model_used,
                timestamp=datetime.now(),
                success=True,
            )
        except Exception as e:
            logger.error(f"Chat service error: {str(e)}")
            raise e


# Create a singleton instance
chat_service = ChatService()
