# Feature Specification: Reliability Engineering

## 1. Purpose
The Reliability Engineering feature adds resilience patterns across the CareerPilot platform. It defines technical Service Level Objectives (SLOs), enforces error budgets, and implements circuit breakers, API rate limits, and graceful degradation paths (e.g., falling back to PostgreSQL full-text search if the Qdrant vector database goes offline).

This guarantees that the platform remains stable under load, prevents cascading system failures, and controls third-party API costs during peak usage.

---

## 2. User Value
Directly operates on the **System Reliability** layer of the **Career Intelligence Compounding Loop**.
- **Compounding Loop Connection**: If an external LLM API or job board endpoint experiences an outage during an application run, the system must degrade gracefully. Rather than crashing, the platform uses fallback models or queues the action in Temporal, preserving the execution state and protecting the compounding outcome records.
- **User Benefit**: Users enjoy a stable platform that handles system issues automatically, ensuring their active applications proceed even during partial network outages.

---

## 3. Requirements
- **Define Service SLOs**: Set targets: API availability > 99.9%, p95 API response times < 200ms, and successful application submissions > 95%.
- **Implement Circuit Breakers**: Use circuit breakers (via Redis-backed state) on third-party APIs (e.g., OpenAI, Greenhouse, JSearch) to prevent system delay cascades when external systems crash.
- **Rate Limiting Middleware**: Implement a Redis token-bucket rate limiter to prevent API abuse and manage usage spikes.
- **Graceful Degradation Paths**: If the vector database is unavailable, fall back to PostgreSQL full-text search. If the primary LLM is unavailable, route requests to a secondary LLM provider.
- **Chaos Test Scenarios**: Create test scripts to simulate database failures, network packet loss, and worker process crashes.
- **Reliability Dashboards**: Build Grafana dashboards displaying SLO status, error budget burn rates, and circuit breaker states.
- **Incident Runbooks**: Document operational guides for system recoveries, database lockouts, and API credentials updates.

---

## 4. Database Changes
No PostgreSQL database changes are required, as circuit breaker states and rate limits are managed in Redis for low latency.

### Redis Cache Structure
- `rate_limit:{user_id}:{route_path}`: Token-bucket count with TTL.
- `circuit_breaker:{service_name}:state`: Stores state (`CLOSED`, `OPEN`, `HALF_OPEN`).
- `circuit_breaker:{service_name}:failure_count`: Counter with TTL.

---

## 5. API Endpoints

### Get Circuit Breaker States
- **HTTP Method**: `GET`
- **Route**: `/api/v2/admin/reliability/circuits`
- **Response Payload (JSON)**:
```json
{
  "circuits": [
    {
      "service_name": "openai-api-connector",
      "state": "CLOSED",
      "failure_count": 0,
      "last_failure_at": null
    },
    {
      "service_name": "greenhouse-board-connector",
      "state": "OPEN",
      "failure_count": 5,
      "last_failure_at": "2026-06-09T02:02:15Z"
    }
  ]
}
```
- **HTTP Status Codes**:
  - `200 OK`: Successful retrieval.
  - `401 Unauthorized`: Invalid credentials.
  - `403 Forbidden`: Admin privileges required.

### Reset Circuit Breaker State
- **HTTP Method**: `POST`
- **Route**: `/api/v2/admin/reliability/circuits/{service_name}/reset`
- **Path Parameters**:
  - `service_name` (string): The name of the target circuit breaker.
- **Response Payload (JSON)**:
```json
{
  "service_name": "greenhouse-board-connector",
  "state": "CLOSED",
  "message": "Circuit breaker reset successfully."
}
```
- **HTTP Status Codes**:
  - `200 OK`: Circuit reset.
  - `401 Unauthorized`: Invalid credentials.
  - `404 Not Found`: Circuit breaker name not found.

---

