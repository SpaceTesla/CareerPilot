# Feature Specification: Career Strategy Reviews (F7.4)

## 1. Purpose
The `Career Strategy Reviews` feature provides a monthly strategy review orchestrated by AI agents. Running on a monthly Temporal schedule, it reviews a user's progress (skill updates, application outcomes, and market changes) to generate structured career advice and actionable next steps.

---

## 2. User Value
Software engineers often lack structured feedback loops outside of corporate performance reviews, which are aligned with company goals rather than candidate progression. 
Career Strategy Reviews provide a monthly check-in focused on the user's career. It evaluates what works, identifies skill gaps, and recommends updates. 
Within the **Career Intelligence Compounding Loop** (outlined in [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md)), this feature serves as the planning gate. It uses historical outcomes to adjust the user's positioning, ensuring their strategy matches current market demand.

---

## 3. Requirements
- **Strategy Review Database Schema**: Store monthly reviews, snapshots of career goals, generated recommendations, and action item task lists.
- **Monthly Review Workflow**: Deploy a Temporal cron workflow that initiates strategy reviews every 30 days.
- **Strategic Recommendation Generation**: Use the [Supervisor Agent (F3.2)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md) and [Intelligence Agent (F3.4)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md) to parse user histories and generate actionable goals.
- **Strategy History Tracking**: Assess progress on action items from previous reviews and carry over unresolved items.
- **Review APIs**: Endpoints to list reviews, fetch detailed advice, and update action items.
- **Review Dashboard UI Aggregation**: Analytics and metrics mapping goals over time.
- **System Notifications**: Alert users when a review is ready for feedback.
- **Observability and Metrics**: Instrument Langfuse tracing to monitor LLM costs and token usage during review generation.

---

## 4. Database Changes

Maintains strategy reviews and lists of generated action items.

### Schema Definitions

#### Table: `career_strategy_reviews`
Stores monthly review records.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `user_id`: `UUID` (FK referencing `users.id`, ON DELETE CASCADE)
- `status`: `VARCHAR(50)` (e.g., "PENDING_REVIEW", "COMPLETED", "SKIPPED")
- `goals_snapshot`: `JSONB` (User career goals at the time of review)
- `health_score_start`: `DECIMAL(5, 2)`
- `health_score_end`: `DECIMAL(5, 2)`
- `insights_summary`: `TEXT` (AI generated summary)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)
- `completed_at`: `TIMESTAMP WITH TIME ZONE` (Nullable)

#### Table: `strategy_action_items`
Actionable tasks generated during the review.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `review_id`: `UUID` (FK referencing `career_strategy_reviews.id`, ON DELETE CASCADE)
- `description`: `VARCHAR(255)`
- `difficulty`: `VARCHAR(50)` (e.g., "EASY", "MODERATE", "HARD")
- `status`: `VARCHAR(50)` (e.g., "TODO", "COMPLETED", "CANCELLED")
- `target_date`: `DATE` (Nullable)
- `completed_at`: `TIMESTAMP WITH TIME ZONE` (Nullable)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)

### Indexes & Migrations
- `idx_user_reviews`: Composite index on `(user_id, created_at)` for loading historical review timelines.
- `idx_action_items_review`: B-Tree index on `review_id` inside `strategy_action_items`.
- **Alembic Migration**: `create_career_strategy_reviews_tables.py` creating the schemas and tables.

---

## 5. API Endpoints

### `GET /api/v2/strategy/reviews`
Retrieves a user's strategy review history.
- **Authentication**: Required (JWT, Scope: `user`)
- **Response (200 OK)**:
```json
{
  "reviews": [
    {
      "id": "e2f3a4b5-6c7d-8e9f-0123-456789abcdef",
      "created_at": "2026-06-01T09:00:00Z",
      "status": "COMPLETED",
      "health_score_start": 72.0,
      "health_score_end": 75.5,
      "completed_at": "2026-06-02T18:00:00Z"
    }
  ]
}
```

### `GET /api/v2/strategy/reviews/{id}`
Returns details of a specific strategy review.
- **Authentication**: Required (JWT, Scope: `user`)
- **Path Parameters**:
  - `id`: `UUID` (Review ID)
- **Response (200 OK)**:
```json
{
  "id": "e2f3a4b5-6c7d-8e9f-0123-456789abcdef",
  "status": "PENDING_REVIEW",
  "goals": {
    "target_role": "AI Platform Engineer",
    "timeline_months": 12
  },
  "metrics": {
    "health_score_start": 75.5,
    "current_health_score": 75.5
  },
  "insights_summary": "Your career health score is stable. You resolved your Kubernetes skill gap. To reach your target role of AI Platform Engineer, we suggest focusing on agent architectures.",
  "action_items": [
    {
      "id": "fa12bc34-de56-78fg-90hi-jklmnopqrstuv",
      "description": "Learn LangGraph and build a multi-agent prototype.",
      "difficulty": "MODERATE",
      "status": "TODO",
      "target_date": "2026-07-01"
    }
  ]
}
```

### `POST /api/v2/strategy/reviews/{id}/complete`
Completes a review and saves candidate feedback.
- **Authentication**: Required (JWT, Scope: `user`)
- **Path Parameters**:
  - `id`: `UUID` (Review ID)
