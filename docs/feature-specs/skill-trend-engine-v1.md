# Feature Specification: Skill Trend Engine V1

## 1. Purpose
This feature powers the skill assessment capabilities of CareerPilot. It aggregates required skills from active job postings to compute frequency and demand velocity metrics. By executing a daily Celery aggregation worker that refreshes Postgres materialized views and caches results in Redis, this engine exposes which skills are rising or declining in market demand.

For structural details on the underlying job postings database, see [job-market-data-foundation.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/job-market-data-foundation.md). For how this maps to the overall compounding loop, see [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md).

## 2. User Value
Software engineering landscapes shift rapidly; skills that were highly compensated 18 months ago may be commoditizing now. The Skill Trend Engine provides candidates with objective, data-backed insights into what skills the market actually demands. This prevents engineers from investing time in depreciating skills and helps them focus their learning on high-velocity technologies (e.g., LangGraph, Kubernetes) to maximize their Career Health Score.

## 3. Requirements
- **Granular Daily Aggregations**: Persist daily snapshots of posting counts and relative frequency for each skill in a structured table.
- **Materialized Views for Performance**: Implement a PostgreSQL materialized view (`mv_skill_trends`) that aggregates metrics over 30-day windows to avoid heavy runtime calculation costs.
- **Velocity Computations**: Implement a comparison formula that evaluates the frequency percentage change in the current 30-day window against the preceding 30-day window.
- **Cache Infrastructure**: Cache the aggregated trending skills list API response in Redis with a 12-hour Time-To-Live (TTL).
- **Automated Refresh Worker**: Set up a Celery task that runs daily in the early morning to run the materialized view refresh and update the cache.

## 4. Database Changes

### `skill_trends_daily`
Stores the daily raw volume and frequency details.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `skill_id`: `UUID` (Foreign Key referencing `normalized_skills.id` ON DELETE CASCADE, Indexed, Not Null)
- `snapshot_date`: `DATE` (Indexed, Not Null)
- `posting_count`: `INTEGER` (Not Null) - Number of postings on this day requiring this skill
- `total_postings_count`: `INTEGER` (Not Null) - Total active postings on this day
- `frequency`: `NUMERIC(6, 5)` (Not Null) - `posting_count` divided by `total_postings_count`

### `mv_skill_trends` (Materialized View)
Pre-aggregates counts, frequencies, and velocities for rapid API reads.
- `skill_id`: `UUID` (Primary Key constraint)
- `skill_name`: `VARCHAR(100)`
- `count_30d`: `INTEGER` - Posting count in the last 30 days
- `freq_30d`: `NUMERIC(6, 5)` - Frequency in the last 30 days
- `count_prev_30d`: `INTEGER` - Posting count in the prior 30 days (days -60 to -30)
- `freq_prev_30d`: `NUMERIC(6, 5)` - Frequency in the prior 30 days
- `velocity`: `NUMERIC(6, 3)` - Demand change rate between windows

#### Materialized View SQL Definition
```sql
CREATE MATERIALIZED VIEW mv_skill_trends AS
WITH current_30 AS (
    SELECT 
        skill_id,
        SUM(posting_count) as count_30d,
        AVG(frequency) as freq_30d
    FROM skill_trends_daily
    WHERE snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY skill_id
),
prior_30 AS (
    SELECT 
        skill_id,
        SUM(posting_count) as count_prev_30d,
        AVG(frequency) as freq_prev_30d
    FROM skill_trends_daily
    WHERE snapshot_date >= CURRENT_DATE - INTERVAL '60 days'
      AND snapshot_date < CURRENT_DATE - INTERVAL '30 days'
    GROUP BY skill_id
)
SELECT 
    ns.id as skill_id,
    ns.name as skill_name,
    COALESCE(c.count_30d, 0)::INTEGER as count_30d,
    COALESCE(c.freq_30d, 0.0)::NUMERIC(6,5) as freq_30d,
    COALESCE(p.count_prev_30d, 0)::INTEGER as count_prev_30d,
    COALESCE(p.freq_prev_30d, 0.0)::NUMERIC(6,5) as freq_prev_30d,
    CASE 
        WHEN COALESCE(p.freq_prev_30d, 0.0) = 0.0 THEN 0.0
        ELSE ((COALESCE(c.freq_30d, 0.0) - p.freq_prev_30d) / p.freq_prev_30d)::NUMERIC(6,3)
    END as velocity
FROM normalized_skills ns
LEFT JOIN current_30 c ON ns.id = c.skill_id
LEFT JOIN prior_30 p ON ns.id = p.skill_id;

CREATE UNIQUE INDEX idx_mv_skill_trends_id ON mv_skill_trends(skill_id);
```

### Indexes and Migrations
- Index on `skill_trends_daily(snapshot_date, skill_id)`.
- Alembic migration `V2026_06_09_0004_create_skill_trends.py` will deploy table, view, and indexes.

## 5. API Endpoints

### `GET /api/v2/market/trends`
Fetches a list of trending skills sorted by velocity or posting frequency. Served from Redis if cached.
- **Query Parameters**:
  - `sort_by`: `"velocity"` (default) or `"frequency"`
  - `limit`: default 20, max 100
  - `offset`: default 0
