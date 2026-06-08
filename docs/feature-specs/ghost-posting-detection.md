# Feature Specification: Ghost Posting Detection (F2.5)

## 1. Purpose
The `Ghost Posting Detection` feature analyzes job postings to identify "ghost postings"—job advertisements kept active on boards indefinitely with no real intent to hire. By analyzing posting age, modification frequency, cohort interview feedback, and company hiring velocity, this service flags suspect jobs, preventing candidates from wasting effort on dead-end applications.

---

## 2. User Value
Applying to jobs is time-consuming and emotionally taxing. Up to 30% of active tech listings on aggregate job boards are estimated to be ghost postings, leading to high rejection or ghosting rates regardless of candidate fit. 
By identifying these listings and excluding them from recommendations (or clearly labeling them with a "Ghost Posting Warning"), CareerPilot protects candidate focus. 
Within the **Career Intelligence Compounding Loop** (outlined in [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md)), this maximizes the platform's North Star metric: the **interview conversion rate**, by directing applications exclusively to active, open hiring pipelines.

---

## 3. Requirements
- **Ghost Posting Signal Model**: Track indicators of inactive listings:
  - **Job Age**: Duration the listing has remained active.
  - **Re-posting Frequency**: How often the job is taken down and re-posted with identical text to reset the posting date.
  - **Company Hiring Velocity Correlation**: Is the company's overall hiring velocity declining while the posting count remains high?
  - **Outcome/Interview Conversion Data**: Have users in the cohort applied to this job or company recently and reported response rates?
- **Ghost Score Computation**: Generate a score (0.0 to 100.0) using a weighted algorithm:
  $$\text{Ghost Score} = (S_{\text{age}} \times 0.3) + (S_{\text{velocity\_mismatch}} \times 0.3) + (S_{\text{repost\_freq}} \times 0.2) + (S_{\text{cohort\_response\_rate}} \times 0.2)$$
  A posting with a score above 70.0 is flagged as a ghost posting.
- **Ghost Posting Database Schema**: Store the calculated scores, constituent signals, and generated explanations.
- **Ghost Posting APIs**: Endpoints to retrieve analysis reports for a specific job ID and query active ghost-flagged roles.
- **Ghost Score Explanation Generator**: Construct human-readable evidence strings (e.g., "This job has been open for 142 days; Stripe's overall hiring has slowed by 30% this month; no interviews have been recorded for this listing in 90 days.").
- **Evaluation Dataset**: A curated training set of 200 labeled listings (100 confirmed active hires, 100 known evergreen/ghost postings).
- **Monitoring Metrics**: Expose Prometheus gauges tracking total flagged ghost postings, average age of listings, and user override requests.

---

## 4. Database Changes

Maintains data audit rows linked directly to primary job posting tables.

### Schema Definitions

