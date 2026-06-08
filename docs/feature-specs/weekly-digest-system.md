# Feature Specification: Weekly Digest System (F7.3)

## 1. Purpose
The `Weekly Digest System` generates and sends personalized weekly updates summarizing career health changes, market trends, position delta progress, and recommended opportunities. Managed via Temporal workflows, it gathers data snapshots for each user and delivers them via email or push notifications.

---

## 2. User Value
Most professionals manage their careers reactively and only look at the market during a job search. 
The Weekly Digest System keeps users informed about their career status in the background, providing regular updates on their market value and skill trajectory. 
In the **Career Intelligence Compounding Loop** (from [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md)), this feature serves as the primary touchpoint that brings passive users back to the dashboard, prompting them to address skill gaps and track their progress.

---

## 3. Requirements
- **Digest Database Schema**: Store historical digests, delivery statuses, open rates, and click tracking metrics.
- **Digest Generation Workflow**: Build a Temporal workflow that runs weekly, queries active user profiles, and generates personalized updates.
- **Section Generation**:
  - **Career Health Score**: Show current health score and the week-over-week change.
  - **Market Insights**: Highlight trending skills, compensation changes, and company hiring alerts.
  - **Position Delta Progress**: Show resolved skill gaps and target requirements.
  - **Recommended Opportunities**: Highlight top job matches.
- **Digest Delivery Service**: Integrate with email APIs (e.g., SendGrid, AWS SES) to format and deliver HTML digests.
- **Digest Preferences API**: Allow users to toggle digests, select their delivery day, and configure content sections.
- **Digest Analytics**: Track email delivery, open rates, and link click metrics.
- **Monitoring**: Track worker queues and delivery failure rates.

---

## 4. Database Changes

Requires a table to store digests and extensions to the user preferences table.

### Schema Definitions

#### Table: `user_digests`
Stores generated digests and delivery records.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `user_id`: `UUID` (FK referencing `users.id`, ON DELETE CASCADE)
- `sent_at`: `TIMESTAMP WITH TIME ZONE` (Nullable)
- `health_score_snapshot`: `JSONB` (Stores `{"score": 75.0, "delta": 1.2}`)
- `market_insight_summary`: `TEXT`
- `position_delta_snapshot`: `JSONB` (Stores `{"resolved": ["Docker"], "gaps": ["LangGraph"]}`)
- `recommendations_snapshot`: `JSONB` (List of recommended job IDs and titles)
- `delivery_status`: `VARCHAR(50)` (e.g., "GENERATED", "QUEUED", "SENT", "FAILED", "BOUNCED")
- `opened_at`: `TIMESTAMP WITH TIME ZONE` (Nullable)
- `clicked_at`: `TIMESTAMP WITH TIME ZONE` (Nullable)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)

#### Table Alterations: `user_preferences` (or equivalent preferences table)
Add digest delivery settings:
- `weekly_digest_enabled`: `BOOLEAN` (default `true`)
- `digest_delivery_day`: `INTEGER` (0-6, where 0 is Sunday, default `1`)
- `digest_delivery_hour`: `INTEGER` (0-23, default `9`)

### Indexes & Migrations
- `idx_user_digests_lookup`: Composite index on `(user_id, created_at)` to fetch user digest history.
- `idx_digest_delivery_queue`: Composite index on `(delivery_status, created_at)` for workers tracking outgoing queues.
- **Alembic Migration**: `create_weekly_digest_tables.py` creating the tables and preferences adjustments.

---

## 5. API Endpoints

### `GET /api/v2/strategy/digests`
Retrieves a user's digest history.
- **Authentication**: Required (JWT, Scope: `user`)
- **Response (200 OK)**:
```json
{
  "digests": [
    {
      "id": "ab12cd34-ef56-78gh-90ij-klmnopqrstuv",
      "sent_at": "2026-06-08T09:00:00Z",
      "health_score": { "score": 75.0, "delta": 1.2 },
      "delivery_status": "SENT"
    }
  ]
}
```

### `GET /api/v2/strategy/digests/{id}`
Returns details of a specific digest.
- **Authentication**: Required (JWT, Scope: `user`)
- **Path Parameters**:
  - `id`: `UUID` (Digest ID)
- **Response (200 OK)**:
```json
{
  "id": "ab12cd34-ef56-78gh-90ij-klmnopqrstuv",
  "sent_at": "2026-06-08T09:00:00Z",
  "content": {
    "health_score": {
      "score": 75.0,
      "delta": 1.2,
      "primary_insight": "Your score increased because you added Docker to your profile."
    },
    "market_insights": "Kubernetes demand has grown by 12% in your target region this week.",
    "position_delta": {
      "resolved_gaps": ["Docker"],
      "remaining_gaps": ["LangGraph"]
    },
    "recommendations": [
      {
        "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3g4h5i6j",
        "title": "Backend Engineer",
        "company_name": "Stripe"
      }
    ]
  }
}
```

