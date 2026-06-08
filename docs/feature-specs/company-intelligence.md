# Feature Specification: Company Intelligence (F2.4)

## 1. Purpose
The `Company Intelligence` feature aggregates raw postings data to profile hiring entities in the tech sector. By measuring active listings, duration of open jobs, and hiring frequency, this feature computes hiring velocity and growth trends. It supports user watchlists, scores employer attractiveness, and outputs structured company profile reports.

---

## 2. User Value
Software engineers want to join growing, high-leverage organizations and avoid companies experiencing stagnation or unannounced hiring freezes. 
Company Intelligence surfaces growth signals (e.g., "This company increased backend postings by 40% this month") that are otherwise hidden. 
In the **Career Intelligence Compounding Loop** (from [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md)), this data powers the [Opportunity Intelligence (F2.7)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md) engine, allowing the system to recommend jobs based on the company's organizational health, trajectory, and compensation standards, rather than simple role descriptions.

---

## 3. Requirements
- **Company Profile Aggregation**: Automatically extract company data from job postings, merge spelling variations, and associate corporate metadata (industry, size, funding).
- **Hiring Velocity Calculations**: Calculate the average number of new jobs posted weekly over 30, 90, and 180-day windows.
- **Hiring Trend Calculations**: Determine trend direction (e.g., "EXPANDING", "STABLE", "CONTRACTING") by comparing rolling averages of active postings.
- **Company Attractiveness Scoring Engine**: Compute an aggregate "Attractiveness Score" (0-100) using weights: hiring velocity growth (40%), average compensation level (40%), and employee retention indicators/size stability (20%).
- **Company Watchlist**: Enable users to follow target companies and receive alerts (via webhook/email) when new positions open or when hiring velocities change.
- **Company Report Generator**: Render structured data summaries containing active jobs, top skills sought, compensation range, and hiring velocity trends.
- **Caching Layer**: Cache aggregated company records in Redis to support sub-50ms API response times.
- **Observability and Monitoring**: Monitor aggregate metrics, company database health, and API latency.

---

## 4. Database Changes

Extends base tables to support tracking historical trends and watchlists.

### Schema Definitions

#### Table: `companies` (Extended)
Enhance the original table with aggregate signal fields:
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `name`: `VARCHAR(255)` (Unique, Indexed)
- `website`: `VARCHAR(255)` (Nullable)
- `industry`: `VARCHAR(100)` (Nullable)
- `size_range`: `VARCHAR(50)` (e.g. "11-50", "501-1000", "10000+")
- `hiring_velocity_30d`: `DECIMAL(6, 2)` (Jobs posted per month, default `0.00`)
- `hiring_velocity_90d`: `DECIMAL(6, 2)` (default `0.00`)
- `trend_direction`: `VARCHAR(50)` (e.g., "ACCELERATING", "STABLE", "DECELERATING")
- `attractiveness_score`: `DECIMAL(5, 2)` (Score between 0.00 and 100.00)
- `last_aggregated_at`: `TIMESTAMP WITH TIME ZONE` (Nullable)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)

#### Table: `company_watchlist`
Allows users to subscribe to specific updates.
- `user_id`: `UUID` (FK referencing `users.id`, ON DELETE CASCADE)
- `company_id`: `UUID` (FK referencing `companies.id`, ON DELETE CASCADE)
- `notifications_enabled`: `BOOLEAN` (default `true`)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)
- Primary Key is composite: `(user_id, company_id)`

#### Table: `company_snapshots`
Logs weekly company snapshots to generate trend graphs.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `company_id`: `UUID` (FK referencing `companies.id`, ON DELETE CASCADE)
- `active_postings_count`: `INTEGER` (default `0`)
- `hiring_velocity`: `DECIMAL(6, 2)`
- `attractiveness_score`: `DECIMAL(5, 2)`
- `snapshot_date`: `DATE` (Indexed with `company_id`)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)

### Indexes & Migrations
- `idx_company_watchlist_user`: B-Tree index on `user_id` inside `company_watchlist`.
- `idx_company_snapshots_lookup`: Composite index on `(company_id, snapshot_date)` to speed up trend graph queries.
- `idx_companies_score_lookup`: B-Tree index on `attractiveness_score` to query highest rated companies.
- **Alembic Migration**: `add_company_intelligence_tables.py` creating the tables and schema modifications.

---