## 6. Domain Models

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CircuitBreakerStatus(BaseModel):
    service_name: str
    state: str
    failure_count: int
    last_failure_at: Optional[datetime] = None

class CircuitBreakerList(BaseModel):
    circuits: List[CircuitBreakerStatus]
```

---

## 7. Services

### Class: `ReliabilityManagerService`
Provides circuit breaker wrappers, handles rate limits, and coordinates fallback execution paths.

- **Method**: `execute_with_breaker`
  - **Inputs**:
    - `service_name` (str): Unique key for target service.
    - `func` (Callable): The function containing the network call.
    - `fallback_func` (Optional[Callable]): Fallback to execute if circuit is open.
  - **Return Type**: `Any`
  - **Responsibilities**:
    - Checks Redis to verify if the circuit breaker for `service_name` is `OPEN`. If open, runs the `fallback_func` immediately or raises a `CircuitOpenException`.
    - If `CLOSED` or `HALF_OPEN`, executes `func`.
    - If execution fails with network errors, increments the failure count in Redis. Once failures exceed threshold (e.g., 5 in 1 minute), transitions state to `OPEN` and updates last failure timestamp.
    - If execution succeeds, resets failure count.

- **Method**: `check_rate_limit`
  - **Inputs**:
    - `user_id` (str): Requester's ID.
    - `route` (str): Targeted endpoint route.
    - `limit` (int): Max requests allowed.
    - `window_seconds` (int): Time period.
  - **Return Type**: `bool` (indicating if request is allowed)
  - **Responsibilities**:
    - Increments the request count in Redis for the window.
    - Returns `True` if under limit, or `False` if rate limit is exceeded.

---

## 8. Events
The reliability layer publishes events when circuit states transition to warn engineering teams of upstream dependencies failing.

### Event: `circuit.opened`
- **Producer**: `ReliabilityManagerService`
- **Consumer**: `observability-service`
- **Payload Schema**:
```json
{
  "event_id": "evt_circ_opn_001",
  "event_type": "circuit.opened",
  "timestamp": "2026-06-09T02:02:15Z",
  "payload": {
    "service_name": "greenhouse-board-connector",
    "failure_count": 5,
    "last_error": "Connection timed out after 10000ms"
  }
}
```

---

## 9. Background Jobs
- **Circuit Breaker Half-Open Controller**: A lightweight Celery background job running every 60 seconds. It changes `OPEN` circuit breakers to `HALF_OPEN` to test if upstream connections have recovered.

---

## 10. Acceptance Criteria
- **Scenario**: Third-party API fails repeatedly.
  - **Given**: The OpenAI API experiences an outage and fails.
  - **When**: The system executes requests and fails 5 times sequentially.
  - **Then**: The system opens the circuit breaker, returns immediate fallback responses, and fires a `circuit.opened` event.
- **Scenario**: Qdrant vector database goes offline.
  - **Given**: Qdrant is unreachable.
  - **When**: A profile matching search is run.
  - **Then**: The system detects the failure, switches search routing to PostgreSQL full-text search, and runs the query successfully.

---

## 11. Edge Cases
- **Circuit Breaker State Desynchronization**: Redis restarts and loses the circuit breaker states.
  - **Resolution**: Circuit breakers default to `CLOSED` when state data is missing, and the system begins count calculations fresh.
- **Rate Limiter Thundering Herd**: Millions of requests hit the rate limiter simultaneously, creating database locking issues.
  - **Resolution**: The rate limiter uses atomic Lua scripts in Redis to execute read-and-increment operations in a single thread-safe database roundtrip.

---

## 12. Test Requirements
- **Unit Tests**: Test the rate-limiter logic and validation checks.
- **Integration Tests**: Mock client connections to external services, verify that circuit breakers open on error rates, and check that fallback paths run successfully.

---

## 13. Dependencies
- **[F6.2: Metrics & Monitoring](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/metrics-monitoring.md)**: Feeds error rate statistics to monitoring dashboards.

---
