from __future__ import annotations

import os
import tempfile
import json
import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4

from app.main import app
from app.services.observability_telemetry_service import ObservabilityTelemetryService
from app.services.metrics_collection_service import MetricsCollectionService
from app.services.reliability_manager_service import ReliabilityManagerService, CircuitOpenException
from app.services.performance_benchmark_service import PerformanceBenchmarkService
from app.services.documentation_service import DocumentationService

@pytest.mark.asyncio
async def test_telemetry_status_endpoint():
    """
    Test GET /api/v2/admin/telemetry/status returns the correct telemetry status payload.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v2/admin/telemetry/status")
        assert resp.status_code == 200
        payload = resp.json()
        assert "collector_status" in payload
        assert "exporter_type" in payload
        assert "active_instrumentations" in payload
        assert isinstance(payload["active_instrumentations"], list)

@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint():
    """
    Test GET /metrics returns the Prometheus-formatted text metrics.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Record a dummy request
        MetricsCollectionService.record_api_request("GET", "/api/v2/health", 200, 0.05)
        
        # Scrape metrics
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        assert "careerpilot_api_requests_total" in resp.text
        assert "careerpilot_api_request_duration_seconds" in resp.text

@pytest.mark.asyncio
async def test_reliability_circuits_and_breaker():
    """
    Test reliability manager circuit breaker state transitions, auto-opening, and manual reset.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Fetch circuit lists
        resp = await client.get("/api/v2/admin/reliability/circuits")
        assert resp.status_code == 200
        payload = resp.json()
        assert "circuits" in payload
        
        service_name = "jsearch-api-connector"
        
        # Reset the circuit breaker state to begin with a clean test
        await ReliabilityManagerService.reset_circuit(service_name)
        
        # Define a failing network call function
        def failing_network_call():
            raise ValueError("Upstream JSearch connection timeout")
            
        # Execute protected calls up to failure threshold (5)
        for _ in range(5):
            try:
                await ReliabilityManagerService.execute_with_breaker(service_name, failing_network_call)
            except ValueError:
                pass
                
        # 6th execution should fail immediately with CircuitOpenException (circuit breaker is OPEN)
        with pytest.raises(CircuitOpenException):
            await ReliabilityManagerService.execute_with_breaker(service_name, failing_network_call)
            
        # Verify state transitioned to OPEN in Redis/endpoint status
        resp = await client.get("/api/v2/admin/reliability/circuits")
        circuits = resp.json()["circuits"]
        target = next(c for c in circuits if c["service_name"] == service_name)
        assert target["state"] == "OPEN"
        assert target["failure_count"] >= 5
        
        # Reset circuit state using reset POST endpoint
        reset_resp = await client.post(f"/api/v2/admin/reliability/circuits/{service_name}/reset")
        assert reset_resp.status_code == 200
        assert reset_resp.json()["state"] == "CLOSED"

@pytest.mark.asyncio
async def test_performance_baselines_and_gate():
    """
    Test performance baseline query endpoints and benchmark regression evaluation logic.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Fetch baselines list
        resp = await client.get("/api/v2/admin/performance/baselines")
        assert resp.status_code == 200
        payload = resp.json()
        assert "performance_baselines" in payload
        assert "last_updated_at" in payload
        
        # 2. Write mock Locust report to check performance gate
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp:
            json.dump([
                {
                    "name": "/api/v2/dashboard",
                    "method": "GET",
                    "num_requests": 150,
                    "num_failures": 0,
                    "p95": 90.0  # Under the 110ms + 10% budget limit
                }
            ], tmp)
            tmp_path = tmp.name
            
        try:
            gate_passed = await PerformanceBenchmarkService.evaluate_run_metrics("test-locust-run", tmp_path)
            assert gate_passed is True
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

@pytest.mark.asyncio
async def test_documentation_adrs_endpoint():
    """
    Test GET /api/v2/docs/adrs returns parsed metadata for ADR markdown files.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v2/docs/adrs")
        assert resp.status_code == 200
        payload = resp.json()
        assert "adrs" in payload
        # Verify that we parsed the existing docs/adrs files
        if len(payload["adrs"]) > 0:
            adr = payload["adrs"][0]
            assert "id" in adr
            assert "title" in adr
            assert "status" in adr
            assert "summary" in adr

@pytest.mark.asyncio
async def test_openapi_specification_endpoint():
    """
    Test GET /api/v2/docs/openapi.json generates dynamic API contracts successfully.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v2/docs/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        assert "openapi" in spec
        assert "paths" in spec
        assert "/api/v2/docs/openapi.json" in spec["paths"]
