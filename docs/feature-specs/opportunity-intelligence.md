# Feature Specification: Opportunity Intelligence (F2.7)

## 1. Purpose
The `Opportunity Intelligence` feature calculates a personalized fit score (0.0 to 100.0) between a candidate's career profile and active job postings. It integrates four components: skill matching, experience alignment, compensation fit, and company attractiveness. It ranks listings and generates detailed explanations for matching results.

---

## 2. User Value
Traditional job boards list postings chronologically or based on simple keyword matches, leaving candidates to parse descriptions and guess which roles fit their requirements. 
Opportunity Intelligence automates this by showing candidates their highest-probability targets first, complete with clear alignment rationales (e.g. "94% Fit: You possess 9 of 10 required skills; the company attractiveness score is high; the salary fits your target range."). 
In the **Career Intelligence Compounding Loop** (defined in [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md)), this is the primary recommendation system. It translates raw market data into actionable strategic targets.

---

## 3. Requirements
- **Opportunity Scoring Schema**: Data tables to store personalized scoring breakdowns, components, and explanations for candidate-job pairs.
- **Profile-Role Matching Engine**: Core component to evaluate a profile against a target role description and produce a composite match percentage.
- **Skill Fit Scoring**: Measure the overlap between user skills and job requirements, giving higher weight to skills labeled as "Required" by the NLP extraction engine.
- **Experience Fit Scoring**: Evaluate experience levels (e.g., comparing user years of experience and target seniority levels to prevent senior engineers from being matched with junior roles, and vice versa).
- **Compensation Fit Scoring**: Compare the user's target compensation from their career goals against the job's salary range or normalized company benchmark.
- **Company Attractiveness Integration**: Include the target company's Attractiveness Score (from F2.4) in the final fit calculation.
- **Scoring Weights**: Configurable component scoring:
  $$\text{Fit Score} = (S_{\text{skill}} \times 0.4) + (S_{\text{experience}} \times 0.2) + (S_{\text{compensation}} \times 0.2) + (S_{\text{company}} \times 0.2)$$
- **Ranking Pipeline**: Filter, score, and sort thousands of active jobs for each active user.
- **Opportunity Discovery API**: Endpoints to list and filter scored opportunities.
- **Ranking Explanations**: Auto-generate text explanations detailing fit scores.

---

## 4. Database Changes

Requires a table to store calculated scores and indices to support real-time sorting.

### Schema Definitions

#### Table: `opportunity_scores`
Stores calculated scoring components for candidate-job pairs.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `user_id`: `UUID` (FK referencing `users.id`, ON DELETE CASCADE)
- `job_posting_id`: `UUID` (FK referencing `job_postings.id`, ON DELETE CASCADE)
- `fit_score`: `DECIMAL(5, 2)` (0.00 to 100.00, Indexed)
- `skill_fit_score`: `DECIMAL(5, 2)`
- `experience_fit_score`: `DECIMAL(5, 2)`
- `compensation_fit_score`: `DECIMAL(5, 2)`
- `company_attractiveness_score`: `DECIMAL(5, 2)`
- `explanation_json`: `JSONB` (Stores evidence blocks: `{"missing_skills": ["Rust"], "salary_comparison": "exceeds_goal"}`)
- `computed_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)

### Indexes & Migrations
- `idx_user_opp_scores`: Unique index on `(user_id, job_posting_id)` to prevent duplicate entries and speed up queries.
- `idx_user_fit_score_sort`: Combined index on `(user_id, fit_score)` for fast sorting on user dashboards.
- **Alembic Migration**: `create_opportunity_scores_table.py` executing table creation.

---

## 5. API Endpoints

### `GET /api/v2/market/opportunities`
Returns a ranked list of job opportunities for the authenticated user.
- **Authentication**: Required (JWT, Scope: `user`)
- **Query Parameters**:
  - `min_score`: `INTEGER` (default 60)
  - `limit`: `INTEGER` (default 20)
  - `offset`: `INTEGER` (default 0)
- **Response (200 OK)**:
```json
{
  "user_id": "8f8e1234-a56b-4c7d-8e9f-0123456789ab",
  "opportunities": [
    {
      "opportunity_score_id": "ab12cd34-ef56-78gh-90ij-klmnopqrstuv",
      "job_posting": {
        "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3g4h5i6j",
        "title": "Senior Staff Backend Engineer",
        "company_name": "Stripe",
        "location": "San Francisco, CA",
        "salary_range": "$190,000 - $240,000"
      },
      "fit_score": 92.4,
      "breakdown": {
        "skill_fit": 95.0,
        "experience_fit": 90.0,
        "compensation_fit": 100.0,
        "company_attractiveness": 92.4
      },
      "explanation_summary": "92% match. You possess 8 of 9 required skills. The salary range of $190,000 - $240,000 matches your target, and Stripe is a high-growth employer with strong hiring velocity."
    }
  ]
}
```

### `GET /api/v2/market/opportunities/{id}`
Returns a detailed score breakdown for a specific opportunity.
- **Authentication**: Required (JWT, Scope: `user`)
- **Path Parameters**:
  - `id`: `UUID` (Opportunity Score ID or Job Posting ID)
- **Response (200 OK)**:
```json
{
  "opportunity_score_id": "ab12cd34-ef56-78gh-90ij-klmnopqrstuv",
  "job_posting_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3g4h5i6j",
  "fit_score": 92.4,
  "breakdown_details": {
    "skills": {
      "score": 95.0,
      "matching_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
      "missing_skills": ["LangGraph"],
      "missing_skills_importance": { "LangGraph": "Nice-to-Have" }
    },
    "experience": {
      "score": 90.0,
      "required_years": 5,
      "candidate_years": 6,
      "level_match": "MATCH"
    },
    "compensation": {
      "score": 100.0,
      "target_salary": 180000.00,
      "job_min_salary": 190000.00,
      "job_max_salary": 240000.00
    },
    "company": {
      "score": 92.4,
      "company_id": "e2f3a4b5-6c7d-8e9f-0123-456789abcdef",
      "company_name": "Stripe"
    }
  },
  "explanation_details": {
    "strengths": [
      "Highly aligned technical skillset.",
      "Compensation exceeds your minimum goal of $180,000."
    ],
    "gaps": [
      "Missing LangGraph experience (found in 40% of similar roles)."
    ]
  }
}
```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List, Dict, Optional

class ScoreComponents(BaseModel):
    skill_fit: float = Field(..., ge=0.0, le=100.0)
    experience_fit: float = Field(..., ge=0.0, le=100.0)
    compensation_fit: float = Field(..., ge=0.0, le=100.0)
    company_attractiveness: float = Field(..., ge=0.0, le=100.0)

class OpportunityBrief(BaseModel):
    id: UUID
    title: str
    company_name: str
    location: str
    salary_range: str

class ScoredOpportunity(BaseModel):
    opportunity_score_id: UUID
    job_posting: OpportunityBrief
    fit_score: float = Field(..., ge=0.0, le=100.0)
    breakdown: ScoreComponents
    explanation_summary: str
```

