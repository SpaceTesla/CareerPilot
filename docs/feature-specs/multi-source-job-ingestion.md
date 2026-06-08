# Feature Specification: Multi-Source Job Ingestion (F2.1)

## 1. Purpose
The `Multi-Source Job Ingestion` feature is responsible for scaling CareerPilot's job market data acquisition by integrating multiple external job boards and applicant tracking system (ATS) crawlers. It extends the initial [Job Market Data Foundation (F1.5)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md) to query APIs (JSearch, Adzuna) and scrape public job boards (Greenhouse, Lever) directly. This feature serves as the raw data feed for all downstream market intelligence services, including deduplication, NLP extraction, company intelligence, and ghost posting detection.

---

## 2. User Value
For CareerPilot users, job hunting is typically manual, episodic, and restricted to a few popular sites. This feature compiles an exhaustive, real-time repository of relevant job postings from across the web. 
By pulling from both direct developer job search APIs and ATS public boards (where startups and tech companies post roles before indexing on major aggregates), candidates get early access to high-fit roles. 
In the **Career Intelligence Compounding Loop** (detailed in [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md)), this data is the raw fuel. It represents the "Market" state that is continuously evaluated against the user's "Profile" state to calculate the Career Health Score and Position Delta.

---

## 3. Requirements
- **JSearch Ingestion**: Integrate JSearch API client to fetch listings using localized and specialized keyword search queries.
- **Adzuna Ingestion**: Integrate Adzuna API client for regional coverage, parsing salary benchmarks and job postings.
- **Greenhouse Board Crawler**: Build a crawler that takes target company Greenhouse board IDs and scrapes their list of open positions.
- **Lever Board Crawler**: Build a crawler that scrapes open positions directly from Lever job board endpoints for target companies.
- **Ingestion Scheduler**: Automate regular ingestion runs using Celery or Temporal schedules with configurable parameters per source.
- **Source Health Monitoring**: Continuously track API response codes, rates, failure counts, and latency, marking sources as degraded when errors spike.
- **Retry Policies**: Robust exponential backoff with jitter to handle network timeouts and temporary API unavailability.
- **Ingestion Observability**: Expose Prometheus metrics on raw jobs crawled, API token consumption, and rate limits.
- **Ingestion Dashboard API**: Endpoints to check current API token utilization, run status, and error logs.
- **Source Comparison Reports**: Internal analytical endpoints to compare the quantity, quality, and duplication rate of postings across JSearch, Adzuna, Greenhouse, and Lever.

---

## 4. Database Changes

This feature introduces tables to manage the source metadata, run audits, and stage raw ingested postings before deduplication.

### Schema Definitions

#### Table: `job_sources`
Tracks active ingestion sources, credentials/API keys reference, state, and rate limit tracking.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `name`: `VARCHAR(100)` (e.g., "JSearch", "Adzuna", "Greenhouse Crawler", "Lever Crawler")
- `source_key`: `VARCHAR(50)` (Unique, e.g., "jsearch", "adzuna", "greenhouse", "lever")
- `is_active`: `BOOLEAN` (default `true`)
- `rate_limit_limit`: `INTEGER` (Nullable)
- `rate_limit_remaining`: `INTEGER` (Nullable)
- `rate_limit_reset_at`: `TIMESTAMP WITH TIME ZONE` (Nullable)
- `error_count_24h`: `INTEGER` (default `0`)
- `last_run_status`: `VARCHAR(50)` (e.g., "SUCCESS", "FAILED", "DEGRADED")
- `last_run_at`: `TIMESTAMP WITH TIME ZONE` (Nullable)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)

