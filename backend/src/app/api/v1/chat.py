from typing import Any

from fastapi import APIRouter, HTTPException, Query, Path
from sse_starlette.sse import EventSourceResponse

from app.core.logging import get_logger
from app.infrastructure.database.connection import get_session
from app.infrastructure.database.repositories.conversation_repository import (
    ConversationRepository,
)
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


# ===== Chat History Endpoints =====

@router.get("/history")
async def get_chat_history(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(50, description="Maximum number of conversations to return"),
) -> dict[str, Any]:
    """Get all chat conversations for a user."""
    try:
        with get_session() as session:
            repo = ConversationRepository(session)
            conversations = repo.get_by_user(user_id, limit=limit)

            return {
                "conversations": [
                    {
                        "id": conv.id,
                        "title": conv.title or "New Chat",
                        "created_at": conv.created_at.isoformat() if conv.created_at else None,
                        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                    }
                    for conv in conversations
                ],
                "total": len(conversations),
            }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve chat history: {str(e)}"
        ) from e


@router.get("/history/{conversation_id}")
async def get_conversation_messages(
    conversation_id: str = Path(..., description="Conversation ID"),
    limit: int = Query(100, description="Maximum number of messages to return"),
) -> dict[str, Any]:
    """Get all messages in a specific conversation."""
    try:
        with get_session() as session:
            repo = ConversationRepository(session)
            conversation = repo.get_by_id(conversation_id)

            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

            messages = repo.get_messages(conversation_id, limit=limit)

            return {
                "conversation": {
                    "id": conversation.id,
                    "title": conversation.title or "New Chat",
                    "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                },
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                        "metadata": msg.metadata_json,
                    }
                    for msg in messages
                ],
                "total": len(messages),
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve conversation: {str(e)}"
        ) from e


@router.post("/history")
async def create_conversation(
    user_id: str = Query(..., description="User ID"),
    title: str | None = Query(None, description="Conversation title"),
) -> dict[str, Any]:
    """Create a new conversation."""
    try:
        with get_session() as session:
            repo = ConversationRepository(session)
            conversation = repo.create_conversation(user_id=user_id, title=title)

            return {
                "id": conversation.id,
                "title": conversation.title or "New Chat",
                "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create conversation: {str(e)}"
        ) from e


@router.delete("/history/{conversation_id}")
async def delete_conversation(
    conversation_id: str = Path(..., description="Conversation ID"),
) -> dict[str, Any]:
    """Delete a conversation and all its messages."""
    try:
        with get_session() as session:
            repo = ConversationRepository(session)
            deleted = repo.delete_conversation(conversation_id)

            if not deleted:
                raise HTTPException(status_code=404, detail="Conversation not found")

            return {"success": True, "message": "Conversation deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete conversation: {str(e)}"
        ) from e
