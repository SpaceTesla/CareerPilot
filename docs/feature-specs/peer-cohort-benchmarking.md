# Feature Specification: Peer Cohort Benchmarking (F5.4)

## 1. Purpose
Peer Cohort Benchmarking is an analytical and ranking service designed to group CareerPilot users into anonymized, similar profile clusters (cohorts) based on education, experience level, skill vectors, and role targets. Rather than comparing users against a generic pool, this feature calculates a user's relative performance and compensation status against highly targeted peers. By running profile clustering algorithms (e.g., K-Means or DBSCAN) and aggregating data from the Outcome Memory System, it provides actionable insights like: "Your skill diversity places you in the 82nd percentile of your peer group, but your salary is in the 40th percentile, indicating negotiation leverage."

---

## 2. User Value
Peer Cohort Benchmarking provides users with concrete context regarding where they stand in the job market. Instead of relying on generic public salary sites, users see precise, outcome-backed metrics of peers with equivalent capabilities. This highlights gap-areas (e.g., "90% of peers in your cohort who transitioned to Staff Engineer possess Kubernetes certification, which you lack") and helps focus their profile and strategy updates to match top-performing peers.

---

## 3. Requirements
* **Peer Cohort Schema**: Define database models to store dynamic cohort metrics, user cohort memberships, and aggregate benchmark criteria.
* **Profile Clustering Pipeline**: Design a service that takes vector embeddings of user profiles (skills, title, experience) and executes K-Means clustering in scikit-learn.
* **Cohort Assignment**: Automatically assign new users to the closest cohort cluster centroid upon profile sync or modification.
* **Benchmark Aggregation**: Calculate cohort-level aggregates, including median salaries, average callback rates, top 10 skills, and interview-to-offer ratios.
* **Percentile Computation**: Implement math service to compute user percentiles across salary, skill count, experience years, and application success rates.
* **Cohort APIs**: Expose endpoints to query user standing, view anonymized cohort distributions, and fetch top skill gaps of the cohort.
* **Observability & Analytics**: Log clustering quality metrics (e.g., silhouette score) to track cluster cohesion.

---

## 4. Database Changes

### PostgreSQL Tables

#### `peer_cohorts`
Stores the definition and aggregate profile centroid characteristics of a cluster.
```sql
CREATE TABLE peer_cohorts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cohort_name VARCHAR(150) UNIQUE NOT NULL,
    cluster_centroid JSONB NOT NULL, -- core features matching the cluster center
    metrics_cache JSONB NOT NULL, -- median compensation, interview conversion velocity, etc.
    member_count INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
```

#### `cohort_memberships`
Maps individual users to cohorts and stores calculated percentile scores.
```sql
CREATE TABLE cohort_memberships (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    peer_cohort_id UUID NOT NULL REFERENCES peer_cohorts(id) ON DELETE CASCADE,
    salary_percentile NUMERIC(5, 2), -- value between 0.00 and 100.00
    skills_percentile NUMERIC(5, 2),
    outcome_velocity_percentile NUMERIC(5, 2),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_cohort_memberships_cohort ON cohort_memberships(peer_cohort_id);
```

### Alembic Migration Plan
1. Create `peer_cohorts` table to store aggregated cluster data.
2. Create `cohort_memberships` table mapping users to cohorts and indexing percentiles.
3. Hook up database trigger or application service to update member counts on change.

---

## 5. API Endpoints

### GET `/api/v1/cohorts/my-benchmark`
Retrieve the authenticated user's benchmark ranking relative to their peer group.
* **Response Body (200 OK)**:
  ```json
  {
    "user_id": "4a2b9c3d-1234-5678-9101-abcdef123456",
    "cohort_name": "Mid-Level Machine Learning Engineers (US-East)",
    "cohort_stats": {
      "total_peers": 420,
      "median_salary": 165000,
      "top_cohort_skills": ["Python", "PyTorch", "Kubernetes", "Docker", "FastAPI"]
    },
    "my_percentiles": {
      "salary": 45.20,
      "skills_count": 82.50,
      "interview_rate": 68.10
    },
    "actionable_gaps": [
      {
        "skill": "Kubernetes",
        "peer_adoption_rate": 0.73, -- 73% of peers in this cohort have this skill
        "priority": "high"
      }
    ]
  }
  ```

