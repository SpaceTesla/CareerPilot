# Feature Specification: Knowledge Graph (F7.1)

## 1. Purpose
The `Knowledge Graph` feature deploys and manages a Neo4j database to model relationships between skills, roles, companies, and candidate profiles. It maps nodes and transition edges (such as career transitions and hiring events) derived from historical outcomes. This enables the platform to perform graph-based pathfinding and career trajectory modeling.

---

## 2. User Value
In traditional career management, candidates view roles in isolation and lack insight into career progression paths. 
The Knowledge Graph maps actual career moves made by professionals in the target industry, identifying common transitions (e.g., "73% of engineers who moved from Senior Backend to AI Platform Engineer added LangGraph and Kubernetes to their stack at a startup first"). 
Within the **Career Intelligence Compounding Loop** (defined in [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md)), this graph powers the next-generation [Position Delta Engine (F1.8)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md). It replaces heuristic gap lists with proven career paths, helping users understand which skills and roles lead to their long-term goals.

---

## 3. Requirements
- **Neo4j Deployment**: Integrate Neo4j database into the system stack (Docker, Kubernetes configurations).
- **Graph Schema Design**:
  - **Nodes**: `Role` (e.g., "Staff Engineer"), `Skill` (e.g., "Python"), `Company` (e.g., "Stripe"), `CandidateProfile` (anonymized node mapping user profiles).
  - **Relationships/Edges**: 
    - `REQUIRES_SKILL` (from `Role`/`Company` to `Skill`)
    - `HAS_SKILL` (from `CandidateProfile` to `Skill`)
    - `TRANSITIONED_TO` (from one `Role` to another `Role`, annotated with count and duration)
    - `EMPLOYED_AT` (from `CandidateProfile` to `Company`)
    - `HIRED_ROLE` (from `Company` to `Role`)
- **Career Transition Edge Generation**: Aggregate user experience timelines to build weighted `TRANSITIONED_TO` edges between roles.
- **Graph Ingestion Pipeline**: Asynchronous workers that sync changes in PostgreSQL tables (profiles, postings, companies) to Neo4j nodes and edges.
- **Graph Query APIs**: Retrieve career paths and related skills using graph adjacencies.
- **Graph Analytics Service**: Compute graph metrics (e.g., degree centrality to identify high-value "bridge skills" and page-rank to find influential companies).
- **Validation Tests**: Unit and integration tests to verify graph creation and query logic.

---

## 4. Database Changes

Introduces Neo4j as a secondary datastore alongside PostgreSQL and Qdrant.

### Graph Schema Definitions (Neo4j Cypher)

#### Node Schema & Constraints
```cypher
// Constraints to ensure entity uniqueness across the graph
CREATE CONSTRAINT unique_role_name IF NOT EXISTS
FOR (r:Role) REQUIRE r.name IS UNIQUE;

CREATE CONSTRAINT unique_skill_name IF NOT EXISTS
FOR (s:Skill) REQUIRE s.canonical_name IS UNIQUE;

CREATE CONSTRAINT unique_company_name IF NOT EXISTS
FOR (c:Company) REQUIRE c.name IS UNIQUE;

CREATE CONSTRAINT unique_profile_id IF NOT EXISTS
FOR (p:CandidateProfile) REQUIRE p.profile_id IS UNIQUE;
```

#### Node Properties
- **`Role`**: `name` (String, PK), `job_family` (String), `average_seniority_level` (Integer)
- **`Skill`**: `canonical_name` (String, PK), `category` (String)
- **`Company`**: `name` (String, PK), `industry` (String), `size_range` (String)
- **`CandidateProfile`**: `profile_id` (String, UUID, PK), `anonymized` (Boolean)

#### Relationship Properties
- **`TRANSITIONED_TO`**: `frequency_count` (Integer), `avg_duration_months` (Float), `confidence` (Float)
- **`REQUIRES_SKILL`**: `relevance_score` (Float), `is_mandatory` (Boolean)
- **`EMPLOYED_AT`**: `start_date` (String), `end_date` (String, Nullable)

### Ingestion Logic
Data from PostgreSQL is exported in batches and loaded into Neo4j using transactional Cypher statements (`MERGE`).

---

## 5. API Endpoints

### `GET /api/v2/market/graph/path`
Finds the most frequent career transition paths from a candidate's current role and skill set to their target role.
- **Authentication**: Required (JWT, Scope: `user`)
- **Query Parameters**:
  - `start_role`: "Senior Backend Engineer" (Required)
  - `target_role`: "AI Platform Engineer" (Required)
  - `max_steps`: `INTEGER` (default 2)
- **Response (200 OK)**:
```json
{
  "paths": [
    {
      "steps": [
        {
          "step_index": 0,
          "source_role": "Senior Backend Engineer",
          "target_role": "AI Platform Engineer",
          "avg_transition_time_months": 20.4,
          "common_bridge_skills": ["LangGraph", "Kubernetes", "Qdrant"],
          "confidence_score": 0.85
        }
      ],
      "path_probability": 0.68
    }
  ]
}
```

