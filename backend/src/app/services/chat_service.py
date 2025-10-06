from datetime import datetime

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
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
        # Build a simple LCEL chain: Prompt → Model → String parser
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are a cool assistant and you talk Gen Z."),
                ("user", "{message}"),
            ]
        )
        self.chain = self.prompt | self.chat | StrOutputParser()

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

            # Use the chain to produce a full (non-streaming) response
            response_text = await self.chain.ainvoke({"message": message})

            logger.info(
                f"Chat response using {self.model_used}: {str(response_text)[:10]}..."
            )

            return ChatResponse(
                message=str(response_text),
                model=self.model_used,
                timestamp=datetime.now(),
                success=True,
            )
        except Exception as e:
            logger.error(f"Chat service error: {str(e)}")
            raise e

    async def stream_message(self, message: str):
        """
        Stream response using a modern LCEL chain. Emits string chunks directly.
        """
        try:
            logger.info(f"Streaming chat request: {message[:10]}...")
            async for chunk in self.chain.astream({"message": message}):
                # chunk is already a string segment from StrOutputParser
                if chunk:
                    yield chunk
        except Exception as e:
            logger.error(f"Chat streaming error: {str(e)}")
            raise e


# Create a singleton instance
chat_service = ChatService()