- **Request Payload**:
```json
{
  "feedback_text": "I agree with these suggestions; I will prioritize LangGraph learning.",
  "accept_action_items": true
}
```
- **Response (200 OK)**:
```json
{
  "id": "e2f3a4b5-6c7d-8e9f-0123-456789abcdef",
  "status": "COMPLETED",
  "completed_at": "2026-06-09T02:04:18Z"
}
```

### `PATCH /api/v2/strategy/reviews/action-items/{id}`
Updates the status of a specific action item.
- **Authentication**: Required (JWT, Scope: `user`)
- **Path Parameters**:
  - `id`: `UUID` (Action Item ID)
- **Request Payload**:
```json
{
  "status": "COMPLETED"
}
```
- **Response (200 OK)**:
```json
{
  "id": "fa12bc34-de56-78fg-90hi-jklmnopqrstuv",
  "status": "COMPLETED",
  "completed_at": "2026-06-09T02:04:18Z"
}
```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime, date
from typing import List, Optional

class ActionItem(BaseModel):
    id: UUID
    description: str
    difficulty: str
    status: str
    target_date: Optional[date] = None

class StrategyReviewDetail(BaseModel):
    id: UUID
    status: str
    goals_snapshot: dict
    health_score_start: float
    health_score_end: float
    insights_summary: str
    action_items: List[ActionItem]
    created_at: datetime
    completed_at: Optional[datetime] = None

class CompleteReviewRequest(BaseModel):
    feedback_text: Optional[str] = None
    accept_action_items: bool = True
```

---

## 7. Services

### `StrategyReviewOrchestrator`
Triggers and coordinates monthly strategy reviews.
- `initiate_review(user_id: UUID) -> UUID`: Runs a Temporal workflow that retrieves user details and runs the LangGraph review engine.
- `save_review_outputs(review_id: UUID, insights: str, items: list[dict]) -> None`: Saves generated recommendations and sets the status to pending.

### `StrategyHistoryTracker`
Assesses progress on historical goals.
- `evaluate_previous_review(user_id: UUID) -> dict`: Compares the status of action items from the previous month and generates a completion score.

---

## 8. Events

### Event: `strategy.review.initiated`
- **Producer**: `StrategyReviewOrchestrator`
- **Consumer**: `notification-service`
- **Payload Schema**:
```json
{
  "event_id": "i7j8k9l0-1m2n-3o4p-5q6r-7s8t9u0v1w2x",
  "event_type": "strategy.review.initiated",
  "timestamp": "2026-06-09T03:00:00Z",
  "payload": {
    "review_id": "e2f3a4b5-6c7d-8e9f-0123-456789abcdef",
    "user_id": "8f8e1234-a56b-4c7d-8e9f-0123456789ab"
  }
}
```

### Event: `strategy.review.completed`
- **Producer**: `StrategyReviewOrchestrator`
- **Consumer**: `observability-service`, `digest-worker`
- **Payload Schema**:
```json
{
  "event_id": "j8k9l0m1-2n3o-4p5q-6r7s-8t9u0v1w2x3y",
  "event_type": "strategy.review.completed",
  "timestamp": "2026-06-09T03:05:00Z",
  "payload": {
    "review_id": "e2f3a4b5-6c7d-8e9f-0123-456789abcdef",
    "user_id": "8f8e1234-a56b-4c7d-8e9f-0123456789ab",
    "health_score_delta": 3.5
  }
}
```

---

## 9. Background Jobs
- **`scheduled_monthly_review_trigger_job`**: Runs on a monthly schedule. Initiates a Temporal workflow to generate strategy reviews for active users.

---

## 10. Acceptance Criteria

### Review Generation Scenario
- **Given**: A candidate has been active on the platform for 30 days.
- **When**: The `scheduled_monthly_review_trigger_job` executes.
- **Then**: The system initiates a strategy review, generates next steps, changes the status to `PENDING_REVIEW`, and alerts the user.

### Action Item Roll-Over Scenario
- **Given**: A user has an unfinished action item from their previous review.
- **When**: The next monthly review is generated.
- **Then**: The history tracker carries the unfinished task over to the new review.

---

## 11. Edge Cases
- **No User Activity**: If a user has not logged in or updated their profile, the review should focus on encouraging them to complete basic steps rather than attempting to generate advanced recommendations.
- **Agent Schema Failures**: If the LangGraph output does not match the expected JSON structure, fail the workflow run and alert operators to prevent unformatted advice from being sent.
- **User Disables Reviews**: If a user opts out of monthly strategic reviews, disable the scheduler task for their ID.

---

## 12. Test Requirements
- **Orchestration Test**: Verify that the review generation workflow executes and populates the database correctly.
- **Schema Validation Test**: Test that the system flags and rejects malformed recommendations.

---

## 13. Dependencies
- **Direct Blockers**:
  - [Supervisor Agent (F3.2)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
  - [Intelligence Agent (F3.4)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
  - [Interaction Memory (F3.5)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
  - [Temporal Infrastructure (F4.1)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
