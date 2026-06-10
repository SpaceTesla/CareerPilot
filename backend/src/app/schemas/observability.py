from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class InstrumentationStatus(BaseModel):
    name: str
    enabled: bool

class TelemetryStatusResponse(BaseModel):
    collector_status: str
    exporter_type: str
    active_instrumentations: List[str]
    traces_sent_count: int
    last_export_timestamp: datetime

class CircuitBreakerStatus(BaseModel):
    service_name: str
    state: str
    failure_count: int
    last_failure_at: Optional[datetime] = None

class CircuitBreakerList(BaseModel):
    circuits: List[CircuitBreakerStatus]

class PerformanceBaselineItem(BaseModel):
    endpoint: str
    p50_latency_ms: int
    p95_latency_ms: int
    p99_latency_ms: int
    max_concurrency: int

class PerformanceBaselinesResponse(BaseModel):
    performance_baselines: List[PerformanceBaselineItem]
    last_updated_at: datetime

class ADRItem(BaseModel):
    id: str
    title: str
    status: str
    date: str
    summary: str

class ADRListResponse(BaseModel):
    adrs: List[ADRItem]
