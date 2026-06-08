# ADR 0010: Event-Driven Architecture for Decoupled Domain Communication

## Status
Accepted

## Context
CareerPilot V2 is divided into distinct, decoupled domains: Identity, Career Profile, Market Intelligence, Intelligence Synthesis, Strategy, and Execution. Changes in one domain frequently trigger updates or evaluations in others. For example:
- Updating a candidate's career goals (Identity Context) requires recalculating their Career Health Score (Intelligence Synthesis Context).
- Completing a job application submission (Execution Context) requires storing the result in the Outcome Memory System (Execution Context) and triggering the Calibration Engine (Intelligence Synthesis Context) to update the opportunity scoring model.

If these cross-domain interactions are handled via synchronous REST APIs or direct service-to-service calls, it leads to:
1. **Tight Coupling**: Services must know about the existence, endpoints, and data contracts of other services.
2. **Cascading Failures**: If the Career Health Score service is down or slow, the Identity service cannot complete goal updates or returns high latency to the client.
3. **Dual-Write Anomalies**: Writing to the database and sending a network request to another service cannot be done atomically. If one succeeds and the other fails, the system is left in an inconsistent state.

Since **outcome data is the most valuable asset** in CareerPilot and the **intelligence compounding loop** relies on 100% reliable data flows (as highlighted in [IMPLEMENTATION_DOCTRINE.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/IMPLEMENTATION_DOCTRINE.md)), the communication architecture must be highly durable, transactionally consistent, and decoupled.

## Decision
We will adopt an Event-Driven Architecture (EDA) utilizing the **Transactional Outbox Pattern** in PostgreSQL as the event publishing mechanism, with **Redis/Celery** serving as the asynchronous message broker and event dispatcher.

The architecture will operate as follows:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TRANSACTIONAL OUTBOX FLOW                       │
│                                                                        │
│  [Domain Service]                                                      │
│       │ (Mutates State)                                                │
│       ▼                                                                │
│  ┌─────────────────────────────────────────────────────────┐          │
│  │ DATABASE TRANSACTION                                    │          │
│  │                                                         │          │
│  │ 1. Update Business Table (e.g., career_goals)           │          │
│  │ 2. Insert Event Record into domain_events_outbox table   │          │
│  │                                                         │          │
│  └────────────────────────────┬────────────────────────────┘          │
│                               │ (Atomic Commit)                        │
│                               ▼                                        │
│  [PostgreSQL Transaction Log (WAL) or Outbox Table]                   │
│                               ▲                                        │
│                               │ (Polls / Listen)                       │
│  [Outbox Publisher (Celery/Daemon)]                                    │
│                               │                                        │
│                               ▼ (Publishes)                            │
│  [Redis Message Broker]                                                │
│                               │                                        │
│                               ▼ (Dispatches)                           │
│  [Celery Asynchronous Workers] ──► [Consumer Services]                 │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### 1. The Outbox Table Schema
All domain services must write events into a single, centralized Outbox table inside the same database transaction as the business data mutation.

```sql
CREATE TABLE domain_events_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(255) NOT NULL, -- e.g., 'identity.goals_updated'
    aggregate_type VARCHAR(100) NOT NULL, -- e.g., 'career_goals'
    aggregate_id VARCHAR(255) NOT NULL, -- UUID of the mutated entity
    payload JSONB NOT NULL, -- Full schema-validated event payload
    metadata JSONB NOT NULL, -- Correlation ID, Causing User, Trace ID
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING, PROCESSED, FAILED
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX idx_outbox_pending_events ON domain_events_outbox(created_at) WHERE status = 'PENDING';
```

### 2. Event Publishing Loop (Outbox Publisher)
An independent background process (either a Celery Beat task executing every 1 second, or a dedicated long-running worker using PostgreSQL `LISTEN/NOTIFY` triggered by a database row insert) will:
1. Query unpulled records from `domain_events_outbox` where `status = 'PENDING'`.
2. Publish each event to the designated Redis broker channel or Celery queue.
3. Upon confirmation from the broker, mark the outbox row as `status = 'PROCESSED'` and populate `processed_at`.
4. If publishing fails, increment the `retry_count` and apply exponential backoff.

