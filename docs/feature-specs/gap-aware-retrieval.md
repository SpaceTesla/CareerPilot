# Feature Specification: Gap-Aware Retrieval (F7.2)

## 1. Purpose
The `Gap-Aware Retrieval` feature extends the system's [Hybrid Retrieval (F3.6)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md) pipeline (BM25 + Qdrant vector search + reranking) by incorporating Neo4j graph relationships. Instead of matching candidates only to roles that match their current skills exactly, it identifies and scores "adjacent" opportunities—roles where the candidate has a small, addressable skill gap but is otherwise highly aligned.

---

## 2. User Value
Traditional search engines only match candidates to roles where they meet 100% of the requirements, which restricts their career progression. 
Gap-Aware Retrieval matches candidates with aspirational roles that are within reach, identifying bridge skills (e.g., "This role is a 85% match. You have the backend skills, and adding LangGraph would make you a fit"). 
In the **Career Intelligence Compounding Loop** (outlined in [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md)), this feature drives professional growth by showing users the exact next steps they need to take to qualify for higher-level opportunities.

---

## 3. Requirements
- **Adjacent Opportunity Model**: Define logical criteria for role adjacency (e.g., a role is adjacent if the candidate has the required core experience and lacks at most 2 addressable skills).
- **Cluster Adjacency Engine**: Map related skills (e.g., if a candidate knows "PyTorch", "TensorFlow" is considered an adjacent skill, requiring less effort to learn than a completely new language).
- **Graph-Based Traversal**: Query Neo4j to find roles that require adjacent skills and identify the bridge skills needed to transition.
- **Adjacent Opportunity Scoring**: Adjust fit scores for adjacent roles. The penalty for missing skills is scaled by how easily the candidate can learn them based on their current background.
- **Recommendation Explanation Generator**: Generate text explaining adjacent match scoring (e.g., "Adjacent Match: This role requires Go (adjacent to your Python experience). You possess all other infrastructure requirements.").
- **Retrieval APIs**: API endpoints to retrieve adjacent opportunities.
- **Retrieval Evaluations**: Run benchmark tests to evaluate adjacent retrieval accuracy (precision at 5/10) against candidate expectations.

---

## 4. Database Changes

Logs queries to monitor performance and tracks user feedback on adjacent matches.

### Schema Definitions

#### Table: `gap_retrieval_logs`
Logs retrieval operations to audit pipeline accuracy and latency.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `user_id`: `UUID` (FK referencing `users.id`, ON DELETE CASCADE)
- `query_vector_id`: `VARCHAR(255)` (Qdrant query vector reference, Nullable)
- `postgres_query_string`: `TEXT` (Nullable)
- `adjacent_results_count`: `INTEGER` (Number of adjacent roles returned)
- `user_feedback_score`: `INTEGER` (User rating, 1 to 5 stars, Nullable)
- `pipeline_duration_ms`: `INTEGER`
- `created_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)

### Neo4j Cypher Query Pattern
```cypher
// Query to retrieve adjacent roles and identify missing bridge skills
MATCH (p:CandidateProfile {profile_id: $profile_id})-[h:HAS_SKILL]->(s:Skill)
WITH p, collect(s.canonical_name) as user_skills
MATCH (j:JobPosting) WHERE j.status = 'ACTIVE'
MATCH (j)-[r:REQUIRES_SKILL]->(js:Skill)
WITH j, user_skills, collect(js.canonical_name) as job_skills
// Find missing skills
WITH j, [x IN job_skills WHERE NOT x IN user_skills] as missing_skills, job_skills
// Filter to roles where the candidate lacks at most 2 skills
WHERE size(missing_skills) <= 2 AND size(missing_skills) > 0
RETURN j.id as job_posting_id, j.title as title, missing_skills, size(job_skills) as total_skills_count;
```

### Indexes & Migrations
- `idx_gap_logs_user`: B-Tree index on `user_id` inside `gap_retrieval_logs`.
- **Alembic Migration**: `create_gap_retrieval_logs_table.py` executing database changes.

---

## 5. API Endpoints

### `GET /api/v2/market/retrieval/adjacent`
Retrieves adjacent opportunities for the user.
- **Authentication**: Required (JWT, Scope: `user`)
- **Query Parameters**:
  - `limit`: `INTEGER` (default 10)
  - `max_gaps`: `INTEGER` (Allowed missing skills limit, default 2)
- **Response (200 OK)**:
```json
{
  "user_id": "8f8e1234-a56b-4c7d-8e9f-0123456789ab",
  "results": [
    {
      "job_posting": {
        "id": "7a8b9c0d-1e2f-3g4h-5i6j-7k8l9m0n1o2p",
        "title": "AI Platform Engineer",
        "company_name": "Acme Corp",
        "location": "San Francisco, CA"
      },
      "fit_score": 84.5,
      "addressable_gaps": [
        {
          "skill_name": "LangGraph",
          "difficulty_estimate": "EASY",
          "estimated_learning_hours": 12,
          "reason": "You have experience with Python and other agent frameworks."
        }
      ],
      "explanation": "84% Match. You possess all core infrastructure skills. Adding LangGraph (estimated 12 hours of learning) makes you a strong candidate for this role."
    }
  ]
}
```

### `GET /api/v2/market/retrieval/gap-analysis`
Provides a breakdown of missing skills and learning paths for a target job posting.
- **Authentication**: Required (JWT, Scope: `user`)
- **Query Parameters**:
  - `job_posting_id`: `UUID` (Required)
- **Response (200 OK)**:
```json
{
  "job_posting_id": "7a8b9c0d-1e2f-3g4h-5i6j-7k8l9m0n1o2p",
  "overall_gap_level": "MODERATE",
  "missing_skills": [
    {
      "skill_name": "Kubernetes",
      "importance": "REQUIRED",
      "learning_path_suggestion": "Deploy a sample cluster using Minikube; learn Pod lifecycles and deployments."
    }
  ],
  "learning_time_estimate_hours": 30
}
```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class SkillGapEstimate(BaseModel):
    skill_name: str
    difficulty_estimate: str = Field(..., regex="^(EASY|MODERATE|HARD)$")
    estimated_learning_hours: int
    reason: str

class AdjacentOpportunity(BaseModel):
    job_posting: dict
    fit_score: float = Field(..., ge=0.0, le=100.0)
    addressable_gaps: List[SkillGapEstimate]
    explanation: str
```