### `GET /api/v2/market/graph/skills/{skill_name}/related`
Retrieves related skills based on co-occurrence in roles and candidate profiles.
- **Authentication**: Required (JWT, Scope: `user`)
- **Path Parameters**:
  - `skill_name`: "React" (Required)
- **Response (200 OK)**:
```json
{
  "searched_skill": "React",
  "related_skills": [
    { "skill_name": "TypeScript", "relationship": "CO_OCCURRENCE", "weight": 0.92 },
    { "skill_name": "Next.js", "relationship": "SPECIALIZATION_OF", "weight": 0.84 },
    { "skill_name": "Redux", "relationship": "COMPATIBLE_WITH", "weight": 0.78 }
  ]
}
```

### `POST /api/v2/market/graph/sync`
Manually triggers synchronization of new PostgreSQL records to Neo4j.
- **Authentication**: Required (JWT, Scope: `admin`)
- **Response (202 Accepted)**:
```json
{
  "task_id": "c1d2e3f4-5678-90ab-cdef-1234567890ab",
  "status": "RUNNING",
  "message": "Graph synchronization pipeline triggered."
}
```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from uuid import UUID
from typing import List, Dict, Optional, Any

class GraphNode(BaseModel):
    id: str
    label: str
    properties: Dict[str, Any]

class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str
    properties: Dict[str, Any]

class CareerPathStep(BaseModel):
    step_index: int
    source_role: str
    target_role: str
    avg_transition_time_months: float
    common_bridge_skills: List[str]
    confidence_score: float
```

---

## 7. Services

### `Neo4jConnectionManager`
Manages Neo4j driver lifecycles.
- `get_session() -> Session`: Returns a thread-safe database session.
- `close_driver() -> None`: Safely closes the driver during shutdown.

### `GraphIngestionPipeline`
Syncs PostgreSQL records to Neo4j.
- `sync_profile_nodes(profiles: list[dict]) -> None`: Syncs user profiles and skills taxonomy using `MERGE` statements.
- `sync_transition_edges(experiences: list[dict]) -> None`: Generates `TRANSITIONED_TO` edges by pairing sequential experiences.

### `CareerGraphAnalyticsService`
Runs graph calculations and queries.
- `find_career_paths(start_role: str, target_role: str, max_depth: int) -> list`: Queries Neo4j for matching paths and calculates confidence weights.
- `get_related_skills(skill_name: str) -> list`: Uses Cypher traversal to find adjacent skill nodes.

---

## 8. Events

### Event: `market.graph.synced`
- **Producer**: `GraphIngestionPipeline`
- **Consumer**: `observability-service`, `digest-worker`
- **Payload Schema**:
```json
{
  "event_id": "e3f4a5b6-7c8d-9e0f-1a2b-3c4d5e6f7a8b",
  "event_type": "market.graph.synced",
  "timestamp": "2026-06-09T03:00:00Z",
  "payload": {
    "sync_run_id": "92f87a3b-2401-447a-88bc-19b813bcfb92",
    "nodes_updated": 1420,
    "edges_updated": 3280,
    "duration_ms": 12050
  }
}
```

---

## 9. Background Jobs
- **`scheduled_postgres_to_neo4j_sync_job`**: Runs nightly. Scans PostgreSQL for changes (updated profiles, newly added jobs) and updates Neo4j.
- **`graph_centrality_recomputation_job`**: Runs weekly. Computes degree centrality metrics for skills and updates `popularity_score` variables in the database.

---

## 10. Acceptance Criteria

### Pathfinding Scenario
- **Given**: Neo4j contains nodes for "Senior Backend Engineer", "AI Platform Engineer", "LangGraph", and "Kubernetes", with transition edges between the roles.
- **When**: A user queries the path from "Senior Backend Engineer" to "AI Platform Engineer".
- **Then**: The pathfinder returns steps showing "LangGraph" and "Kubernetes" as key skills required for the transition.

### Sync Integrity Scenario
- **Given**: A user adds "Rust" to their profile in PostgreSQL.
- **When**: The `scheduled_postgres_to_neo4j_sync_job` runs.
- **Then**: Neo4j creates a `HAS_SKILL` edge between the corresponding `CandidateProfile` and the `Rust` `Skill` node.

---

## 11. Edge Cases
- **Circular Paths**: Career paths can form loops (e.g., Role A -> Role B -> Role A). Pathfinder queries must use Cypher depth limits (`*1..3`) and path uniqueness checks to prevent infinite loops.
- **Super-nodes**: Common skills like "Python" or "Git" can connect to thousands of nodes, which can slow down query performance. Traversal queries must filter by skill category to ignore generic tools.
- **Connection Loss**: If Neo4j disconnects, the ingestion task should write failed records to a queue and retry once the connection is restored.

---

## 12. Test Requirements
- **Integration Path Test**: Assert that the pathfinder correctly returns transition paths for a sample dataset.
- **Transaction Rollback Test**: Verify that graph updates rollback completely if a transaction fails.

---

## 13. Dependencies
- **Direct Blockers**:
  - [Career Profile Domain (F1.3)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
  - [Job Market Data Foundation (F1.5)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
- **Downstream Beneficiaries**:
  - [Gap-Aware Retrieval (F7.2)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/gap-aware-retrieval.md)