#### Table: `job_ingestion_runs`
Audit trail of every scheduled and manual run.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `source_id`: `UUID` (FK referencing `job_sources.id`, ON DELETE CASCADE)
- `status`: `VARCHAR(50)` (e.g., "PENDING", "RUNNING", "COMPLETED", "FAILED")
- `items_scraped`: `INTEGER` (default `0`)
- `items_inserted`: `INTEGER` (default `0`)
- `items_failed`: `INTEGER` (default `0`)
- `error_log`: `TEXT` (Nullable)
- `started_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)
- `completed_at`: `TIMESTAMP WITH TIME ZONE` (Nullable)

#### Table: `raw_job_postings`
Staging area for incoming postings. Unmodified data is saved here before deduplication and skill extraction processes run.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `ingestion_run_id`: `UUID` (FK referencing `job_ingestion_runs.id`, ON DELETE CASCADE)
- `source_key`: `VARCHAR(50)` (Indexed)
- `external_id`: `VARCHAR(255)` (Unique ID from source, e.g., "jsearch_12345", Indexed with `source_key`)
- `title`: `VARCHAR(255)` (Raw title)
- `company_name`: `VARCHAR(255)` (Raw company name, Indexed)
- `description`: `TEXT` (Raw description)
- `location_raw`: `VARCHAR(255)`
- `url`: `TEXT`
- `salary_raw`: `JSONB` (Nullable)
- `raw_payload`: `JSONB`
- `created_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)

### Indexes & Migrations
- `idx_raw_jobs_source_ext`: Unique index on `(source_key, external_id)` to prevent inserting exact source duplicates in the raw layer.
- `idx_raw_jobs_company_title`: Composite index on `(company_name, title)` to accelerate pre-deduplication queries.
- **Alembic Migration**: `create_multi_source_ingestion_tables.py` containing operations to create `job_sources`, `job_ingestion_runs`, and `raw_job_postings` tables.

---

## 5. API Endpoints

All routes are versioned under `/api/v2`.

### `POST /api/v2/market/ingestion/trigger`
Triggers a manual ingestion run for a specific source.
- **Authentication**: Required (JWT, Scope: `admin`)
- **Request Payload**:
```json
{
  "source_key": "jsearch",
  "query": "Software Engineer",
  "location": "United States",
  "limit": 100
}
```
- **Response (202 Accepted)**:
```json
{
  "run_id": "8f8e1234-a56b-4c7d-8e9f-0123456789ab",
  "source_key": "jsearch",
  "status": "PENDING",
  "message": "Ingestion job queued successfully."
}
```
- **Status Codes**: `202` (Accepted), `400` (Bad Request), `401` (Unauthorized), `403` (Forbidden), `500` (Internal Server Error)

### `GET /api/v2/market/ingestion/runs/{run_id}`
Returns details of a specific ingestion run.
- **Authentication**: Required (JWT, Scope: `admin` or `operator`)
- **Response (200 OK)**:
```json
{
  "run_id": "8f8e1234-a56b-4c7d-8e9f-0123456789ab",
  "source_key": "jsearch",
  "status": "COMPLETED",
  "metrics": {
    "items_scraped": 100,
    "items_inserted": 95,
    "items_failed": 5
  },
  "error_log": null,
  "started_at": "2026-06-09T02:00:00Z",
  "completed_at": "2026-06-09T02:05:30Z"
}
```

### `GET /api/v2/market/ingestion/sources/health`
Lists health statistics of all configured sources.
- **Authentication**: Required (JWT, Scope: `admin` or `operator`)
- **Response (200 OK)**:
```json
{
  "sources": [
    {
      "source_key": "jsearch",
      "name": "JSearch API",
      "is_active": true,
      "status": "SUCCESS",
      "last_run_at": "2026-06-09T02:00:00Z",
      "error_rate_24h": 0.02,
      "rate_limits": {
        "limit": 10000,
        "remaining": 9250,
        "reset_at": "2026-06-10T00:00:00Z"
      }
    },
    {
      "source_key": "greenhouse",
      "name": "Greenhouse Crawler",
      "is_active": true,
      "status": "DEGRADED",
      "last_run_at": "2026-06-08T22:00:00Z",
      "error_rate_24h": 0.25,
      "rate_limits": null
    }
  ]
}
```

### `GET /api/v2/market/ingestion/reports/comparison`
Analytical comparison of different sources over a specified date range.
- **Authentication**: Required (JWT, Scope: `admin` or `operator`)
- **Query Parameters**:
  - `start_date`: ISO Timestamp (optional)
  - `end_date`: ISO Timestamp (optional)
