# ADR 0003: Redis as Caching Layer, Session Store, Rate Limiter, and Message Broker

## Status
Accepted

## Context
CareerPilot is designed as an event-driven, microservice-adjacent platform. As outlined in the [Master Design Document (careerpilot_v2.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md) and the [Dependency Graph (DEPENDENCY_GRAPH.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md), the backend integrates several asynchronous services (API gateway, ingestion scrapers, LangGraph agents, Temporal workflows, and ML calibration workers).

To ensure reliability, low latency, and efficient scaling, the system requires infrastructure supporting the following operational roles:
1. **High-Performance Caching:** Critical read-heavy endpoints, such as the Career Dashboard (F1.9), normalized Skill Trends (F1.6), and Company Intelligence profiles (F2.4), must load in sub-100ms. Querying PostgreSQL directly for every page load would cause database bottlenecks.
2. **Rate Limiting:** To prevent abuse of public API endpoints and protect downstream LLM integrations (which incur significant API costs) and web scraping targets from exceeding rate limits, the system needs an extremely fast, low-overhead rate limiting mechanism.
3. **Session and Token Management:** Storing active user session states, temporary OAuth data, and blacklisted JWT access tokens requires a fast key-value store with support for automatic Time-To-Live (TTL) key expiration.
4. **Message Broker for Celery Workers:** Ingestion tasks, NLP extractions, and health score calculations run asynchronously in background workers (Celery). The system requires a highly responsive message broker to distribute and queue tasks from the FastAPI layer to Celery.

## Decision
We will use **Redis** as the unified caching layer, session store, rate limiter, and Celery message broker.

Redis will be utilized in the following capacity:
* **Celery Queue Broker:** Redis will act as the transport layer for Celery, passing serialized task payloads between the FastAPI HTTP gateway and the background workers.
* **Distributed Cache:** We will implement caching decorators on read-heavy service methods (e.g., retrieving computed health score matrices or company watchlist statistics). Cache keys will be namespaces (e.g., `cache:user_health:{user_id}`) and configure explicit TTLs based on update frequency.
* **Token Blacklist and Session Store:** Access and refresh token hashes will be stored in Redis. Upon user logout, JWT tokens will be blacklisted in Redis with a TTL set to match the token’s remaining lifespan.
* **Rate Limiter:** We will implement token-bucket or sliding-window rate limiting middleware at the FastAPI HTTP gateway level, storing IP/user hit counters in Redis using atomic operations (`INCR`, `EXPIRE`).
* **Deployment Segmentation:** In production, Redis operations will be divided into separate logical databases or distinct container instances (e.g., Instance A dedicated as the Celery message broker, Instance B dedicated to application caching and rate limiting) to prevent cache eviction configurations from dropping queued tasks.

## Alternatives Considered

### RabbitMQ (for Message Brokering)
* **Why Evaluated:** RabbitMQ is a highly robust, dedicated message broker supporting advanced routing topologies, message acknowledgments, and complex queue configurations.
* **Why Rejected:** RabbitMQ is purely a message broker. Implementing it would still require deploying a separate caching and key-value store (such as Redis or Memcached) to handle dashboard caching and rate-limiting. Introducing RabbitMQ increases operational overhead, deployment complexity, and infrastructure costs. Redis is fully capable of handling Celery's broker requirements at CareerPilot's scale.

### Memcached (for Caching)
* **Why Evaluated:** Memcached is a high-performance, simple, distributed memory caching system, frequently used for scaling web databases.
* **Why Rejected:** Memcached only supports simple key-value strings and lacks advanced data structures (hashes, lists, sets, sorted sets) that are necessary for implementing rate-limiting algorithms and Celery queues. Additionally, Memcached lacks persistence and does not support pub/sub or message broker features.

### PostgreSQL (as Broker and Session Store)
* **Why Evaluated:** Using PostgreSQL tables to store Celery tasks and session data keeps the technology stack simple and avoids running another infrastructure service.
* **Why Rejected:** Databases designed for relational integrity are not optimized for queuing workloads. Using Postgres as a Celery broker results in constant polling, frequent row locking, and massive write-amplification, which degrades performance and degrades the responsiveness of system of record transactions.

## Consequences
* **Reduced Stack Complexity:** A single, well-understood technology handles caching, rate-limiting, sessions, and task queues.
* **Low Latency Read Operations:** Cached API responses (like the Dashboard view) load almost instantly, offloading queries from PostgreSQL.
* **Decoupled Architecture:** Asynchronous tasks are quickly dispatched to Celery via Redis, allowing the API gateway to return immediate 202 Accepted responses.
* **In-Memory Volatility:** If the Redis instance restarts, cached data is lost. While not fatal for caches, a crash of the Celery broker instance without configured append-only-file (AOF) persistence can lead to lost task states.
* **Eviction Risks:** If cache memory fills up, Redis may evict keys based on the configured policy (e.g., `allkeys-lru`). If Celery queues share the same instance without proper isolation, task payloads could be evicted, causing task failures.

## Tradeoffs

### Operational Simplicity vs. Resource Isolation
We trade off the strict resource isolation of having separate specialized tools (e.g., RabbitMQ for queues + Memcached for caching) for the operational simplicity of using a single Redis stack. We mitigate the risk of mutual resource starvation (where a caching surge deprives the message queue of memory) by running separate Redis processes for the cache and the queue broker in high-load environments. This gives us logical and physical resource isolation while keeping the developer API identical.

### RAM Speed vs. Persistent Durability
Redis operates entirely in memory to achieve sub-millisecond latencies. This speed comes at the cost of disk durability. We accept this trade-off because all critical, permanent application state (profiles, job details, outcome memories, audit trails) is stored in PostgreSQL. Redis is strictly reserved for transient, non-authoritative data. If the Redis cache is wiped, the application degrades gracefully: caches are rebuilt from PostgreSQL on the next request, and active users may need to re-authenticate.
