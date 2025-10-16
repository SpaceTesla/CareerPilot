from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str
    user_id: str | None = None
    session_id: str | None = None
    include_sources: bool = True
    context: dict[str, Any] = Field(default_factory=dict)


class AgentChatResponse(BaseModel):
    message: str
    data: dict[str, Any] | None = None
    sources: list[str] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    model: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
