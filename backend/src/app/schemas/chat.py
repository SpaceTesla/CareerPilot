from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# Agent capabilities and tools
class AgentTool(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class AgentCapability(BaseModel):
    name: str
    description: str
    tools: list[AgentTool] = Field(default_factory=list)


# Message types
class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


# Agent response with structured data
class AgentResponse(BaseModel):
    message: str
    data: dict[str, Any] | None = None  # Structured data from resume
    sources: list[str] = Field(default_factory=list)  # Sources used
    actions_taken: list[str] = Field(default_factory=list)  # Actions performed
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)  # Confidence score
    model: str
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool = True


# Minimal chat response used by chat endpoints
class ChatResponse(BaseModel):
    message: str
    model: str
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool = True


# Enhanced request with context
class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None
    session_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    include_sources: bool = True
    stream: bool = False


# Conversation management
class Conversation(BaseModel):
    id: str
    user_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


# Agent status and capabilities
class AgentStatus(BaseModel):
    status: Literal["active", "processing", "idle", "error"]
    capabilities: list[AgentCapability] = Field(default_factory=list)
    last_activity: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