#### Table: `ghost_posting_signals`
Stores the detailed signal computation data for each active job evaluation.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `job_posting_id`: `UUID` (FK referencing `job_postings.id`, ON DELETE CASCADE, Unique)
- `ghost_score`: `DECIMAL(5, 2)` (0.00 to 100.00, Indexed)
- `is_flagged_ghost`: `BOOLEAN` (default `false`, Indexed)
- `age_days`: `INTEGER`
- `repost_count`: `INTEGER` (default `0`)
- `company_velocity_ratio`: `DECIMAL(4, 2)` (Ratio of current company postings to historic average)
- `cohort_applications`: `INTEGER` (Number of platform applications tracked)
- `cohort_interviews`: `INTEGER` (Number of interviews reported)
- `explanation`: `TEXT` (Human-readable rationale)
- `computed_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)

#### Table Alterations: `job_postings`
Integrate simple fields for fast index querying:
- `is_ghost_posting`: `BOOLEAN` (default `false`, Indexed)
- `ghost_score`: `DECIMAL(5, 2)` (default `0.00`)

### Indexes & Migrations
- `idx_ghost_signals_job_lookup`: Unique B-Tree index on `job_posting_id` inside `ghost_posting_signals`.
- `idx_job_postings_ghost_flag`: Combined index on `(is_ghost_posting, ghost_score)` to facilitate exclusion filters.
- **Alembic Migration**: `create_ghost_posting_signals_table.py` executing database adjustments.

---

## 5. API Endpoints

### `GET /api/v2/market/opportunities/{id}/ghost-analysis`
Provides details on why a job was flagged or marked safe.
- **Authentication**: Required (JWT, Scope: `user`)
- **Path Parameters**:
  - `id`: `UUID` (Job Posting ID)
- **Response (200 OK)**:
```json
{
  "job_posting_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3g4h5i6j",
  "ghost_score": 78.5,
  "is_flagged_ghost": true,
  "signals": {
    "age_days": 134,
    "repost_count": 3,
    "company_velocity_direction": "DECLINING",
    "cohort_stats": {
      "total_applications": 12,
      "total_interviews": 0,
      "response_rate": 0.0
    }
  },
  "explanation": "This position has been open for 134 days. No interviews have been recorded for this listing, and Acme Corp has reduced active job openings by 45% over the past 30 days.",
  "computed_at": "2026-06-09T01:30:00Z"
}
```

### `GET /api/v2/market/ghost-postings`
Queries active listings flagged as ghost postings. Used primarily in admin monitoring dashboards.
- **Authentication**: Required (JWT, Scope: `admin` or `operator`)
- **Query Parameters**:
  - `min_score`: `INTEGER` (default 70)
  - `limit`: `INTEGER` (default 50)
- **Response (200 OK)**:
```json
{
  "ghost_postings": [
    {
      "job_posting_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3g4h5i6j",
      "title": "Senior Solutions Engineer",
      "company_name": "Acme Corp",
      "ghost_score": 78.5,
      "flagged_at": "2026-06-09T01:30:00Z"
    }
  ]
}
```

### `POST /api/v2/market/ghost-postings/{id}/override`
Allows admins or moderators to manually override the system's ghost flag.
- **Authentication**: Required (JWT, Scope: `admin` or `operator`)
- **Path Parameters**:
  - `id`: `UUID` (Job Posting ID)
- **Request Payload**:
```json
{
  "override_ghost_flag": false,
  "reason": "Verified active hiring process with internal recruiter contact."
}
```
- **Response (200 OK)**:
```json
{
  "job_posting_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3g4h5i6j",
  "is_ghost_posting": false,
  "ghost_score": 0.0,
  "override_applied": true,
  "updated_at": "2026-06-09T02:04:18Z"
}
```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Dict, Any

class CohortStats(BaseModel):
    total_applications: int
    total_interviews: int
    response_rate: float = Field(..., ge=0.0, le=1.0)

class GhostSignalDetails(BaseModel):
    age_days: int
    repost_count: int
    company_velocity_direction: str
    cohort_stats: CohortStats

class GhostPostingAnalysis(BaseModel):
    job_posting_id: UUID
    ghost_score: float = Field(..., ge=0.0, le=100.0)
    is_flagged_ghost: bool
    signals: GhostSignalDetails
    explanation: str
    computed_at: datetime

class GhostOverrideRequest(BaseModel):
    override_ghost_flag: bool
    reason: str = Field(..., min_length=10)
```

---

## 7. Services

### `GhostPostingDetectorService`
Runs the pipeline to compute scores and update tables.
- `evaluate_posting(job_id: UUID) -> GhostPostingAnalysis`: Gathers age data, repost records, company velocities, and cohort application results, computes the weighted score, and writes to `ghost_posting_signals`.
- `apply_admin_override(job_id: UUID, override: bool, reason: str) -> None`: Applies manual status updates and logs the override transaction.

