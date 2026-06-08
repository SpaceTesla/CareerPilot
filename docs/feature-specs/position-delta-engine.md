# Feature Specification: Position Delta Engine

## 1. Purpose
This feature implements the Position Delta Engine, a core analysis component of the platform's Intelligence Synthesis Context. It calculates the exact skill and experience gap (the "delta") between a candidate's current career profile and their stated target career role. By comparing user profiles against target role specifications derived from active market postings, it identifies missing skills, ranks them by market importance, prioritizes the top 3 high-leverage items, and generates evidence-backed recommendations.

For architectural decompositon details, see [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md) and [DEPENDENCY_GRAPH.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md).

## 2. User Value
Candidates often make career transitions blindly, relying on generic advice like "learn AI" or "do more side projects." The Position Delta Engine provides surgical, data-backed guidance. It tells the candidate exactly what skills stand between them and their target role, and prioritizes them based on what recruiters are actually hiring for. This changes the candidate's career progression from guessing to execution.

## 3. Requirements
- **Target Role Specifications**: Maintain a dynamic data model representing the typical requirements for roles (e.g., typical years of experience, common skill requirements, salary percentiles) aggregated from active market data.
- **Profile vs. Target Comparison Engine**: Compare a user's skills list and work experience against the target role model.
- **Missing Skill Detection**: Identify which normalized skills are frequently required in target role postings but are completely absent from the user's active profile.
- **Skill Importance Ranking**: Rank missing skills based on their occurrence frequency (percentage of active postings for the role that require the skill).
- **Top-3 Prioritization**: Select and highlight the top 3 highest-frequency missing skills to provide focused, high-leverage priorities.
- **Evidence-Backed Recommendations**: Synthesize recommendations complete with numerical evidence (e.g. "Adding LangGraph would make you compatible with an additional 43% of AI Backend Engineer postings").

## 4. Database Changes

### `target_role_specifications`
Caches aggregated profiles of target roles to speed up delta queries.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `role_title`: `VARCHAR(255)` (Unique, Indexed, Not Null) - Standardized target role name
- `typical_experience_years`: `NUMERIC(4, 1)` (Not Null)
- `typical_salary_p50`: `NUMERIC(12, 2)` (Nullable)
- `typical_salary_p75`: `NUMERIC(12, 2)` (Nullable)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

