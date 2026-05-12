from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.infrastructure.database.connection import get_session
from app.infrastructure.database.repositories.conversation_repository import (
    ConversationRepository,
)
from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.services.agent import AgentService

router = APIRouter(prefix="/agent", tags=["agent"])

_agent = AgentService()


def _resolve_user_id(req: AgentChatRequest) -> str | None:
    if req.user_id:
        return req.user_id

    if req.session_id:
        with get_session() as session:
            conv_repo = ConversationRepository(session)
            conversation = conv_repo.get_by_id(req.session_id)
            if conversation:
                return conversation.user_id
    return None


def _save_chat_messages(
    user_id: str,
    conversation_id: str | None,
    user_message: str,
    ai_response: str,
    actions_taken: list[str] | None = None,
) -> str:
    """Save chat messages to database and return conversation_id."""
    with get_session() as session:
        repo = ConversationRepository(session)

        # Get or create conversation
        if conversation_id:
            conversation = repo.get_by_id(conversation_id)
            if not conversation:
                # Create new if provided ID doesn't exist
                conversation = repo.create_conversation(
                    user_id=user_id,
                    title=user_message[:50] + "..." if len(user_message) > 50 else user_message,
                )
        else:
            # Create new conversation with first message as title
            conversation = repo.create_conversation(
                user_id=user_id,
                title=user_message[:50] + "..." if len(user_message) > 50 else user_message,
            )

        # Save user message
        repo.add_message(
            conversation_id=conversation.id,
            role="user",
            content=user_message,
        )

        # Save AI response
        repo.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=ai_response,
            metadata={"actions_taken": actions_taken} if actions_taken else None,
        )

        return conversation.id


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(req: AgentChatRequest) -> AgentChatResponse:
    try:
        resolved_user_id = _resolve_user_id(req)
        if not resolved_user_id:
            raise HTTPException(
                status_code=400,
                detail="No resume session found. Please upload your resume again.",
            )

        result = await _agent.chat(resolved_user_id, req.message)

        # Save messages to database for chat history
        conversation_id = _save_chat_messages(
            user_id=resolved_user_id,
            conversation_id=req.conversation_id,
            user_message=req.message,
            ai_response=result.get("message", ""),
            actions_taken=result.get("actions_taken", []),
        )

        return AgentChatResponse(
            message=result.get("message", ""),
            data=result.get("data"),
            sources=result.get("sources", []),
            actions_taken=result.get("actions_taken", []),
            confidence=result.get("confidence", 1.0),
            model=None,
            success=True,
            conversation_id=conversation_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}") from e
