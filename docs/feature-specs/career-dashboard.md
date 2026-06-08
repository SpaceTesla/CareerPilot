# Feature Specification: Career Dashboard

## 1. Purpose
This feature implements the Career Dashboard, the primary entry point and central aggregator for CareerPilot. It compiles multiple analytical components—the Career Health Score, Score Change, Market Insights, Position Delta, and Opportunity Spotlights—into a unified endpoint (`GET /api/v2/dashboard`). It configures user-specific Redis caching, sets up asynchronous concurrent service aggregation, structures frontend components with loading/error UI states, and tracks user interaction analytics.

For details on the user interface structure and dashboard surfaces, refer to [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md). For structural dependencies, see [DEPENDENCY_GRAPH.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md).

## 2. User Value
The dashboard is the central terminal for managing one's career. It synthesizes complex, distributed information (skills metrics, application state, and market movements) into a clean, 60-second summary. Instead of forcing users to dig through separate reports, it highlights immediate changes and prioritized actions, encouraging passive, weekly engagement with the Career Intelligence loop.

## 3. Requirements
- **Dashboard API Aggregator**: Build an asynchronous coordinator endpoint that concurrently pulls data from Health, Delta, and Market services using `asyncio.gather`.
- **Integrated Widgets**:
  - **Health Score Widget**: Displays the 0-100 composite score.
  - **Score Change Widget**: Indicates the 7-day and 30-day delta values with directional trend indicators.
  - **Market Insight Widget**: Highlights high-level market changes (e.g. hiring velocity, skill appreciation).
  - **Position Delta Widget**: Highlights the top 3 gaps and actionable recommendations.
  - **Opportunity Spotlight Widget**: Shows 1-3 best-fit jobs based on goals and profile.
- **Aggregated Caching**: Cache the assembled dashboard response in Redis with user-specific keys. Evict the cache when user profiles, goals, or the daily materialized view refreshes.
- **Frontend Screen Layout**: Design structured single-page application layouts complete with loading skeletons, fallback error cards, and interactive buttons.
- **Analytics Tracker**: Log client-side page views and widget interactions in a structured events table.

## 4. Database Changes

### `dashboard_analytics_events`
Tracks user interaction with dashboard items to measure engagement.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `user_id`: `UUID` (Foreign Key referencing `users.id` ON DELETE CASCADE, Indexed, Not Null)
- `event_type`: `VARCHAR(100)` (Not Null) - E.g. "VIEW_DASHBOARD", "CLICK_WIDGET"
- `widget_name`: `VARCHAR(100)` (Nullable) - E.g. "POSITION_DELTA", "HEALTH_SCORE"
- `metadata`: `JSONB` (Default: `'{}'`, Not Null) - Contains details like target URLs or click targets
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Indexed, Not Null)

### Indexes and Migrations
- Composite index on `dashboard_analytics_events(user_id, created_at DESC)`.
- Alembic migration `V2026_06_09_0007_create_dashboard_tables.py` will deploy the table.

## 5. API Endpoints

### `GET /api/v2/dashboard`
Aggregates health, delta, and opportunities for the current authenticated user. Served from Redis if cached.
- **Request Headers**: JWT Bearer Token
- **Response Headers**:
  - `X-Cache`: `"HIT"` or `"MISS"`
- **Response Body (200 OK)**:
  ```json
  {
    "timestamp": "2026-06-09T02:04:18Z",
    "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a",
    "health_score": {
      "score": 78.50,
      "delta_7d": 2.10,
      "primary_insight": "Your positioning for AI Platform Engineer roles improved because Kubernetes was verified in your profile."
    },
    "position_delta": {
      "top_3_gaps": [
        {
          "skill_name": "LangGraph",
          "importance_rank": 1,
          "actionable_recommendation": "Build a multi-agent system project. Mention LangGraph and state management on your profile."
        }
      ]
    },
    "market_insight": {
      "insight_text": "AI infrastructure roles at Series B companies are up 34% this month. Your profile is in the top 15% for these roles."
    },
    "opportunity_spotlight": [
      {
        "id": "7db091bb-000c-4828-9828-0902bd32a688",
        "company_name": "Anthropic",
        "title": "AI Platform Engineer",
        "fit_score": 94,
        "location": "San Francisco, CA",
        "salary_range": "$190,000 - $240,000"
      }
    ]
  }
  ```

### `POST /api/v2/dashboard/analytics`
Logs user interactions with the dashboard widgets.
- **Request Headers**: JWT Bearer Token
- **Request Body**:
  ```json
  {
    "event_type": "CLICK_WIDGET",
    "widget_name": "OPPORTUNITY_SPOTLIGHT",
    "metadata": {
      "job_posting_id": "7db091bb-000c-4828-9828-0902bd32a688",
      "target_company": "Anthropic"
    }
  }
  ```
- **Response Body (201 Created)**:
  ```json
  {
    "status": "logged",
    "event_id": "ab71efd3-90d4-4899-b1d1-08dcd3f218bb"
  }
  ```

