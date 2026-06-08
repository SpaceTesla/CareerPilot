# Feature Specification: Load & Performance Testing

## 1. Purpose
The Load & Performance Testing feature establishes the performance verification infrastructure for CareerPilot, using the Locust framework to run high-concurrency benchmarks. It measures the behavior, latency, and stability of API gateways, search databases, background queues, and workflow systems under simulated load.

This ensures that the platform can scale to handle sudden user growth, identify performance bottlenecks before production deployments, and catch code regressions that impact latency.

---

## 2. User Value
Directly supports the **Observability & Scale** context of the **Career Intelligence Compounding Loop**.
- **Compounding Loop Connection**: As the user base grows, high-concurrency reads on the Career Dashboard and Opportunity Matching systems must stay fast. Performance testing ensures that the vector databases (Qdrant) and matching engines can scale without lag, delivering fast, real-time matching metrics.
- **User Benefit**: Users experience a fast, responsive app, with dashboard widgets, recommendations, and search results loading instantly even during peak platform usage.

---

## 3. Requirements
- **Locust Framework Integration**: Set up Locust load testing scripts that simulate real-world user paths (e.g., logging in, browsing dashboard widgets, updating profiles).
- **Authentication Load Testing**: Benchmark JWT generation, verification, and token refresh endpoints under concurrent user login loads.
- **Career Profile API Benchmarks**: Measure database performance during concurrent CRUD operations on profile records.
- **Retrieval Pipeline Testing**: Test Qdrant and Postgres databases under high-concurrency hybrid search queries (vector + keyword search).
- **Workflow Load Testing**: Test Temporal task queues and workers by triggering thousands of concurrent dummy workflows to ensure the system handles backlogs correctly.
- **Dashboard API Aggregator Benchmarking**: Test the home dashboard aggregator under load to verify Redis cache hit rates and database fallback performance.
- **Automated Performance Reports**: Generate performance reports (including average latency, p95/p99 latency, and error rates) after each run.
- **Performance Regression Gates**: Set up performance budget gates in the CI pipeline to fail builds if API latency increases by more than 10%.

---

## 4. Database Changes
No database schema changes are required for production. However, load testing requires database seeding scripts to populate test databases with realistic data volumes.

### DB Seed Target Baselines (Test Environment Only)
- Seeding **10,000** mock user profiles, complete with skills, educations, and experience rows.
- Seeding **100,000** mock job postings.
- Seeding **50,000** historical application outcomes.

---

## 5. API Endpoints
Admin endpoints allow developers to query baseline targets.

### Get Performance Baselines
- **HTTP Method**: `GET`
- **Route**: `/api/v2/admin/performance/baselines`
- **Response Payload (JSON)**:
```json
{
  "performance_baselines": [
    {
      "endpoint": "GET /api/v2/dashboard",
      "p50_latency_ms": 45,
      "p95_latency_ms": 110,
      "p99_latency_ms": 220,
      "max_concurrency": 500
    },
    {
      "endpoint": "GET /api/v2/opportunities/match",
      "p50_latency_ms": 80,
      "p95_latency_ms": 180,
      "p99_latency_ms": 350,
      "max_concurrency": 200
    }
  ],
  "last_updated_at": "2026-06-09T02:04:18Z"
}
```
- **HTTP Status Codes**:
  - `200 OK`: Baselines returned.
  - `401 Unauthorized`: Invalid credentials.
  - `403 Forbidden`: Admin privileges required.

---

## 6. Domain Models

```python
from pydantic import BaseModel
from typing import List
from datetime import datetime

class PerformanceBaselineItem(BaseModel):
    endpoint: str
    p50_latency_ms: int
    p95_latency_ms: int
    p99_latency_ms: int
    max_concurrency: int

class PerformanceBaselinesResponse(BaseModel):
    performance_baselines: List[PerformanceBaselineItem]
    last_updated_at: datetime
```

---

## 7. Services

### Class: `PerformanceBenchmarkService`
Verifies system latency metrics against defined baselines and evaluates CI pipeline gates.

- **Method**: `evaluate_run_metrics`
  - **Inputs**:
    - `run_id` (str): Unique performance run identifier.
    - `stats_json_path` (str): File path containing the Locust run statistics.
  - **Return Type**: `bool` (indicating if performance gate passed)
  - **Responsibilities**:
    - Parses the JSON metrics file output by the Locust run.
    - Compares each endpoint's p95 latency and error rate against the stored baselines.
    - Returns `True` if all metrics are within 10% of baselines and error rates are under 0.1%.
    - Returns `False` if any endpoint exceeds the performance budget, outputting failure details to the console log.

---

## 8. Events
The performance test run completes by publishing a summary event, which is picked up by notification services to alert developers of the run results.

### Event: `performance.run_completed`
- **Producer**: `PerformanceBenchmarkService`
- **Consumer**: `observability-service`
- **Payload Schema**:
```json
{
  "event_id": "evt_perf_run_001",
  "event_type": "performance.run_completed",
  "timestamp": "2026-06-09T02:05:00Z",
  "payload": {
    "run_id": "locust-run-20260609",
    "concurrency_users": 1000,
    "total_requests": 45000,
    "error_rate": 0.0005,
    "gate_passed": true
  }
}
```

---

## 9. Background Jobs
No periodic background crons. Performance runs are triggered on-demand via CI/CD deployment pipelines or by administrators during testing cycles.

---

## 10. Acceptance Criteria
- **Scenario**: Automated performance gate execution.
  - **Given**: A test DB is seeded with baseline data volumes.
  - **When**: The Locust test suite runs in the CI/CD pipeline.
  - **Then**: All API endpoints maintain p95 latencies under 250ms with zero request errors, and the performance gate returns a passing status.
- **Scenario**: Performance regression detected.
  - **Given**: A code change introduces an un-indexed SQL query on the profile endpoint.
  - **When**: The Locust profile tests execute.
  - **Then**: The p95 response time jumps to 850ms, the performance gate returns a failing status, and the build pipeline halts.

---

## 11. Edge Cases
- **Database Connection Pools Exhausted**: High concurrency testing exhausts the Postgres connection pool, causing connection timeouts rather than endpoint slowness.
  - **Resolution**: Configure connection pool limits specifically for testing environments (e.g. max 100 connections) and configure database clients to return clean pool-exhausted errors for easier identification.
- **Locust Runner Resource Bottlenecks**: The Locust runner instance runs out of CPU, throttling requests and skewing latency metrics.
  - **Resolution**: Monitor the Locust runner CPU load during testing. Use Locust's distributed mode (one coordinator, multiple workers) to distribute the load generation across multiple system instances.

---

## 12. Test Requirements
- **Unit Tests**: Test the performance stats parser to verify it calculates budget deltas and flags failures correctly.
- **Integration Tests**: Execute a mini load test run (5 concurrent users for 30 seconds) in the test environment to verify end-to-end telemetry pipeline stability.

---

## 13. Dependencies
- **[F6.2: Metrics & Monitoring](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/metrics-monitoring.md)**: Used to monitor database CPU and system metrics during load testing runs.

---