### `PATCH /api/v2/profile/preferences`
Updates user delivery settings.
- **Authentication**: Required (JWT, Scope: `user`)
- **Request Payload**:
```json
{
  "weekly_digest_enabled": true,
  "digest_delivery_day": 1,
  "digest_delivery_hour": 8
}
```
- **Response (200 OK)**:
```json
{
  "weekly_digest_enabled": true,
  "digest_delivery_day": 1,
  "digest_delivery_hour": 8,
  "updated_at": "2026-06-09T02:04:18Z"
}
```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class HealthScoreDigest(BaseModel):
    score: float
    delta: float
    primary_insight: str

class DeltaDigest(BaseModel):
    resolved_gaps: List[str]
    remaining_gaps: List[str]

class RecommendationBrief(BaseModel):
    id: UUID
    title: str
    company_name: str

class DigestContent(BaseModel):
    health_score: HealthScoreDigest
    market_insights: str
    position_delta: DeltaDigest
    recommendations: List[RecommendationBrief]

class UserDigestDetails(BaseModel):
    id: UUID
    sent_at: Optional[datetime] = None
    content: DigestContent
    delivery_status: str
```

---

## 7. Services

### `DigestGenerationService`
Compiles user career updates.
- `generate_digest(user_id: UUID) -> DigestContent`: Queries user dashboards and recommendation engines to compile weekly updates.
- `render_html_template(content: DigestContent) -> str`: Compiles content into an HTML email template.

### `DigestDeliveryService`
Sends outgoing updates.
- `queue_digests() -> list[UUID]`: Identifies users scheduled for updates and queues them.
- `send_digest_email(digest_id: UUID) -> bool`: Sends HTML templates via email APIs and records delivery status.

### `DigestAnalyticsTracker`
Tracks delivery performance.
- `track_open(digest_id: UUID) -> None`: Updates `opened_at` timestamps.
- `track_click(digest_id: UUID) -> None`: Updates `clicked_at` timestamps.

---

## 8. Events

### Event: `strategy.digest.generated`
- **Producer**: `DigestGenerationService`
- **Consumer**: `observability-service`
- **Payload Schema**:
```json
{
  "event_id": "g5h6i7j8-9k0l-1m2n-3o4p-5q6r7s8t9u0v",
  "event_type": "strategy.digest.generated",
  "timestamp": "2026-06-09T03:00:00Z",
  "payload": {
    "digest_id": "ab12cd34-ef56-78gh-90ij-klmnopqrstuv",
    "user_id": "8f8e1234-a56b-4c7d-8e9f-0123456789ab"
  }
}
```

### Event: `strategy.digest.sent`
- **Producer**: `DigestDeliveryService`
- **Consumer**: `observability-service`
- **Payload Schema**:
```json
{
  "event_id": "h6i7j8k9-0l1m-2n3o-4p5q-6r7s8t9u0v1w",
  "event_type": "strategy.digest.sent",
  "timestamp": "2026-06-09T03:05:00Z",
  "payload": {
    "digest_id": "ab12cd34-ef56-78gh-90ij-klmnopqrstuv",
    "user_id": "8f8e1234-a56b-4c7d-8e9f-0123456789ab",
    "delivery_status": "SENT"
  }
}
```

---

## 9. Background Jobs
- **`weekly_digest_scheduler`**: Run daily. Scans user delivery settings and starts a Temporal workflow to process scheduled updates.
- **`digest_delivery_retry_worker`**: hourly job that retries failed deliveries using exponential backoff.

---

## 10. Acceptance Criteria

### Workflow Execution Scenario
- **Given**: A user has enabled weekly digests for Monday at 8 AM.
- **When**: The Temporal schedule executes on Monday morning.
- **Then**: The workflow generates a digest record, compiles user profile and recommendations data, and successfully delivers the email.

### Toggle Off Scenario
- **Given**: A user disables weekly digests.
- **When**: The weekly scheduler runs.
- **Then**: The system skips digest generation for this user.

---

## 11. Edge Cases
- **Bounces and Unsubscribes**: If the email client reports a hard bounce or spam complaint, immediately set `weekly_digest_enabled` to `false` in user preferences and alert the user.
- **Empty Updates**: If a user has no new recommendations or score changes, the system should generate a general market update rather than leaving sections empty.
- **High Traffic Volumes**: To prevent email delivery limits from being hit, the scheduler should batch delivery jobs throughout the configured hour.

---

## 12. Test Requirements
- **Template Render Test**: Verify that the HTML renderer handles custom characters and generates valid email templates.
- **Delivery Status Test**: Test delivery error scenarios (API keys invalid, rate limits exceeded) to ensure failures are caught and retried.

---

## 13. Dependencies
- **Direct Blockers**:
  - [Career Dashboard (F1.9)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
  - [Temporal Infrastructure (F4.1)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
