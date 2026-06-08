# Feature Specification: Career Health Score Engine V1

## 1. Purpose
This feature implements the Career Health Score engine, the primary user-facing intelligence output of the platform. It calculates a composite score (0-100) representing how well-positioned a candidate is for their target career role. The score is compiled from five weighted components: Skill Alignment, Market Positioning, Activity Health, Compensation Alignment, and Profile Completeness. It provides structured historical database tracking, explanation generation, and API presentation.

For product design specifications and code representations, refer to [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md). For feature dependencies, see [DEPENDENCY_GRAPH.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md).

## 2. User Value
Most professionals lack objective indicators of their career competitiveness. By providing a "Career Credit Score," users can monitor their market value and career health continuously. The breakdown reveals exactly why their score changed and points to specific improvements, turning career management into an active, data-driven compounding habit.

## 3. Requirements
- **Composite Score Engine**: Build a linear score weighting aggregator that combines five distinct component scores:
  - **Skill Alignment (30% weight)**: Measures user's skills against the most frequent skills found in job postings matching their `target_role`.
  - **Market Positioning (25% weight)**: Measures the candidate's seniority and specialized experience against active job posting requirements.
  - **Activity Health (20% weight)**: Measures job application volumes, interview conversions, or profile updates.
  - **Compensation Alignment (15% weight)**: Compares the user's `target_compensation_min` against market salary benchmarks (P25, P50, P75) for the role.
  - **Profile Completeness (10% weight)**: Percentage of required profile fields populated.
- **Explanation Generator**: Synthesize structured explanations identifying the primary driver (largest positive change) and primary detractor (largest gap) impacting the score.
- **Historical Tracking**: Save computed scores in a historical log on every change, enabling time-series visualization.
- **Async Execution Worker**: Wrap computations in a Celery background task triggered by profile updates or goal changes to keep API response times low.

## 4. Database Changes

