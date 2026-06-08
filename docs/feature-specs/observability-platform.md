# Feature Specification: Observability Platform

## 1. Purpose
The Observability Platform feature sets up distributed tracing across all services in CareerPilot using OpenTelemetry (OTel). It captures trace context across FastAPI routers, Celery background workers, Temporal workflows, and LangGraph agent execution.

This allows engineers to track the execution path of a user action (e.g., generating a Career Health Score or executing a browser-fallback application) and identify bottlenecks, database latency spikes, and external API rate limit issues in a single unified trace view.

---

## 2. User Value
Directly supports the **Observability** context of the **Career Intelligence Compounding Loop**.
- **Compounding Loop Connection**: When a user's Career Health Score calculation is delayed, the system must trace the exact cause (e.g., a slow Qdrant vector retrieval or a blocked LLM API request). OpenTelemetry logs trace IDs alongside telemetry, enabling developers to debug performance regressions instantly.
- **User Benefit**: Users experience a high-performance application with low latency, fast dashboard loading times, and rapid error resolution, as developers have immediate access to transaction trace logs.

---

## 3. Requirements
- **OpenTelemetry Tracing Integration**: Configure OTel SDK to export spans in OTLP format to an OpenTelemetry collector (backed by Jaeger or Honeycomb).
- **FastAPI Instrumentation**: Automatically instrument all FastAPI routes using `FastAPIInstrumentor` to capture HTTP method, route, request/response size, status code, and latency.
- **Celery Worker Instrumentation**: Hook into Celery worker lifecycle events (task-prerun, task-postrun) to propagate trace context across message queues.
- **Temporal Workflow Instrumentation**: Configure Temporal interceptors to record workflow spans, activity durations, and exceptions.
- **Agent Execution Tracing**: Wrap LangGraph node transitions and LLM API calls with custom OTel spans to measure agent thinking time vs. tool execution time.
- **Trace Dashboards**: Establish dashboard layouts in Jaeger/Grafana showcasing system path mappings and slow spans.
- **Distributed Tracing Tests**: Assert that trace headers (e.g., `traceparent`) propagate correctly between API, Workers, and Workflows.
- **Observability Health Checks**: Expose status endpoints showing OTel collector connection health.

---

## 4. Database Changes
No database schema changes are required for telemetry, as tracing spans are emitted out-of-process to the OpenTelemetry Collector.

---

## 5. API Endpoints
These endpoints exist to verify telemetry pipeline status and export collector health.

### Get Telemetry System Status
- **HTTP Method**: `GET`
- **Route**: `/api/v2/admin/telemetry/status`
- **Response Payload (JSON)**:
```json
{
  "collector_status": "CONNECTED",
  "exporter_type": "OTLP_HTTP",
  "active_instrumentations": [
    "fastapi",
    "sqlalchemy",
    "celery",
    "temporal"
  ],
  "traces_sent_count": 142908,
  "last_export_timestamp": "2026-06-09T02:04:18Z"
}
```
- **HTTP Status Codes**:
  - `200 OK`: Telemetry system is operational.
  - `401 Unauthorized`: Invalid credentials.
  - `403 Forbidden`: Admin privileges required.

---

## 6. Domain Models

```python
from pydantic import BaseModel
from typing import List
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
```

---

## 7. Services

### Class: `ObservabilityTelemetryService`
Bootstraps OpenTelemetry, sets up tracer providers, registers instrumentation modules, and manages dynamic span creation.

- **Method**: `initialize_telemetry`
  - **Inputs**:
    - `service_name` (str): Name of the running service (e.g., `careerpilot-api`).
    - `collector_url` (str): OTLP collector destination URL.
  - **Return Type**: `None`
  - **Responsibilities**:
    - Initializes the global TracerProvider and MeterProvider.
    - Sets up batch processors and OTLP exporters.
    - Configures W3C Trace Context propagation.
    - Instruments standard libraries (SQLAlchemy, requests, httpx).

- **Method**: `start_span`
  - **Inputs**:
    - `span_name` (str): Descriptive name for the span.
    - `parent_context` (Optional[Any]): Current parent trace context.
  - **Return Type**: `SpanContext`
  - **Responsibilities**:
    - Starts and returns a new span.
    - Inject tracing tags (e.g., `user_id`, `org_id` where applicable).

---

## 8. Events
Observability services subscribe to all workflow and system event queues via interceptors to correlate message queues with span traces. No custom domain events are published by the observability service itself.

---

## 9. Background Jobs
No periodic background crons. Traces are batched and exported asynchronously in the background by the OpenTelemetry SDK thread pool.

---

## 10. Acceptance Criteria
- **Scenario**: FastAPI request triggers background task.
  - **Given**: OpenTelemetry is initialized on API and Worker.
  - **When**: A request is made to `/api/v2/profile/sync` which schedules a Celery task.
  - **Then**: A single Trace ID spans from the initial FastAPI HTTP request, through Celery message broker, into the Worker task execution, and down to SQL query executions.
- **Scenario**: Telemetry Collector goes offline.
  - **Given**: Jaeger is shut down.
  - **When**: FastAPI handles requests.
  - **Then**: The system degrades gracefully; trace exports timeout silently in the background without affecting API response times or raising user-facing errors.

---

## 11. Edge Cases
- **Trace Loop Inflation**: Large loops in LangGraph agent execution generate thousands of trace spans, exceeding token limits or storage boundaries on Jaeger/Honeycomb.
  - **Resolution**: Implement trace sampling policies. Set sampling rates to 100% for errors and failures, but only 5% for successful agent runs.
- **PII Leakage in Telemetry**: Resumes, emails, or personal details get written to span tags (e.g., `db.statement` or HTTP request body tag).
  - **Resolution**: Implement OTel processors that filter out and redact fields containing emails, phone numbers, or key names before sending data to the OTLP collector.

---

## 12. Test Requirements
- **Unit Tests**: Verify that the trace context extractor correctly parses OTel headers from incoming request payloads.
- **Integration Tests**: Execute API routes under mock tests and assert that `opentelemetry.trace.get_current_span()` returns active span contexts.

---

## 13. Dependencies
- **[F1.1: Project Setup & Architecture](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/project-setup-architecture.md)**: Configures FastAPI skeletal framework.
- **[F3.1: LangGraph Foundation](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/langgraph-foundation.md)**: Tracing agent state transitions.
- **[F4.1: Temporal Infrastructure](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/temporal-infrastructure.md)**: Tracing background activity flows.

---
