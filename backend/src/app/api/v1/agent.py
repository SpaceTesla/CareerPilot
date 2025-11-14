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
        return AgentChatResponse(
            message=result.get("message", ""),
            data=result.get("data"),
            sources=result.get("sources", []),
            actions_taken=result.get("actions_taken", []),
            confidence=result.get("confidence", 1.0),
            model=None,
            success=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}") from e