## 5. API Endpoints

### `GET /api/v2/market/companies/{id}`
Returns a company's profile, hiring velocity indicators, and active job openings count.
- **Authentication**: Required (JWT, Scope: `user`)
- **Path Parameters**:
  - `id`: `UUID` (Company ID)
- **Response (200 OK)**:
```json
{
  "id": "e2f3a4b5-6c7d-8e9f-0123-456789abcdef",
  "name": "Stripe",
  "website": "https://stripe.com",
  "industry": "Fintech",
  "size_range": "1000-5000",
  "metrics": {
    "active_postings_count": 87,
    "hiring_velocity_30d": 24.5,
    "hiring_velocity_90d": 18.2,
    "trend_direction": "ACCELERATING",
    "attractiveness_score": 92.4,
    "last_updated": "2026-06-09T01:00:00Z"
  },
  "top_skills_sought": [
    { "name": "Python", "frequency": 0.65 },
    { "name": "Go", "frequency": 0.42 },
    { "name": "Kubernetes", "frequency": 0.35 }
  ]
}
```

### `POST /api/v2/market/companies/{id}/watchlist`
Adds or removes a company to/from the user's active watchlist.
- **Authentication**: Required (JWT, Scope: `user`)
- **Path Parameters**:
  - `id`: `UUID`
- **Request Payload**:
```json
{
  "action": "ADD",
  "notifications_enabled": true
}
```
- **Response (200 OK)**:
```json
{
  "user_id": "8f8e1234-a56b-4c7d-8e9f-0123456789ab",
  "company_id": "e2f3a4b5-6c7d-8e9f-0123-456789abcdef",
  "status": "WATCHING",
  "notifications_enabled": true
}
```

### `GET /api/v2/market/companies/watchlist`
Retrieves all companies tracked by the authenticated user.
- **Authentication**: Required (JWT, Scope: `user`)
- **Response (200 OK)**:
```json
{
  "watchlist": [
    {
      "company_id": "e2f3a4b5-6c7d-8e9f-0123-456789abcdef",
      "name": "Stripe",
      "attractiveness_score": 92.4,
      "active_postings_count": 87,
      "added_at": "2026-06-08T22:00:00Z"
    }
  ]
}
```

### `GET /api/v2/market/companies/{id}/report`
Triggers generation of a detailed JSON payload configured for frontend PDF/HTML rendering.
- **Authentication**: Required (JWT, Scope: `user`)
- **Response (200 OK)**:
```json
{
  "report_metadata": {
    "generated_at": "2026-06-09T02:04:18Z",
    "company_id": "e2f3a4b5-6c7d-8e9f-0123-456789abcdef"
  },
  "company_details": {
    "name": "Stripe",
    "website": "https://stripe.com"
  },
  "velocity_history": [
    { "date": "2026-05-01", "velocity": 16.5, "score": 90.1 },
    { "date": "2026-06-01", "velocity": 24.5, "score": 92.4 }
  ],
  "hiring_insights": {
    "primary_focus": "Infrastructure expansion",
    "estimated_salary_p50": 195000
  }
}
```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime, date
from typing import Optional, List

class CompanyHiringStats(BaseModel):
    active_postings_count: int
    hiring_velocity_30d: float
    hiring_velocity_90d: float
    trend_direction: str
    attractiveness_score: float
    last_updated: datetime

class TopSkillSought(BaseModel):
    name: str
    frequency: float = Field(..., ge=0.0, le=1.0)

class CompanyProfile(BaseModel):
    id: UUID
    name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    size_range: Optional[str] = None
    metrics: CompanyHiringStats
    top_skills_sought: List[TopSkillSought]

class WatchlistRequest(BaseModel):
    action: str = Field(..., regex="^(ADD|REMOVE)$")
    notifications_enabled: bool = True