- **Response Headers**:
  - `X-Cache`: `"HIT"` or `"MISS"`
- **Response Body (200 OK)**:
  ```json
  {
    "timestamp": "2026-06-09T02:04:18Z",
    "trends": [
      {
        "skill_id": "c7128cf7-21a4-4f81-9b1b-7a32bd32a688",
        "skill_name": "LangGraph",
        "count_30d": 240,
        "frequency_30d": 0.12000,
        "velocity": 0.450
      },
      {
        "skill_id": "a189f783-91aa-4789-bb11-47fa3cd29bb1",
        "skill_name": "Kubernetes",
        "count_30d": 810,
        "frequency_30d": 0.40500,
        "velocity": 0.052
      }
    ]
  }
  ```

## 6. Domain Models

### Pydantic Schemas

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List
from decimal import Decimal

class SkillTrendItem(BaseModel):
    skill_id: UUID
    skill_name: str
    count_30d: int
    frequency_30d: Decimal = Field(..., max_digits=6, decimal_places=5)
    velocity: Decimal = Field(..., max_digits=6, decimal_places=3)

class SkillTrendsResponse(BaseModel):
    timestamp: datetime
    trends: List[SkillTrendItem]
```

## 7. Services

### `SkillTrendService`
- **Responsibilities**: Pulls aggregates from materialized view, handles fallback logic on cache misses, manages caching entries in Redis, and runs the snapshot calculations.
- **Methods**:
  - `get_trends(sort_by: str, limit: int, offset: int) -> List[SkillTrendItem]`: Queries Redis cache. If key is missing, queries `mv_skill_trends`, updates Redis, and returns list.
  - `compute_daily_snapshots() -> None`: Inserts daily records into `skill_trends_daily` by querying active `job_postings` and counting matching skill intersections.
  - `refresh_materialized_view() -> None`: Executes `REFRESH MATERIALIZED VIEW CONCURRENTLY mv_skill_trends`. Clears Redis keys on completion. Emits `market.skill_trends_refreshed` event.

## 8. Events

- **`market.skill_trends_refreshed`**:
  - **Producer**: `SkillTrendService.refresh_materialized_view`
  - **Consumers**: `CareerHealthScoreEngine` (triggers check to see if user health scores need updating based on new market trends).
  - **Payload**:
    ```json
    {
      "event_id": "4eb9cd2d-961f-442c-a2b1-09cdb3f29bb0",
      "event_type": "market.skill_trends_refreshed",
      "timestamp": "2026-06-09T02:04:18Z",
      "data": {
        "snapshot_date": "2026-06-09",
        "total_skills_tracked": 420
      }
    }
    ```

## 9. Background Jobs

### `daily_aggregate_trends`
- **Trigger**: Cron, daily at 02:00 AM.
- **Payload**: None.
- **Workflow**:
  1. Executes `SkillTrendService.compute_daily_snapshots()` to write the previous day's metrics.
  2. Executes `SkillTrendService.refresh_materialized_view()` to refresh view concurrently.
- **Retry Behavior**: Retries 3 times, exponential backoff (delay 300s, multiplier 2).

## 10. Acceptance Criteria

- **Scenario: Materialized View Refresh**
  - **Given** new daily snapshots are written to `skill_trends_daily`,
  - **When** calling the refresh worker,
  - **Then** the materialized view is refreshed concurrently, no database read lock is held (queries still execute), and the unique index is preserved.
- **Scenario: Velocity Math Corner Cases**
  - **Given** a skill has a `freq_prev_30d` of `0.0` (it was never seen), and a `freq_30d` of `0.02000`,
  - **When** the materialized view is refreshed,
  - **Then** output the velocity as `0.000` rather than throwing a division-by-zero database error.
- **Scenario: Cache Hit Performance**
  - **Given** a populated database and a warm cache,
  - **When** executing a load test against `GET /api/v2/market/trends`,
  - **Then** the response must return `X-Cache: HIT` and resolve in under 10ms for 95% of requests.

## 11. Edge Cases
- **New Emerging Skills**: Emerging skills with zero occurrences in the previous 30-day window default to a velocity of `0.000` in V1. A future iteration will calculate velocity based on shorter 7-day windows for emerging signals.
- **Dead/Expired Postings Cleaning**: Postings marked `is_active: false` or past their expiry date are ignored by daily snapshots to ensure the trends represent current hiring market conditions.
- **Database Connection Dropout**: If Postgres fails during refresh, the Redis cache is not evicted, ensuring clients can still fetch the previous day's trends while the database recovers.

## 12. Test Requirements
- **Unit Tests**:
  - Test calculation formulas (assert velocity = 0.500 if frequency rises from 0.04 to 0.06).
  - Assert velocity safety blocks (division by zero overrides).
- **Integration Tests**:
  - Insert mock postings, execute the celery aggregation task, and verify that `mv_skill_trends` values match mathematically calculated outcomes.
  - Assert Redis gets populated on the first API hit and subsequent calls read from Redis.

## 13. Dependencies
This feature depends on [job-market-data-foundation.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/job-market-data-foundation.md).
Downward features that depend on this are:
- [career-health-score-engine-v1.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-health-score-engine-v1.md)
