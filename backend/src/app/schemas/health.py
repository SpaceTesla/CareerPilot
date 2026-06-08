from datetime import datetime

from pydantic import BaseModel


class ServiceHealthDetail(BaseModel):
    status: str  # "connected", "disconnected"
    latency_ms: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str  # "healthy", "unhealthy"
    version: str
    timestamp: datetime
    services: dict[str, ServiceHealthDetail]