- **Response (200 OK)**:
```json
{
  "comparison": [
    {
      "source_key": "jsearch",
      "total_ingested": 1420,
      "duplicate_rate": 0.12,
      "avg_latency_ms": 320.5
    },
    {
      "source_key": "greenhouse",
      "total_ingested": 450,
      "duplicate_rate": 0.01,
      "avg_latency_ms": 1105.2
    }
  ]
}
```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Any, Dict

class JobIngestionSource(BaseModel):
    id: UUID
    name: str
    source_key: str
    is_active: bool
    rate_limit_limit: Optional[int] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset_at: Optional[datetime] = None
    error_count_24h: int
    last_run_status: str
    last_run_at: Optional[datetime] = None

class JobIngestionRun(BaseModel):
    id: UUID
    source_id: UUID
    status: str
    items_scraped: int
    items_inserted: int
    items_failed: int
    error_log: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

class RawJobPosting(BaseModel):
    id: UUID
    ingestion_run_id: UUID
    source_key: str
    external_id: str
    title: str
    company_name: str
    description: str
    location_raw: str
    url: str
    salary_raw: Optional[Dict[str, Any]] = None
    raw_payload: Dict[str, Any]
    created_at: datetime
```

---

## 7. Services

### `JobIngestionService`
Orchestrates the ingestion lifecycle: starts runs, logs events, tracks health, and delegates requests to specific API clients.
- `trigger_run(source_key: str, query: str, location: str, limit: int) -> UUID`: Initializes a `JobIngestionRun` record, publishes an event, and starts an asynchronous task.
- `complete_run(run_id: UUID, items_scraped: int, items_inserted: int, items_failed: int, error_log: Optional[str] = None) -> None`: Updates the run status and records metrics.
- `update_source_limits(source_key: str, remaining: int, reset_at: datetime) -> None`: Updates rate limit metrics in `job_sources`.
- `record_source_error(source_key: str, error: str) -> None`: Increments error counter and evaluates if source status should degrade.

### `JSearchIngestionClient`
Encapsulates JSearch RapidAPI client logic.
- `fetch_jobs(query: str, location: str, page: int = 1) -> list[dict]`: Hits JSearch `/search` endpoint, returning raw structured lists. Handles API authentication and headers.

### `AdzunaIngestionClient`
Encapsulates Adzuna API client logic.
- `fetch_jobs(query: str, location: str, page: int = 1) -> list[dict]`: Hits Adzuna API, converting payload keys to unified formats.

### `GreenhouseCrawlerClient`
Public board crawler.
- `fetch_board_jobs(company_board_id: str) -> list[dict]`: Fetches Greenhouse API `/v1/boards/{board_id}/jobs` to grab job schema metadata and individual descriptions.

### `LeverCrawlerClient`
Public board crawler.
- `fetch_board_jobs(company_board_id: str) -> list[dict]`: Fetches Lever API `/v1/postings/{board_id}` for public listings.

---

## 8. Events

Ingestion status changes and individual raw jobs are published to the message broker.

### Event: `market.job_ingestion_run.started`
- **Producer**: `JobIngestionService`
- **Consumer**: `observability-service`, `notification-service`
- **Payload Schema**:
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "market.job_ingestion_run.started",
  "timestamp": "2026-06-09T02:00:00Z",
  "payload": {
    "run_id": "8f8e1234-a56b-4c7d-8e9f-0123456789ab",
    "source_key": "jsearch",
    "triggered_by": "scheduler"
  }
}
```

