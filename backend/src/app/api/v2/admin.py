from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Dict, Any

from app.schemas.observability import (
    TelemetryStatusResponse,
    CircuitBreakerList,
    CircuitBreakerStatus,
    PerformanceBaselinesResponse,
    PerformanceBaselineItem
)
from app.services.observability_telemetry_service import ObservabilityTelemetryService
from app.services.reliability_manager_service import ReliabilityManagerService
from app.services.performance_benchmark_service import PerformanceBenchmarkService

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/telemetry/status", response_model=TelemetryStatusResponse)
async def get_telemetry_status():
    """
    Retrieves status metrics and configurations from the OpenTelemetry tracer exporter.
    """
    try:
        status = ObservabilityTelemetryService.get_status()
        return TelemetryStatusResponse(
            collector_status=status["collector_status"],
            exporter_type=status["exporter_type"],
            active_instrumentations=status["active_instrumentations"],
            traces_sent_count=status["traces_sent_count"],
            last_export_timestamp=status["last_export_timestamp"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch telemetry status: {e}")

@router.get("/reliability/circuits", response_model=CircuitBreakerList)
async def get_circuit_breaker_states():
    """
    Gathers active circuit breaker statuses and failure metrics.
    """
    try:
        circuits = await ReliabilityManagerService.get_circuits()
        circuit_statuses = [
            CircuitBreakerStatus(
                service_name=c["service_name"],
                state=c["state"],
                failure_count=c["failure_count"],
                last_failure_at=datetime.fromisoformat(
                    c["last_failure_at"].replace("+00:00Z", "+00:00").replace("Z", "+00:00")
                ) if c["last_failure_at"] else None
            )
            for c in circuits
        ]
        return CircuitBreakerList(circuits=circuit_statuses)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch circuit states: {e}")

@router.post("/reliability/circuits/{service_name}/reset")
async def reset_circuit_breaker(service_name: str):
    """
    Resets the specified circuit breaker to CLOSED.
    """
    try:
        # Check if the service name is valid/exists in our circuits
        circuits = await ReliabilityManagerService.get_circuits()
        valid_names = {c["service_name"] for c in circuits}
        if service_name not in valid_names:
            raise HTTPException(status_code=404, detail=f"Circuit breaker '{service_name}' not found.")
            
        result = await ReliabilityManagerService.reset_circuit(service_name)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset circuit breaker: {e}")

@router.get("/performance/baselines", response_model=PerformanceBaselinesResponse)
async def get_performance_baselines():
    """
    Retrieves system latency target baseline levels.
    """
    try:
        baselines = PerformanceBenchmarkService.get_baselines()
        baseline_items = [
            PerformanceBaselineItem(
                endpoint=b["endpoint"],
                p50_latency_ms=b["p50_latency_ms"],
                p95_latency_ms=b["p95_latency_ms"],
                p99_latency_ms=b["p99_latency_ms"],
                max_concurrency=b["max_concurrency"]
            )
            for b in baselines
        ]
        return PerformanceBaselinesResponse(
            performance_baselines=baseline_items,
            last_updated_at=datetime.now(timezone.utc)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch performance baselines: {e}")
