from datetime import datetime

from pydantic import BaseModel


class ChatResponse(BaseModel):
    message: str
    model: str
    timestamp: datetime
    success: bool = True


class ChatRequest(BaseModel):
    message: str