```

---

## 7. Services

### `CompanyIntelligenceService`
Manages calculation of company scores and database aggregation.
- `calculate_hiring_velocity(company_id: UUID) -> dict`: Compares historical postings counts across 30, 90, and 180 days to compute velocity ratios.
- `update_attractiveness_score(company_id: UUID) -> float`: Evaluates compensation metrics, hiring trends, and business data to calculate the Attractiveness Score.
- `get_company_profile(company_id: UUID) -> CompanyProfile`: Fetches profile details, retrieves cached metrics from Redis, or recalculates them on cache miss.

### `WatchlistService`
Handles watchlist subscriptions and user alerts.
- `add_to_watchlist(user_id: UUID, company_id: UUID, notify: bool) -> None`: Inserts user-company pairing into database.
- `trigger_watchlist_alerts(company_id: UUID, new_posting_id: UUID) -> None`: Scans watches for the company and triggers user events for email/push dispatch.

---

## 8. Events

### Event: `market.company.score_calculated`
- **Producer**: `CompanyIntelligenceService`
- **Consumer**: `intelligence-synthesis-service`, `search-index-update-job`
- **Payload Schema**:
```json
{
  "event_id": "7b8a9c0d-1e2f-3g4h-5i6j-7k8l9m0n1o2p",
  "event_type": "market.company.score_calculated",
  "timestamp": "2026-06-09T02:00:00Z",
  "payload": {
    "company_id": "e2f3a4b5-6c7d-8e9f-0123-456789abcdef",
    "company_name": "Stripe",
    "velocity_30d": 24.5,
    "trend_direction": "ACCELERATING",
    "attractiveness_score": 92.4
  }
}
```

### Event: `market.company.watchlist_alert`
- **Producer**: `WatchlistService`
- **Consumer**: `notification-service`
- **Payload Schema**:
```json
{
  "event_id": "8c9d0e1f-2a3b-4c5d-6e7f-8a9b0c1d2e3f",
  "event_type": "market.company.watchlist_alert",
  "timestamp": "2026-06-09T02:05:00Z",
  "payload": {
    "user_id": "8f8e1234-a56b-4c7d-8e9f-0123456789ab",
    "company_id": "e2f3a4b5-6c7d-8e9f-0123-456789abcdef",
    "company_name": "Stripe",
    "reason": "NEW_JOB_POSTED",
    "details": {
      "job_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3g4h5i6j",
      "job_title": "Senior Infrastructure Engineer"
    }
  }
}
```

---

## 9. Background Jobs
- **`scheduled_company_velocity_aggregation_job`**: Runs nightly. Scans `job_postings`, aggregates job listings per company entity, and updates 30/90-day velocity stats.
- **`scheduled_company_scoring_job`**: Runs weekly. Recalculates the Attractiveness Score and writes a new history snapshot to `company_snapshots`.

---

## 10. Acceptance Criteria

### Ingestion Metric Calculation Scenario
- **Given**: Ingestion pipeline successfully loaded 15 new listings for "Stripe" over the past 30 days, up from 5 postings in the prior month.
- **When**: The `scheduled_company_velocity_aggregation_job` executes.
- **Then**: Stripe's `hiring_velocity_30d` is updated, the `trend_direction` updates to `ACCELERATING`, and a `market.company.score_calculated` event is emitted.

### Watchlist Notification Scenario
- **Given**: A user is watching "Stripe" with notifications enabled.
- **When**: A new Greenhouse posting is crawled for Stripe and is successfully deduplicated as a unique listing.
- **Then**: The system publishes a `market.company.watchlist_alert` event containing the user's ID and the job's title details.

---

## 11. Edge Cases
- **Name Fragmentation**: "Google LLC" vs. "Google Ireland" vs. "Google Inc.". During ingestion, clean corporate suffixes and resolve aliases using a mapping dictionary to link data to a single primary "Google" record.
- **Low Posting Volume**: Small startups might only post one job per quarter. In these cases, calculations should default to 0.00 rather than throwing divide-by-zero or precision errors, and the trend is marked "STABLE".
- **Database Failures**: If PostgreSQL is locked during batch aggregation runs, log the failure to the task queue, retry with exponential backoff, and retain previous metrics until the next database access window.

---

## 12. Test Requirements
- **Velocity Formula Tests**: Mock input timelines of postings and verify that the calculated outputs match mathematical calculations.
- **Concurrency Test**: Test parallel ingestion processing to ensure multiple threads do not lock the same `companies` rows.

---

## 13. Dependencies
- **Direct Blockers**:
  - [Multi-Source Job Ingestion (F2.1)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/multi-source-job-ingestion.md)
- **Downstream Beneficiaries**:
  - [Ghost Posting Detection (F2.5)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/ghost-posting-detection.md)
  - [Opportunity Intelligence (F2.7)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/opportunity-intelligence.md)
  - [Research Agent (F3.3)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
