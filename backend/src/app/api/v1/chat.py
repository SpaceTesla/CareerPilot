from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.schemas.chat import ChatResponse
from app.services.chat_service import chat_service

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/", response_model=ChatResponse)
async def chat_route(
    message: str = Query(..., description="The user message to send to the AI"),
):
    """
    Chat endpoint that processes user messages and returns AI responses.

    Args:
        message: The user message to send to the AI

    Returns:
        ChatResponse: Structured response with AI message, model info, and metadata
    """

    try:
        return await chat_service.process_message(message)
    except Exception as e:
        logger.error(f"Chat route error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Chat service error: {str(e)}"
        ) from e
