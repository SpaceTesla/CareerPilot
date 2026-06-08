from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel


class ServiceHealthDetail(BaseModel):
    status: str  # "connected", "disconnected"
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str  # "healthy", "unhealthy"
    version: str
    timestamp: datetime
    services: Dict[str, ServiceHealthDetail]
