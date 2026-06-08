# ADR 0004: Qdrant as Primary Vector Database

## Status
Accepted

## Context
CareerPilot relies on semantic matching to connect candidates with opportunities. As specified in the [Master Design Document (careerpilot_v2.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md) and the [Implementation Doctrine (IMPLEMENTATION_DOCTRINE.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/IMPLEMENTATION_DOCTRINE.md), traditional keyword matching is insufficient for career intelligence. The system requires advanced retrieval methods for:
* **Semantic Experience Matching:** Evaluating how a candidate’s experience block matches a job requirement on a conceptual level, going beyond identical terms (e.g., recognizing that "orchestrated high-throughput ML pipelines" matches a request for "Kubernetes AI infra experience").
* **Opportunity Match Scoring:** Powering the Opportunity Intelligence Engine (F2.7) by calculating similarity vectors between user profiles and thousands of daily job postings.
* **Long-Term Interaction Memory:** Enabling the LangGraph agents (F3.1) to retrieve relevant historical summaries, user preferences, and research context by embedding agent decision logs and interaction history.

To build the default retrieval stack—**BM25 (Postgres) ➔ Vector Search (Qdrant) ➔ Reranking (Cohere Cross-Encoder)**—specified in [IMPLEMENTATION_DOCTRINE.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/IMPLEMENTATION_DOCTRINE.md), the vector database must satisfy these criteria:
1. **High-Performance Vector Similarity Search:** Sub-50ms search execution for high-dimensional embedding vectors (e.g., 1536-dim OpenAI or 1024-dim Cohere embeddings).
2. **Advanced Payload Filtering:** Vector search queries must support filtering by metadata (e.g., querying only job postings matching a specific `user_id`, `salary_floor`, `location`, or `company_stage`). These filters must run *during* the vector search phase (pre-filtering) rather than after, to ensure accuracy and low latency.
3. **Self-Hostable and Developer Friendly:** The database must run locally inside a Docker container for testing and offline development, while offering simple REST and gRPC interfaces.
4. **Isolate Index Build Compute:** Building vector indices (e.g., HNSW graphs) is highly CPU and memory intensive. The vector search engine must be isolated from the relational database (PostgreSQL) to prevent search queries and index builds from impacting the transactional system of record.

## Decision
We will use **Qdrant** as the primary vector database for all semantic search, job matching, and agent memory workflows.

Qdrant will be utilized in the following capacity:
* **Collection Strategy:** We will maintain three distinct collections in Qdrant:
  1. `job_postings`: Vector representations of normalized job descriptions, including payload properties such as company, salary bounds, title, and timestamp.
  2. `candidate_profiles`: Embeddings of parsed resume experiences, education, and skills.
  3. `agent_memory`: Embeddings of interaction histories, user preferences, and research briefs for the LangGraph agent state.
* **HNSW (Hierarchical Navigable Small World) Indexing:** We will configure HNSW indices on all collections to enable fast, approximate nearest neighbor (ANN) searches.
* **Payload Indexing:** We will explicitly index highly queried payload keys (e.g., `user_id`, `skills`, `created_at`) within Qdrant to optimize filtered search performance.
* **Synchronized Write Pipeline:** When a job is ingested or a user profile is updated in PostgreSQL, a background Celery worker (`embedding-worker`) will generate the vector embedding via our embedding model API and upsert the vector along with its metadata payload into Qdrant.

## Alternatives Considered

### pgvector (PostgreSQL Extension)
* **Why Evaluated:** `pgvector` adds vector storage and distance calculations directly to PostgreSQL. This approach keeps all database storage in a single database, eliminating the need to sync data between SQL and a separate vector engine.
* **Why Rejected:** Building and searching vector indices is highly compute-intensive. Running index builds (like HNSW or IVFFlat) directly inside PostgreSQL consumes CPU and RAM resources that are needed for relational transactions, lock management, and ACID operations. This risks slowing down core application APIs during heavy vector ingestion. Furthermore, Qdrant offers superior out-of-the-box support for advanced vector compression techniques (like scalar quantization), dynamic payload filtering, and cluster scaling.

### Pinecone
* **Why Evaluated:** Pinecone is a popular, fully managed, cloud-native vector database that requires zero infrastructure management.
* **Why Rejected:** Pinecone is proprietary, closed-source, and cannot be run locally. This prevents developers from writing integration tests against a local instance (e.g., inside a local Docker Compose setup) and complicates offline development. Additionally, sending candidate profiles and agent memories to a third-party vector cloud introduces data privacy concerns and incurs high, unpredictable API costs at scale.

### Milvus
* **Why Evaluated:** Milvus is an open-source, highly scalable vector database designed for enterprise-scale workloads.
* **Why Rejected:** Milvus has a massive infrastructure footprint. Running a production-grade Milvus cluster requires deploying and managing multiple dependencies (MinIO, etcd, Pulsar), which introduces excessive operational overhead for CareerPilot's early-to-mid stages.

### Chroma
* **Why Evaluated:** Chroma is a lightweight, open-source vector store designed for AI application prototyping.
* **Why Rejected:** Chroma is excellent for local experiments but lacks production-grade features, such as horizontal scaling, multi-node clustering, advanced query optimization, and granular memory usage tuning.

## Consequences
* **Isolated Resource Utilization:** CPU-intensive vector graph traversals and embedding indexing run entirely within Qdrant, keeping PostgreSQL free to handle relational transaction queries.
* **Fast Metadata-Filtered Queries:** Qdrant's pre-filtering capabilities allow the system to apply SQL-like constraints (e.g., "only return jobs with salary > $120k") directly during vector similarity calculations.
* **Local Testability:** Developers can spin up Qdrant locally in seconds using Docker, enabling complete test suites to run in CI pipelines.
* **Split-Database Sync Management:** Introducing a separate database means PostgreSQL and Qdrant must be kept in sync. If a job posting is deleted from Postgres, we must write code to ensure its vector is deleted from Qdrant. We must handle these edge cases within our Celery pipeline.
* **Network Overhead:** Querying Qdrant adds a network hop between the API/Worker service and the vector database, although this is mitigated by using high-speed gRPC clients.

## Tradeoffs

### Infrastructure Footprint vs. CPU Isolation
We trade off the simplicity of a single database stack (which we could achieve using `pgvector` in PostgreSQL) for resource isolation and search performance. Because CareerPilot calculates match scores and search queries continuously, separating vector math from relational records is essential to prevent system degradation. We manage this trade-off by delegating the sync responsibility to asynchronous Celery workers, ensuring that HTTP request paths are never blocked by database synchronization logic.

### Dynamic Schemas vs. Strict Query Validation
Unlike PostgreSQL's strict schemas, Qdrant payload metadata is unstructured JSON. This makes it easy to attach arbitrary metadata to vector records, which is useful when scrapers change formats. However, it introduces the risk of query failures if payload fields are modified (e.g., querying a payload key that has been renamed). We resolve this trade-off by using typed Pydantic models in the Python codebase to strictly validate and write payloads to Qdrant, ensuring metadata consistency at the application boundary.