### POST `/api/v1/cohorts/recluster`
Force a clustering task run over the entire profile database (admin only).
* **Response Body (202 Accepted)**:
  ```json
  {
    "job_id": "job_cluster_9988",
    "status": "queued",
    "message": "User profile re-clustering pipeline initiated."
  }
  ```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from uuid import UUID

class CohortPeerGap(BaseModel):
    skill: str
    peer_adoption_rate: float = Field(ge=0.0, le=1.0)
    priority: str

class UserPercentiles(BaseModel):
    salary: float = Field(ge=0.0, le=100.0)
    skills_count: float = Field(ge=0.0, le=100.0)
    interview_rate: float = Field(ge=0.0, le=100.0)

class BenchmarkReport(BaseModel):
    user_id: UUID
    cohort_name: str
    member_count: int
    median_salary: float
    my_percentiles: UserPercentiles
    actionable_gaps: List[CohortPeerGap]
```

---

## 7. Services

### `PeerCohortBenchmarkingService`
* **Method**: `generate_cohorts() -> dict`
  * Pulls profile feature records from database. Standardizes features, fits a K-Means model (determining ideal cluster size `K` via Elbow method), writes new `peer_cohorts` records, and updates assignments.
* **Method**: `assign_user_to_cohort(user_id: UUID) -> UUID`
  * Calculates distance between user profile vector and existing cluster centroids. Updates `cohort_memberships` with closest cluster match and computes percentile metrics.
* **Method**: `get_benchmark_report(user_id: UUID) -> BenchmarkReport`
  * Fetches membership rows and dynamically compiles the benchmark report payload.

---

## 8. Events

### `cohort.assignment.updated`
* **Producer**: `PeerCohortBenchmarkingService`
* **Consumer**: `ObservabilityPlatform`, `InteractionMemory`
* **Payload**:
  ```json
  {
    "event_id": "evt_coh_assign_01",
    "timestamp": "2026-06-09T02:04:18Z",
    "user_id": "4a2b9c3d-1234-5678-9101-abcdef123456",
    "cohort_id": "9f8e7d6c-5b4a-3c2d-1e0f-998877665544",
    "cohort_name": "Mid-Level Machine Learning Engineers (US-East)"
  }
  ```

---

## 9. Background Jobs
* **Job Name**: `run_monthly_clustering_pipeline`
  * **Frequency**: Monthly on the 1st at 02:00 AM (`0 2 1 * *`)
  * **Payload**: None
  * **Logic**: Triggers `generate_cohorts()` service. Recalculates centroids based on new user registrations and modified profile records. Assigns users and recalculates percentiles.
  * **Retry Behavior**: Retry up to 3 times, with 10-minute backoffs.

---

## 10. Acceptance Criteria
* **AC 1**: Given an active user profile, when requesting their benchmark, they must see percentiles calculated against their assigned cohort (not the global user pool).
* **AC 2**: The clustering algorithm must enforce a silhouette score threshold of >= 0.35 to ensure distinct, meaningful user segments.
* **AC 3**: If a user is missing salary details or has an empty skill set, they must be assigned to a default, broad-category cohort centroid until their profile is updated.

---

## 11. Edge Cases
* **Small Cluster Size**: If a specialized cluster drops below 5 members, statistical calculations become non-anonymized. The service must automatically merge small clusters into a broader parent cohort to protect privacy.
* **Centroid Shift After Reclustering**: If a monthly re-clustering runs, user IDs might migrate to different cohort IDs. The service must implement transition mapping to update memberships smoothly without breaking dashboard states.
* **Vector Dimension Mismatch**: If the embedding model for profiles is upgraded, historical centroid coordinates will mismatch. The clustering task must rebuild all centroid vectors whenever the embedding model version tag is modified.

---

## 12. Test Requirements
* **Unit Testing**:
  * Test percentile calculation functions with edge cases (e.g., single-user cohort, values at absolute boundaries).
  * Assert distance calculations (Euclidean vs Cosine) return the correct closest cluster.
* **Integration Testing**:
  * Feed mock users to the clustering pipeline, verify centroid calculations, cohort table writes, and memberships persist in DB.
* **Agent/Workflow Evaluation**:
  * Verify that silhouette scores and inertia calculations are printed to logs during test runs to verify clustering quality.

---

## 13. Dependencies
* This feature depends on:
  * [career-profile-domain.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-profile-domain.md) (F1.3)
  * [outcome-memory-system.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/outcome-memory-system.md) (F4.6)
