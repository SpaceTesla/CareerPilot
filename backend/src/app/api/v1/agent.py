from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.services.agent import AgentService

router = APIRouter(prefix="/agent", tags=["agent"])

_agent = AgentService()


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(req: AgentChatRequest) -> AgentChatResponse:
    try:
        result = await _agent.chat(req.user_id, req.message)
        return AgentChatResponse(
            message=result.get("message", ""),
            data=result.get("data"),
            sources=result.get("sources", []),
            actions_taken=result.get("actions_taken", []),
            confidence=result.get("confidence", 1.0),
            model=None,
            success=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}") from e