### `position_deltas`
Stores computed gap assessments for users.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `user_id`: `UUID` (Foreign Key referencing `users.id` ON DELETE CASCADE, Unique, Indexed, Not Null)
- `target_role`: `VARCHAR(255)` (Not Null) - Cached string of the target role name evaluated
- `missing_skills`: `JSONB` (Default: `'[]'`, Not Null) - Array of objects with keys `[skill_id, name, frequency_pct, importance_rank]`
- `top_3_prioritized_gaps`: `JSONB` (Default: `'[]'`, Not Null) - Detailed structured recommendations for top 3 gaps
- `recommendation_summary`: `TEXT` (Not Null)
- `computed_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Indexed, Not Null)

### Indexes and Migrations
- Unique index on `target_role_specifications.role_title`.
- Index on `position_deltas.user_id`.
- Alembic migration `V2026_06_09_0006_create_position_delta.py` will deploy tables.

## 5. API Endpoints

### `GET /api/v2/intelligence/position-delta`
Retrieves the user's active position gap evaluation, missing skills list, and prioritized recommendations.
- **Request Headers**: JWT Bearer Token
- **Response Body (200 OK)**:
  ```json
  {
    "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a",
    "target_role": "AI Platform Engineer",
    "computed_at": "2026-06-09T02:04:18Z",
    "recommendation_summary": "You have solid backend foundations but need experience with container orchestrations and LLM frameworks to be competitive.",
    "top_3_prioritized_gaps": [
      {
        "skill_name": "LangGraph",
        "importance_rank": 1,
        "frequency_pct": 68.5,
        "actionable_recommendation": "Build a multi-agent system project. Mention LangGraph and state management on your profile."
      },
      {
        "skill_name": "Kubernetes",
        "importance_rank": 2,
        "frequency_pct": 52.0,
        "actionable_recommendation": "Add your experience deploying Docker containers into clustered K8s environments."
      },
      {
        "skill_name": "Qdrant",
        "importance_rank": 3,
        "frequency_pct": 41.5,
        "actionable_recommendation": "Highlight vector databases usage in search optimization projects."
      }
    ],
    "all_gaps": [
      {
        "skill_name": "LangGraph",
        "frequency_pct": 68.5
      },
      {
        "skill_name": "Kubernetes",
        "frequency_pct": 52.0
      },
      {
        "skill_name": "Qdrant",
        "frequency_pct": 41.5
      },
      {
        "skill_name": "Triton Inference Server",
        "frequency_pct": 18.0
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
from typing import List, Optional

class DeltaGapItem(BaseModel):
    skill_name: str
    importance_rank: int
    frequency_pct: Decimal = Field(..., max_digits=5, decimal_places=2)
    actionable_recommendation: str

class SimpleGapItem(BaseModel):
    skill_name: str
    frequency_pct: Decimal = Field(..., max_digits=5, decimal_places=2)

class PositionDeltaResponse(BaseModel):
    user_id: UUID
    target_role: str
    computed_at: datetime
    recommendation_summary: str
    top_3_prioritized_gaps: List[DeltaGapItem]
    all_gaps: List[SimpleGapItem]
```

## 7. Services

### `PositionDeltaService`
- **Responsibilities**: Performs calculations comparing profile lists to market metrics, generates recommendation structures, and manages DB persistence.
- **Methods**:
  - `compute_delta(user_id: UUID) -> PositionDelta`: Retrieves profile skills and goals, queries market table statistics for matching role descriptions, identifies missing entities, sorts by frequency, compiles recommendation objects, and saves record. Emits `position_delta.computed` event.
  - `get_delta(user_id: UUID) -> Optional[PositionDelta]`: Fetches user's latest computed delta record.

### `TargetRoleSpecificationService`
- **Responsibilities**: Updates cached role parameters from aggregates of raw postings.
- **Methods**:
  - `rebuild_role_specifications() -> None`: Daily database cron job querying `job_postings` and `job_postings_skills` to rebuild the specifications table.

## 8. Events

- **`position_delta.computed`**:
  - **Producer**: `PositionDeltaService.compute_delta`
  - **Consumers**: `DashboardAggregationService` (triggers widget cache clearance), `StrategyService` (suggests strategy revision based on new gaps).
  - **Payload**:
    ```json
    {
      "event_id": "0d3a0ee1-21cb-40bc-98cb-09a1fb32bccc",
      "event_type": "position_delta.computed",
      "timestamp": "2026-06-09T02:04:18Z",
      "data": {
        "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a",
        "target_role": "AI Platform Engineer",
        "top_gaps": ["LangGraph", "Kubernetes", "Qdrant"]
      }
    }
    ```

## 9. Background Jobs
No background cron tasks run directly in V1. Calculations are triggered asynchronously alongside the health score computation in Celery during user profile or goals modifications.

## 10. Acceptance Criteria

- **Scenario: Identify Missing Skills**
  - **Given** a user has "Python" and "SQL" on their profile, and the target role specification lists "Python" (100% frequency), "Docker" (70%), and "LangGraph" (60%),
  - **When** calling the delta engine,
  - **Then** identify "Docker" and "LangGraph" as missing, leaving out "Python".
- **Scenario: Correct Sorting of Gaps**
  - **Given** missing skills "Docker" (70% frequency) and "LangGraph" (60% frequency) and "Qdrant" (40%),
  - **When** computing delta priorities,
  - **Then** sort gaps in descending order of frequency (Docker, LangGraph, Qdrant) and assign ranks 1, 2, and 3.
- **Scenario: Perfect Match Gaps**
  - **Given** a user who possesses all skills required in target specifications,
  - **When** running delta calculation,
  - **Then** return an empty `top_3_prioritized_gaps` array, set `recommendation_summary` to "You match all core skills. You are ready to target applications.", and commit cleanly.

## 11. Edge Cases
- **No Active Postings for Target Role**: If the database contains zero job postings for the requested title, the system falls back to a broader sector standard (e.g. matching general "Backend" specs if target is "AI Python Backend Developer") rather than returning an empty calculation or error.
- **Skills Aliases Overlap**: The engine resolves skill aliases to their master name (e.g., if a user has "k8s" on their profile and the role requires "Kubernetes", the system matches them and does not flag a gap).
- **User Has No Skills Listed**: If the candidate's profile is empty, the engine lists the top 3 highest-frequency skills for that role overall as the gaps, rather than crashing.

## 12. Test Requirements
- **Unit Tests**:
  - Test ranking math and sorting behaviors with mock inputs.
  - Assert skill alias resolution catches standard synonyms.
- **Integration Tests**:
  - Assert that calling the API retrieves structured JSON payloads matching the `PositionDeltaResponse` schema definition.
  - Validate database cascading (deleting a user account cleans up target specs maps and delta rows).

## 13. Dependencies
This feature depends on:
- [career-profile-domain.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-profile-domain.md) (user profile data)
- [job-market-data-foundation.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/job-market-data-foundation.md) (job skills frequency benchmarks)
Downward features that depend on this are:
- [career-dashboard.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-dashboard.md)