### Event: `market.job_ingestion_run.completed`
- **Producer**: `JobIngestionService`
- **Consumer**: `observability-service`, `dashboard-service`, `normalization-worker`
- **Payload Schema**:
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440001",
  "event_type": "market.job_ingestion_run.completed",
  "timestamp": "2026-06-09T02:05:30Z",
  "payload": {
    "run_id": "8f8e1234-a56b-4c7d-8e9f-0123456789ab",
    "source_key": "jsearch",
    "items_scraped": 100,
    "items_inserted": 95,
    "items_failed": 5
  }
}
```

### Event: `market.raw_job.ingested`
- **Producer**: `JobIngestionService`
- **Consumer**: `deduplication-service`
- **Payload Schema**:
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440002",
  "event_type": "market.raw_job.ingested",
  "timestamp": "2026-06-09T02:01:15Z",
  "payload": {
    "raw_job_id": "7ca6b8c9-d2e1-4c60-a2b1-5e7e8fa1b98f",
    "source_key": "jsearch",
    "external_id": "jsearch_12345",
    "company_name": "Acme Corp",
    "title": "Senior Staff Backend Engineer"
  }
}
```

---

## 9. Background Jobs
- **`scheduled_jsearch_ingestion_job`**: Run every 12 hours. Targets software engineering roles in major tech hubs.
- **`scheduled_adzuna_ingestion_job`**: Run every 12 hours. Normalizes regional tech salaries.
- **`scheduled_greenhouse_crawler_job`**: Daily cron executing Greenhouse crawls across a watch list of 100+ target startups and tech firms.
- **`scheduled_lever_crawler_job`**: Daily cron executing Lever crawls across a watch list of 100+ startups.
- **`ingestion_health_check_monitor`**: Hourly cron tracking health status. Degrades a source if `error_count_24h` exceeds a threshold of 10 failures.
- **Retry Logic**: Celery tasks use exponential backoff (`default_retry_delay=300`, `max_retries=3`, backoff factor of 2).

---

## 10. Acceptance Criteria

### Ingestion Execution Scenario
- **Given**: The JSearch API source is configured and active.
- **When**: The `scheduled_jsearch_ingestion_job` runs at its cron interval.
- **Then**: An entry is created in `job_ingestion_runs` with state `RUNNING`, the API is queried, retrieved jobs are saved to `raw_job_postings`, the run is updated to `COMPLETED`, and a `market.job_ingestion_run.completed` event is emitted.

### Health Degradation Scenario
- **Given**: The Greenhouse crawler starts experiencing repeated HTTP 403 blocks from target sites.
- **When**: 10 consecutive failures occur within a 2-hour window.
- **Then**: The Greenhouse entry in `job_sources` changes its `last_run_status` to `DEGRADED`, and a health degradation alert is pushed to the observability context.

---

## 11. Edge Cases
- **API Rate Limiting**: JSearch and Adzuna API limits can be consumed quickly. The ingestion worker must read response headers (`X-RateLimit-Remaining`) and pause ingestion if remaining tokens fall below 5%.
- **ATS URL Structural Changes**: Web crawler endpoints are subject to changes. If crawl schemas fail validation, the job must fail gracefully, alert operators, and preserve previously scraped raw descriptions.
- **Payload Bloat**: Descriptions can be massive or formatted in heavy HTML. Clean and strip HTML formatting in the client wrapper before storing it in PostgreSQL.
- **Duplicate Raw Entries**: If the source serves the same job ID in consecutive queries, the database unique constraint `idx_raw_jobs_source_ext` triggers a rollback. Use `ON CONFLICT DO NOTHING` in the INSERT statement to maintain throughput.

---

## 12. Test Requirements
- **Mocking Client APIs**: All integration tests must mock the external REST responses using tools like `pytest-responses` or `HTTPPretty`.
- **Schema Validation Testing**: Verify that malformed JSearch payloads with missing titles or links are redirected to `items_failed` counters.
- **Concurrency Testing**: Ensure that multiple concurrent ingestion workers targeting different sources do not cause deadlock locks on `raw_job_postings`.

---

## 13. Dependencies
- **Direct Blockers**:
  - [Job Market Data Foundation (F1.5)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
- **Downstream Beneficiaries**:
  - [Advanced Deduplication (F2.2)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/advanced-deduplication.md)
  - [NLP Skill Extraction (F2.3)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/nlp-skill-extraction.md)
  - [Company Intelligence (F2.4)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/company-intelligence.md)
  - [Ghost Posting Detection (F2.5)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/ghost-posting-detection.md)
  - [Compensation Intelligence (F2.6)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/compensation-intelligence.md)