---

## 7. Services

### `OpportunityScoringEngine`
Calculates scores and component metrics.
- `compute_scores(user_id: UUID, job_id: UUID) -> OpportunityScoreBreakdown`: Retrieves profile data and job details, computes scoring component values, and applies weights.
- `generate_explanation(breakdown: dict) -> str`: Compiles score evidence into readable text segments.

### `OpportunityRankingService`
Updates lists of scored roles.
- `refresh_user_opportunities(user_id: UUID) -> None`: Scans active jobs, calculates new scores, updates the database, and flags matches exceeding the target score.
- `get_top_opportunities(user_id: UUID, limit: int, offset: int) -> list[ScoredOpportunity]`: Queries `opportunity_scores` sorted by fit score.

---

## 8. Events

### Event: `synthesis.opportunity_scored`
- **Producer**: `OpportunityScoringEngine`
- **Consumer**: `dashboard-service`, `notification-service`
- **Payload Schema**:
```json
{
  "event_id": "cd12ef34-gh56-ij78-kl90-mnopqurstuvw",
  "event_type": "synthesis.opportunity_scored",
  "timestamp": "2026-06-09T02:00:00Z",
  "payload": {
    "user_id": "8f8e1234-a56b-4c7d-8e9f-0123456789ab",
    "job_posting_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3g4h5i6j",
    "fit_score": 92.4
  }
}
```

---

## 9. Background Jobs
- **`scheduled_opportunity_scoring_refresh_job`**: Runs nightly. Calculates fit scores for all active users against new job listings, updating `opportunity_scores`.
- **`stale_scores_cleanup_job`**: Weekly job that purges scores for closed or expired job postings.

---

## 10. Acceptance Criteria

### Scoring Process Scenario
- **Given**: A user profile lists "Python", "FastAPI", and 5 years experience, with a salary goal of $150,000.
- **When**: A job posting is added requiring "Python", "FastAPI", 5 years experience, and offering $160,000.
- **Then**: The fit score calculates above 90.0, an entry is added to `opportunity_scores`, and a `synthesis.opportunity_scored` event is emitted.

### Seniority Mismatch Scenario
- **Given**: A user has 2 years of experience.
- **When**: The matching engine evaluates a "Principal Engineer" role requiring 12+ years of experience.
- **Then**: The experience fit score drops to 0.0, dragging the composite fit score below the 60.0 threshold.

---

## 11. Edge Cases
- **No Compensation Info**: If a listing lacks salary details, query company benchmarks (from F2.6). If benchmarks are unavailable, set compensation fit score to a neutral default of 70.0 to avoid dragging down the composite score.
- **Target Role Changes**: If a user updates their career goals, delete previous scores and queue a job to recalculate matching scores against active listings.
- **Very Large Job Volume**: If active jobs exceed 50,000, pre-filter candidates using simple keyword queries before running full scoring calculations on matching subsets.

---

## 12. Test Requirements
- **Recalculation Testing**: Verify that updating a profile skill updates the fit score of affected job postings.
- **Load Test Ranking**: Test ranking performance with 1,000 users and 10,000 active jobs to ensure calculations complete within execution windows.

---

## 13. Dependencies
- **Direct Blockers**:
  - [Career Profile Domain (F1.3)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
  - [Company Intelligence (F2.4)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/company-intelligence.md)
  - [Compensation Intelligence (F2.6)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/compensation-intelligence.md)
- **Downstream Beneficiaries**:
  - [Intelligence Agent (F3.4)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