### 3. Message Broker (Redis)
- **Role**: Redis will act as the high-throughput, low-latency transport layer.
- **Routing**: Events are pushed to Redis list-based Celery queues configured for pub-sub-like routing using Celery's task routing capabilities.

### 4. Consumer Dispatch (Celery)
- **Role**: Celery workers subscribe to event tasks.
- **Idempotency**: Consumers must be designed to be idempotent. Since the Outbox Pattern guarantees *at-least-once* delivery, consumers will track processed `event_id` values in a lightweight Redis-based deduplication store (with a 24-hour TTL) or directly in their local PostgreSQL tables before processing.

## Alternatives Considered

### 1. Direct Pub-Sub Publishing (Redis Pub/Sub or Celery Direct Dispatch)
- **Description**: Domain services publish events directly to Redis or dispatch Celery tasks inline during API requests (e.g. `auth_service.update_goals()` directly calling `recalculate_health.delay()`).
- **Why Rejected**: This introduces dual-write anomalies. If the database update succeeds but the Celery dispatch fails (network glitch, Redis crash), the event is lost. If the Celery task is dispatched first but the database transaction rolls back, the consumer processes phantom data. This risk violates the durability requirements of CareerPilot's outcome-driven architecture.

### 2. Dedicated Message Brokers (RabbitMQ or Apache Kafka)
- **Description**: Running RabbitMQ for reliable queuing or Kafka for event streaming and log playback.
- **Why Rejected**: Adding RabbitMQ or Kafka introduces significant operational overhead (clustering, partition management, configuration, monitoring) to the stack. For the MVP and V2 scale, self-hosting PostgreSQL and Redis is already standard and configured in [project-setup-architecture.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/project-setup-architecture.md). Using the PostgreSQL outbox table provides RabbitMQ-like durability without the infrastructure complexity.

### 3. Log-Based Change Data Capture (Debezium + Kafka)
- **Description**: Using Debezium to stream database WAL logs directly to a message broker.
- **Why Rejected**: Highly robust and non-intrusive, but requires complex infrastructure (Java/Kafka Connect/Zookeeper/Kafka). It is overkill for our current Python/FastAPI monolithic deployment.

## Consequences

### Positive
- **Guaranteed At-Least-Once Delivery**: Events are never lost due to network or service crashes during database writes.
- **Strong Domain Decoupling**: Producers have zero knowledge of consumers. The Identity context only knows it writes `identity.goals_updated` to the outbox.
- **Write-Path Performance**: API response latency remains low because database transactions only write to a local outbox table, avoiding inline external network hops.
- **Traceability**: The `domain_events_outbox` table serves as an audit log of all historical state changes, assisting debugging and event replay scenarios.

### Negative
- **Operational Complexity**: Requires a background publishing process to poll the outbox table and forward events.
- **Storage Overhead**: The outbox table grows over time. We must implement a purging job to delete rows older than 14 days where `status = 'PROCESSED'`.
- **Eventual Consistency**: State changes in downstream services (e.g., Career Health Score) are not immediate. The user dashboard may display a stale health score for a brief window (typically < 2 seconds) until the background loop completes.

## Tradeoffs

### Reliability vs. Latency (Real-time vs. Eventual Consistency)
We trade immediate synchronous consistency for system reliability. A synchronous API write is simple but fragile. By choosing the Outbox Pattern, we accept that the system is eventually consistent, requiring the client UI to handle asynchronous updates (e.g. via polling or WebSockets) in exchange for ensuring no event is ever dropped.

### Infrastructure Overhead vs. Application Logic Complexity
We chose to implement the Outbox Pattern in the application database rather than using dedicated event-streaming infrastructure. This trades a small amount of application write-path complexity (every service must write to the outbox table) for substantial infrastructure simplicity (no need to deploy, maintain, or secure RabbitMQ or Kafka clusters).
