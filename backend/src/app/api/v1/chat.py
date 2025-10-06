from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

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


@router.get("/stream")
async def chat_stream_route(
    message: str = Query(..., description="The user message to send to the AI"),
):
    """
    SSE streaming endpoint. Streams tokens as they are generated.

    Events:
    - event: meta (once)
    - event: token (many)
    - event: end (once)
    """

    async def event_generator():
        # Send initial metadata
        yield {
            "event": "meta",
            "data": {
                "model": chat_service.model_used,
            },
        }

        # Stream token chunks
        async for chunk in chat_service.stream_message(message):
            yield {
                "event": "token",
                "data": chunk,
            }

        # Signal completion
        yield {
            "event": "end",
            "data": "[DONE]",
        }

    return EventSourceResponse(event_generator())