---

## 7. Services

### `GapAwareRetrievalEngine`
Orchestrates search operations.
- `retrieve_adjacent_opportunities(user_id: UUID, limit: int = 10, max_gaps: int = 2) -> list[AdjacentOpportunity]`: Queries Neo4j for adjacent jobs, retrieves posting details, calculates adjusted fit scores, and returns sorted recommendations.
- `analyze_skill_gap(user_skills: list[str], job_skills: list[str]) -> list[SkillGapEstimate]`: Evaluates missing skills and estimates learning difficulty based on the candidate's existing background.

### `GapScoringService`
Calculates adjusted scores for adjacent roles.
- `calculate_adjusted_score(base_score: float, gaps: list[SkillGapEstimate]) -> float`: Deducts points for missing skills, scaling the penalty based on how easily the candidate can learn them (e.g., minor penalty for easy-to-learn skills, larger penalty for hard-to-learn skills).

---

## 8. Events

### Event: `retrieval.gap_aware_run_completed`
- **Producer**: `GapAwareRetrievalEngine`
- **Consumer**: `observability-service`
- **Payload Schema**:
```json
{
  "event_id": "f4g5h6i7-8j9k-0l1m-2n3o-4p5q6r7s8t9u",
  "event_type": "retrieval.gap_aware_run_completed",
  "timestamp": "2026-06-09T03:05:00Z",
  "payload": {
    "user_id": "8f8e1234-a56b-4c7d-8e9f-0123456789ab",
    "results_count": 5,
    "duration_ms": 145
  }
}
```

---

## 9. Background Jobs
- **`scheduled_gap_index_update_job`**: Runs weekly. Recomputes skill adjacency weights in the database based on global job posting trends.

---

## 10. Acceptance Criteria

### Bridge Skill Identification Scenario
- **Given**: A candidate has Python experience but lacks Go and LangGraph.
- **When**: The candidate runs a query for adjacent positions.
- **Then**: The search returns a "Go Backend Engineer" role requiring Go and LangGraph, flags Go as a moderate gap (due to candidate's Python background), and ranks the posting accordingly.

### Large Gap Penalty Scenario
- **Given**: A frontend developer profile lacks Python, PyTorch, and machine learning models.
- **When**: The candidate runs a query for adjacent positions.
- **Then**: The system filters out "Machine Learning Research Scientist" roles requiring these skills, as the gap exceeds the allowed threshold.

---

## 11. Edge Cases
- **Empty Candidate Profiles**: If a candidate has not listed any skills or experiences, the gap-aware search falls back to standard keyword recommendations and prompts the user to complete their profile.
- **Large Skill Gaps**: If a role requires 10 skills and the candidate only has 1, the matching engine must immediately filter it out to prevent irrelevant recommendations.
- **Out-of-Date Index**: If Neo4j has not synced recent Postgres updates, Cypher queries might return stale results. The system must verify matching IDs against PostgreSQL before returning recommendations.

---

## 12. Test Requirements
- **Pathfinder Accuracy Test**: Assert that traversal queries correctly identify missing skills against a mock database.
- **Gap Scoring Test**: Verify that score adjustments scale correctly based on learning difficulty.

---

## 13. Dependencies
- **Direct Blockers**:
  - [Knowledge Graph (F7.1)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/knowledge-graph.md)
  - [Hybrid Retrieval (F3.6)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