### `career_health_scores`
Stores historical and active health score calculations.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `user_id`: `UUID` (Foreign Key referencing `users.id` ON DELETE CASCADE, Indexed, Not Null)
- `score`: `NUMERIC(5, 2)` (Not Null) - Composite score from 0.00 to 100.00
- `skill_alignment_score`: `NUMERIC(5, 2)` (Not Null)
- `market_positioning_score`: `NUMERIC(5, 2)` (Not Null)
- `activity_health_score`: `NUMERIC(5, 2)` (Not Null)
- `compensation_alignment_score`: `NUMERIC(5, 2)` (Not Null)
- `profile_completeness_score`: `NUMERIC(5, 2)` (Not Null)
- `primary_insight`: `TEXT` (Not Null) - Summary explanation
- `top_driver`: `VARCHAR(255)` (Not Null) - Main positive factor
- `top_detractor`: `VARCHAR(255)` (Not Null) - Main negative factor
- `computed_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Indexed, Not Null)

### Indexes and Migrations
- Composite Index on `career_health_scores(user_id, computed_at DESC)`.
- Alembic migration `V2026_06_09_0005_create_health_score.py` will generate the table.

## 5. API Endpoints

### `GET /api/v2/intelligence/health-score`
Retrieves the most recent health score with detailed components and explanations.
- **Request Headers**: JWT Bearer Token
- **Response Body (200 OK)**:
  ```json
  {
    "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a",
    "computed_at": "2026-06-09T02:04:18Z",
    "score": 78.50,
    "delta_7d": 2.10,
    "delta_30d": 5.00,
    "components": {
      "skill_alignment_score": 85.00,
      "market_positioning_score": 75.00,
      "activity_health_score": 90.00,
      "compensation_alignment_score": 60.00,
      "profile_completeness_score": 100.00
    },
    "primary_insight": "Your positioning for AI Platform Engineer roles improved because Kubernetes was verified in your profile.",
    "top_driver": "High skill alignment on core infrastructure tools.",
    "top_detractor": "Target compensation of $240,000 is in the P90 range for this role, reducing matching postings."
  }
  ```

### `GET /api/v2/intelligence/health-score/history`
Returns historical scores for charting.
- **Query Parameters**:
  - `limit`: default 30 (days/records)
- **Response Body (200 OK)**:
  ```json
  {
    "history": [
      {
        "computed_at": "2026-06-09T02:04:18Z",
        "score": 78.50
      },
      {
        "computed_at": "2026-06-02T02:00:00Z",
        "score": 76.40
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
from decimal import Decimal
from typing import Dict, List

class HealthComponentsSchema(BaseModel):
    skill_alignment_score: Decimal = Field(..., max_digits=5, decimal_places=2)
    market_positioning_score: Decimal = Field(..., max_digits=5, decimal_places=2)
    activity_health_score: Decimal = Field(..., max_digits=5, decimal_places=2)
    compensation_alignment_score: Decimal = Field(..., max_digits=5, decimal_places=2)
    profile_completeness_score: Decimal = Field(..., max_digits=5, decimal_places=2)

class HealthScoreResponse(BaseModel):
    user_id: UUID
    computed_at: datetime
    score: Decimal = Field(..., max_digits=5, decimal_places=2)
    delta_7d: Decimal = Field(..., max_digits=5, decimal_places=2)
    delta_30d: Decimal = Field(..., max_digits=5, decimal_places=2)
    components: HealthComponentsSchema
    primary_insight: str
    top_driver: str
    top_detractor: str
```

## 7. Services

### `CareerHealthService`
- **Responsibilities**: Gathers required inputs from Profile, Market, and Goals contexts, calls math helpers, compiles explanation string, and commits record.
- **Methods**:
  - `compute_score(user_id: UUID) -> CareerHealthScore`: Performs computations, evaluates delta against history, saves and returns results. Emits `health_score.computed` event.
  - `get_latest_score(user_id: UUID) -> Optional[CareerHealthScore]`: Fetches most recent row.
  - `get_history(user_id: UUID, limit: int) -> List[dict]`: Fetches limited historical timeline entries.

### `ScoreWeightingEngine`
- **Responsibilities**: Encapsulates formula weights and handles raw calculations.
- **Methods**:
  - `calculate_skill_alignment(profile_skills: List[str], target_role: str) -> float`: Evaluates percentage of core skills present. Matches against required skills lists extracted from active job postings for the role.
  - `calculate_market_positioning(profile: dict, target_role: str) -> float`: Compares years of experience vs. average posting demands.
  - `calculate_activity_health(search_status: str, application_activity: List[dict]) -> float`: Evaluates submission frequencies; defaults to high scores (95.0+) if search status is passive/closed.
  - `calculate_compensation_alignment(target_salary: float, role_benchmarks: dict) -> float`: Evaluates target vs. market percentiles.
  - `calculate_profile_completeness(profile: dict) -> float`: Calculates field presence ratios.
  - `combine_weights(components: dict) -> float`: Multiplies components by their relative weights (`[0.30, 0.25, 0.20, 0.15, 0.10]`) to output composite score.

## 8. Events

- **`health_score.computed`**:
  - **Producer**: `CareerHealthService.compute_score`
  - **Consumers**: `NotificationService` (alert user if score changes by > 5 points), `DashboardAggregationService` (invalidate cached dashboard elements).
  - **Payload**:
    ```json
    {
      "event_id": "c71ea00d-45bf-4078-bb18-a6e11bdcbcc1",
      "event_type": "health_score.computed",
      "timestamp": "2026-06-09T02:04:18Z",
      "data": {
        "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a",
        "new_score": 78.50,
        "delta_7d": 2.10
      }
    }
    ```

## 9. Background Jobs

### `async_recompute_health_score`
- **Trigger**: Celery queue, triggered by `profile.updated` or `identity.goals_updated` events.
- **Payload**:
  ```json
  {
    "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a"
  }
  ```
- **Workflow**: Invokes `CareerHealthService.compute_score(user_id)`.
- **Retry Behavior**: Retries 3 times, delay 30s.

## 10. Acceptance Criteria

- **Scenario: Score Weight Aggregation**
  - **Given** component scores of Skill Alignment (100.0), Market Positioning (80.0), Activity Health (90.0), Comp Alignment (50.0), and Profile Completeness (100.0),
  - **When** calling the weighting engine,
  - **Then** output exactly: `(100 * 0.3) + (80 * 0.25) + (90 * 0.2) + (50 * 0.15) + (100 * 0.1) = 30 + 20 + 18 + 7.5 + 10 = 85.50`.
- **Scenario: Unrealistic Salary Target Detractor**
  - **Given** a market P75 salary benchmark of $150,000 for a role, and a user sets a target of $300,000 (200% of P75),
  - **When** health score recalculates,
  - **Then** return a low compensation alignment score (< 40.0) and flag `compensation` as the top detractor in the explanation.
- **Scenario: Recalculation Trigger**
  - **Given** a user has updated their goals via API,
  - **When** the goals update transaction completes,
  - **Then** verify a `health_score.computed` event is dispatched and the `career_health_scores` table gets a new row.

## 11. Edge Cases
- **No Job Postings Found for Target Role**: If the database contains zero job postings for the user's `target_role`, the engine defaults the required skills list to national tech averages (e.g. Python, SQL) and sets the market benchmarking values to generic templates to avoid dividing by zero.
- **Salary Target is Zero**: If the user omits or inputs $0 for target salary, the engine skips compensation penalty calculations and normalizes the component score to 100.0 to prevent mathematical distortion.
- **Profile Devoid of Experience**: If the user has an empty work history, the Market Positioning component defaults to 0.00 rather than crashing, reflecting a high barrier to entering senior/staff markets.

## 12. Test Requirements
- **Unit Tests**:
  - Test aggregate math calculations asserting strict boundary checks (0.00 to 100.00).
  - Test calculation formulas under varying inputs (different search states, salary percentiles).
- **Integration Tests**:
  - Mock the database connections and check that updating profile details triggers the Celery worker and yields a valid new database row.
  - Verify that retrieving historical trends returns lists sorted chronologically.

## 13. Dependencies
This feature depends on:
- [authentication-identity-context.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/authentication-identity-context.md) (user goals references)
- [career-profile-domain.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-profile-domain.md) (profile details)
- [skill-trend-engine-v1.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/skill-trend-engine-v1.md) (market skill reference metrics)
Downward features that depend on this are:
- [career-dashboard.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-dashboard.md)