## 6. Domain Models

### Pydantic Schemas

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

class DashboardHealthWidget(BaseModel):
    score: Decimal = Field(..., max_digits=5, decimal_places=2)
    delta_7d: Decimal = Field(..., max_digits=5, decimal_places=2)
    primary_insight: str

class DashboardDeltaItem(BaseModel):
    skill_name: str
    importance_rank: int
    actionable_recommendation: str

class DashboardDeltaWidget(BaseModel):
    top_3_gaps: List[DashboardDeltaItem]

class DashboardMarketWidget(BaseModel):
    insight_text: str

class DashboardSpotlightItem(BaseModel):
    id: UUID
    company_name: str
    title: str
    fit_score: int
    location: str
    salary_range: Optional[str] = None

class DashboardResponse(BaseModel):
    timestamp: datetime
    user_id: UUID
    health_score: DashboardHealthWidget
    position_delta: DashboardDeltaWidget
    market_insight: DashboardMarketWidget
    opportunity_spotlight: List[DashboardSpotlightItem]

class AnalyticsLogRequest(BaseModel):
    event_type: str
    widget_name: Optional[str] = None
    metadata: dict = {}
```

## 7. Services

### `DashboardAggregationService`
- **Responsibilities**: Pulls data blocks from underlying modules, maps schemas, handles caching layers, and coordinates async requests.
- **Methods**:
  - `generate_dashboard(user_id: UUID) -> DashboardResponse`: Fetches caching. If cache is empty, executes concurrent calls:
    - `CareerHealthService.get_latest_score(user_id)`
    - `PositionDeltaService.get_delta(user_id)`
    - `MarketIntelligenceService.get_spotlight_opportunities(user_id)`
    Merges results, writes to Redis, and returns the response.
  - `invalidate_cache(user_id: UUID) -> None`: Evicts user-specific dashboard keys.

### `AnalyticsService`
- **Responsibilities**: Stores log entries.
- **Methods**:
  - `log_event(user_id: UUID, payload: AnalyticsLogRequest) -> UUID`: Records user activity in database.

## 8. Events
- **`dashboard.viewed`**:
  - **Producer**: `/api/v2/dashboard` route.
  - **Consumers**: `AnalyticsService` (creates analytics record).
  - **Payload**:
    ```json
    {
      "event_id": "0d3a771b-21da-45fb-98cb-09a2d3b2bcca",
      "event_type": "dashboard.viewed",
      "timestamp": "2026-06-09T02:04:18Z",
      "data": {
        "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a"
      }
    }
    ```

## 9. Background Jobs
No background jobs run directly. Cache invalidation is handled reactively via events (`health_score.computed`, `position_delta.computed`).

## 10. Acceptance Criteria

- **Scenario: Concurrent Fetch Execution**
  - **Given** three backing services (Health, Delta, Spotlight),
  - **When** calling the aggregator API,
  - **Then** execute calls in parallel using async routines. The maximum timeout for the entire request is 5 seconds.
- **Scenario: Cache Validation & Eviction**
  - **Given** a warm dashboard cache,
  - **When** a user updates their skills list (firing `profile.updated`),
  - **Then** evict the Redis cache immediately, forcing the subsequent dashboard fetch to compute fresh figures.
- **Scenario: Incomplete User Profile Route**
  - **Given** a user has not uploaded a resume or completed their profile setup,
  - **When** fetching the dashboard,
  - **Then** return HTTP 200 containing empty metrics, and return onboarding instruction payloads so the client can render the initial setup wizard.

## 11. Edge Cases
- **Downstream Service Failures**: If one service (e.g. Opportunity Spotlight) fails or times out, the aggregator logs the error, falls back to a blank payload or cached metadata for that widget, and renders the rest of the dashboard successfully rather than crashing.
- **Stale Materialized Views**: During the daily materialized view refresh, the dashboard reads from the last complete snapshot of trends, ensuring zero uptime degradation for clients.
- **Rate Limiting**: Users reloading the dashboard page continuously are limited to 30 requests per minute. Excess requests return HTTP 429 and are served from browser cache.

## 12. Test Requirements
- **Unit Tests**:
  - Assert the aggregator merges disparate models (Health, Delta, Opportunities) into a valid response.
  - Validate caching TTL is correctly configured.
- **Integration Tests**:
  - Simulate a slow network environment and test the 5-second aggregate timeout.
  - Run regression checks asserting cache eviction fires on profile updates.

## 13. Dependencies
This feature depends on:
- [authentication-identity-context.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/authentication-identity-context.md) (authorization contexts)
- [career-profile-domain.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-profile-domain.md) (profile details)
- [career-health-score-engine-v1.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-health-score-engine-v1.md) (health stats widget)
- [position-delta-engine.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/position-delta-engine.md) (delta widget)
There are no Epic 1 features that depend on this feature; it is the terminal presenter module for Epic 1.
