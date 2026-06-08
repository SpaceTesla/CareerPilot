# Feature Specification: Metrics & Monitoring

## 1. Purpose
The Metrics & Monitoring feature establishes the observability layer for CareerPilot, using Prometheus to collect metrics and Grafana to display real-time dashboards. This includes business metrics (e.g., application conversion rates, health score trends) and system metrics (e.g., API latency, queue depth, workflow retry rates).

This ensures that the engineering and product teams can monitor system health, detect performance regressions, and identify delivery issues (like broken ATS forms or API rate limiting) immediately.

---

## 2. User Value
Directly operates on the **Observability** context of the **Career Intelligence Compounding Loop**.
- **Compounding Loop Connection**: Monitoring the volume and success of application submissions allows the system to flag when a specific ATS portal (e.g., Workday) changes its form layout. The resulting alert prompts developers to update form schemas, preventing other users from experiencing failed applications.
- **User Benefit**: Users get a reliable platform where system problems are caught and resolved before they impact active job applications.

---

## 3. Requirements
- **Prometheus Scrape Configuration**: Set up a Prometheus server to scrape `/metrics` endpoints across all service instances every 15 seconds.
- **Grafana Integration**: Provision a Grafana server connected to Prometheus, with dashboard layouts stored as code.
- **FastAPI HTTP Metrics**: Capture request rate, duration histogram, and error rate (RED metrics).
- **Temporal & Celery System Metrics**: Export queue lengths, task durations, and worker concurrency rates.
- **Business Performance Metrics**: Collect custom application metrics (e.g., total submissions, success rates by ATS provider, average days to response).
- **Health Score Trend Tracking**: Record aggregates of user Career Health Scores to track overall platform intelligence quality.
- **Alert Policies**: Set up alert rules for API error spikes, worker backlogs, and database connection pools.
- **Monitoring documentation**: Detail alert routing paths (PagerDuty, Slack, Email) and system metric definitions.

---

## 4. Database Changes
No database schema changes are required. Metrics are stored in the memory buffers of individual service instances and scraped by Prometheus to be written to its time-series database.

---

## 5. API Endpoints

### Prometheus Metrics Scrape Endpoint
- **HTTP Method**: `GET`
- **Route**: `/metrics`
- **Response Headers**:
  - `Content-Type: text/plain; version=0.0.4`
- **Response Body**: Prometheus-formatted text metrics.
- **Example Payload**:
```text
# HELP careerpilot_api_requests_total Total number of HTTP requests.
# TYPE careerpilot_api_requests_total counter
careerpilot_api_requests_total{method="POST",route="/api/v2/applications/workflows/trigger",status="202"} 1420
# HELP careerpilot_application_submissions_total Total applications processed.
# TYPE careerpilot_application_submissions_total counter
careerpilot_application_submissions_total{ats_type="GREENHOUSE",status="SUCCESS"} 870
careerpilot_application_submissions_total{ats_type="WORKDAY",status="FAILED"} 30
# HELP careerpilot_avg_health_score Average Career Health Score across active users.
# TYPE careerpilot_avg_health_score gauge
careerpilot_avg_health_score 74.2
```
- **HTTP Status Codes**:
  - `200 OK`: Metrics returned.

---

## 6. Domain Models
No internal domain models are required for metrics. Python classes use the `prometheus_client` SDK to define metrics objects.

```python
from prometheus_client import Counter, Histogram, Gauge

# System Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "careerpilot_api_requests_total",
    "Total HTTP requests handled",
    ["method", "route", "status"]
)

HTTP_REQUEST_DURATION = Histogram(
    "careerpilot_api_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route"]
)

# Business Metrics
APPLICATION_SUBMISSIONS = Counter(
    "careerpilot_application_submissions_total",
    "Total applications submitted",
    ["ats_type", "status"]
)

AVERAGE_HEALTH_SCORE = Gauge(
    "careerpilot_avg_health_score",
    "Average Career Health Score across users"
)
```

---

## 7. Services

### Class: `MetricsCollectionService`
A utility class to record system events and map them to Prometheus metric counters.

- **Method**: `record_api_request`
  - **Inputs**:
    - `method` (str): HTTP method.
    - `route` (str): API route path.
    - `status` (int): HTTP response code.
    - `duration` (float): Request duration in seconds.
  - **Return Type**: `None`
  - **Responsibilities**:
    - Increments `HTTP_REQUESTS_TOTAL` counter.
    - Adds duration to `HTTP_REQUEST_DURATION` histogram.

- **Method**: `record_application_submission`
  - **Inputs**:
    - `ats_type` (str): e.g., `GREENHOUSE`, `WORKDAY`.
    - `status` (str): e.g., `SUCCESS`, `FAILED`.
  - **Return Type**: `None`
  - **Responsibilities**:
    - Increments `APPLICATION_SUBMISSIONS` counter.

---

## 8. Events
The metrics service acts as a consumer of system events (e.g., `application.submitted`, `application.failed`) to increment Prometheus gauges and counters asynchronously.

---

## 9. Background Jobs
- **Platform Aggregations Collector**: A lightweight Celery background job running every 10 minutes to compute macro-level platform stats (like `careerpilot_avg_health_score`) and update Prometheus gauge values.

---

## 10. Acceptance Criteria
- **Scenario**: FastAPI endpoint receives requests.
  - **Given**: The `/metrics` endpoint is configured.
  - **When**: Requests are made to the API.
  - **Then**: Prometheus counter metrics are incremented and scraped by the Prometheus server.
- **Scenario**: Application submission fails.
  - **Given**: Application workflow throws an execution exception.
  - **When**: The failure handler executes.
  - **Then**: The counter `careerpilot_application_submissions_total{status="FAILED"}` is incremented.

---

## 11. Edge Cases
- **Metric Label Cardinality Explosion**: Creating labels on dynamic parameters (such as `user_id` or `job_id`) creates millions of unique timeseries, overwhelming Prometheus memory.
  - **Resolution**: Use static labels (e.g. `ats_type`, `http_status`, `route`). Never use unique transaction identifiers as metric labels.
- **Scrape Path Latency**: Calculating metrics on-the-fly during the `/metrics` request delays scraper runs.
  - **Resolution**: Calculate heavy database metrics (like average health scores) in background Celery tasks, storing the result in a fast Redis cache read by the `/metrics` route.

---

## 12. Test Requirements
- **Unit Tests**: Test that the `MetricsCollectionService` records and increments values without crashing.
- **Integration Tests**: Hit API endpoints, scrape `/metrics` directly, and verify that request count counters match execution counts.

---

## 13. Dependencies
- **[F6.1: Observability Platform](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/observability-platform.md)**: OpenTelemetry handles trace correlation for metrics.

---