### `SignalAnalysisEngine`
Utility engine calculating scoring parameters.
- `calculate_age_score(posted_date: datetime) -> float`: Returns score based on age thresholds (e.g., > 60 days = 50 points, > 120 days = 100 points).
- `analyze_repost_patterns(fingerprint: str) -> int`: Queries historical postings with matching deduplication fingerprints to find re-posting count.
- `evaluate_cohort_feedback(company_id: UUID, job_id: UUID) -> dict`: Queries the [Outcome Memory System (F4.6)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md) to evaluate real candidate conversions.

---

## 8. Events

### Event: `market.job.ghost_score_computed`
- **Producer**: `GhostPostingDetectorService`
- **Consumer**: `intelligence-synthesis-service`
- **Payload Schema**:
```json
{
  "event_id": "9d8e7f6a-5b4c-3d2e-1f0a-9b8c7d6e5f4a",
  "event_type": "market.job.ghost_score_computed",
  "timestamp": "2026-06-09T01:30:00Z",
  "payload": {
    "job_posting_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3g4h5i6j",
    "ghost_score": 78.5,
    "is_flagged_ghost": true
  }
}
```

### Event: `market.job.ghost_flagged`
- **Producer**: `GhostPostingDetectorService`
- **Consumer**: `notification-service`, `search-index-worker`
- **Payload Schema**:
```json
{
  "event_id": "0a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
  "event_type": "market.job.ghost_flagged",
  "timestamp": "2026-06-09T01:30:01Z",
  "payload": {
    "job_posting_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3g4h5i6j",
    "company_name": "Acme Corp",
    "title": "Senior Solutions Engineer"
  }
}
```

---

## 9. Background Jobs
- **`scheduled_ghost_detection_job`**: Runs daily. Iterates over active postings in `job_postings`, calculates scores, and flags jobs with scores exceeding the 70.0 threshold.
- **`scheduled_cohort_outcome_correlation_job`**: Runs weekly. Gathers outcome feedback metrics from the [Outcome Memory System (F4.6)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md) and triggers re-evaluations for affected companies.

---

## 10. Acceptance Criteria

### Auto-Flagging Ghost Posting Scenario
- **Given**: A job posting for "Senior Systems Engineer" at "Acme Corp" has been active for 150 days.
- **When**: The `scheduled_ghost_detection_job` executes.
- **Then**: The score computes to 78.5, the job status `is_ghost_posting` is updated to `true`, and the system publishes the `market.job.ghost_flagged` event.

### General Pool Exclusion Scenario
- **Given**: A general pool job posting for "Software Engineer" at "Google" has been active for 180 days.
- **When**: The scoring algorithm runs.
- **Then**: It observes Stripe/Google size is large ("10000+"), identifies the role as an evergreen portal, reduces the age penalty weight, evaluates the ghost score under 70.0, and leaves the job marked as active.

---

## 11. Edge Cases
- **Evergreen General Openings**: Large enterprise companies maintain open links to collect resumes. The system must verify company size and whitelist general postings to avoid flagging valid entry points.
- **Scraper Failure**: If the crawler fails to capture the correct posting date, it might default to the ingestion timestamp, skewing age calculations. The system must fallback to checking company velocity ratios rather than relying solely on age.
- **Aggressive Re-posting**: If a company generates unique URLs daily for the same job, the similarity engine must recognize matching fingerprints to track true posting age.

---

## 12. Test Requirements
- **Verification Against Labeled Dataset**: Run evaluation tests comparing system flags to the labeled dataset. System must achieve **> 85% Accuracy** in classifying ghost vs. active roles.
- **Unit Test Signal Weighting**: Verify that variations in single signals (e.g., changing only cohort response rate) change scores correctly based on weights.

---

## 13. Dependencies
- **Direct Blockers**:
  - [Multi-Source Job Ingestion (F2.1)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/multi-source-job-ingestion.md)
  - [Company Intelligence (F2.4)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/company-intelligence.md)
- **Downstream Beneficiaries**:
  - [Opportunity Intelligence (F2.7)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/opportunity-intelligence.md)
  - [Research Agent (F3.3)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
