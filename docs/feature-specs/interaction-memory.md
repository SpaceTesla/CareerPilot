# Feature Specification: Interaction Memory (F3.5)

## 1. Purpose
Interaction Memory is a dedicated state-management and retrieval service designed to preserve and manage multi-turn dialogue history, user preferences, and agent actions. It stores raw transaction histories in PostgreSQL and compiles semantic vector representations in Qdrant. A core challenge in LLM agent systems is context window bloat and performance degradation over long sessions. Interaction Memory resolves this by implementing a dual-memory system: a sliding window for raw transaction history and an asynchronous memory summarizer that condenses older turns into highly compressed, semantically indexable summary logs.

---

## 2. User Value
Interaction Memory ensures that CareerPilot acts like a continuous career advisor. The system doesn't "forget" context between chat messages or job search runs. If a user says, "I prefer remote roles or companies headquartered on the East Coast" in their first week, and searches for "Platform Engineering" three weeks later, the system remembers that preference. This builds a personalization loop, making the recommendations feel customized and compounding in value over time.

---

## 3. Requirements
* **Schema Design**: Support a database schema in PostgreSQL for message logs and summaries, linked to Qdrant for semantic retrieval.
* **Memory Storage**: Store incoming user prompts, agent thoughts, outputs, and intermediate states in real time.
* **Memory Retrieval**: Provide hybrid lookup (BM25 + Semantic Vector) to retrieve relevant historical interactions based on the active prompt context.
* **Asynchronous Memory Summarization**: Monitor active thread sizes. When message count exceeds a threshold (e.g., 10 turns), compile and summarize older messages, append the summary, and archive raw turns to keep context payloads light.
* **API Endpoints**: Provide developer interfaces to retrieve, update, delete, or clear session memories.
* **Expiration Policies**: Implement rules for data retention (e.g., raw message archives expire after 30 days, summarized semantic vectors persist indefinitely).
* **Memory Analytics**: Compute stats on memory hits, active token size reductions, and semantic relevance ratios.

---

## 4. Database Changes

### PostgreSQL Tables

#### `interaction_memories`
Stores the raw historical messages for user-agent conversations.
```sql
CREATE TABLE interaction_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR(255) NOT NULL REFERENCES agent_sessions(thread_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- user, assistant, system
    content TEXT NOT NULL,
    summary_id UUID, -- refers to summarized log if archived
    tokens_count INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_interaction_memories_thread ON interaction_memories(thread_id);
CREATE INDEX idx_interaction_memories_user ON interaction_memories(user_id);
```

#### `interaction_summaries`
Stores compiled summaries of older turns.
```sql
CREATE TABLE interaction_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR(255) NOT NULL REFERENCES agent_sessions(thread_id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    start_message_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    end_message_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_interaction_summaries_thread ON interaction_summaries(thread_id);
```

### Qdrant Vector Collection
* **Collection Name**: `interaction_memory_vectors`
* **Vector Configuration**:
  * Dimension: 1536 (OpenAI `text-embedding-3-small`) or 384 (local `bge-small-en-v1.5`)
  * Distance: Cosine
* **Payload Fields**:
  * `user_id` (UUID)
  * `thread_id` (string)
  * `memory_id` (UUID - matching `interaction_memories` or `interaction_summaries`)
  * `text_chunk` (string)
  * `created_at` (integer timestamp)

### Alembic Migration Plan
1. Create `interaction_summaries` table.
2. Create `interaction_memories` table with a nullable foreign key `summary_id` referencing `interaction_summaries(id)`.
3. Add indexes to optimize queries on `thread_id` and `user_id`.

---

## 5. API Endpoints

### GET `/api/v1/memory/{thread_id}`
Retrieve raw active messages for a thread (unarchived) plus the consolidated summary.
* **Response Body (200 OK)**:
  ```json
  {
    "thread_id": "thread_8f3b2a1c_user_4a2b9c3d",
    "summary": "User prefers remote opportunities in FinTech. Emphasized Kubernetes skills and backend architecture.",
    "messages": [
      {
        "id": "c1c1c1c1-2233-4455-6677-8899aabbccdd",
        "role": "user",
        "content": "Can you check Netflix postings?",
        "created_at": "2026-06-09T02:04:18Z"
      }
    ]
  }
  ```

### DELETE `/api/v1/memory/{thread_id}`
Clear or reset memory context for a thread.
* **Response Body (200 OK)**:
  ```json
  {
    "thread_id": "thread_8f3b2a1c_user_4a2b9c3d",
    "status": "cleared",
    "message": "Memory logs and Qdrant vector links deleted successfully"
  }
  ```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class MessageModel(BaseModel):
    id: UUID
    role: str = Field(description="Role identifier: 'user', 'assistant', or 'system'")
    content: str
    tokens_count: int
    created_at: datetime

class ThreadMemory(BaseModel):
    thread_id: str
    user_id: UUID
    summary: Optional[str] = None
    messages: List[MessageModel] = Field(default_factory=list)
```

---

## 7. Services

### `InteractionMemoryService`
* **Method**: `store_message(thread_id: str, role: str, content: str) -> MessageModel`
  * Computes tokens count, writes message to `interaction_memories` database, generates vector embedding of the content chunk, and saves it in the Qdrant vector collection.
* **Method**: `retrieve_contextual_memories(thread_id: str, query: str, limit: int = 5) -> List[str]`
  * Queries Qdrant using similarity matching for historical events, returns matches.
* **Method**: `summarize_thread_history(thread_id: str) -> Optional[str]`
  * Compiles active messages past threshold, triggers LLM summarization, saves to `interaction_summaries`, updates `summary_id` on consolidated messages, and deletes raw messages from PostgreSQL if expiration policy requires.

---

## 8. Events

### `agent.memory.summarized`
* **Producer**: `InteractionMemoryService`
* **Consumer**: `ObservabilityPlatform`
* **Payload**:
  ```json
  {
    "event_id": "evt_mem_sum_12",
    "timestamp": "2026-06-09T02:04:18Z",
    "thread_id": "thread_8f3b2a1c_user_4a2b9c3d",
    "archived_messages_count": 12,
    "new_summary_tokens": 120
  }
  ```

---

## 9. Background Jobs
* **Job Name**: `memory_expiration_archiver`
  * **Frequency**: Daily at 02:00 AM (`0 2 * * *`)
  * **Payload**: None
  * **Logic**: Scan `interaction_memories` rows where `created_at < CURRENT_TIMESTAMP - INTERVAL '30 days'` and `summary_id IS NOT NULL`. Delete these expired raw messages. Keep Qdrant vectors and `interaction_summaries` rows intact.
  * **Retry Behavior**: Retry with Celery default exponential backoff (up to 3 times).

---

## 10. Acceptance Criteria
* **AC 1**: Given an active chat thread, when writing messages, the system must create a corresponding vector payload inside Qdrant and a transaction record in PostgreSQL.
* **AC 2**: Given a thread with more than 15 messages, when a new message is sent, the system must trigger the summarization routine to archive the first 10 messages.
* **AC 3**: Given a search query, when executing retrieval, the service must return historically relevant messages matching semantically even if key nouns are different.

---

## 11. Edge Cases
* **Qdrant Timeout**: If the Qdrant connection fails during write, the PostgreSQL database write must succeed, and the system must queue a background task to index the missing message vectors in Qdrant later.
* **Summarizer Failure**: If the LLM summarization pipeline errors out, the graph must continue running with raw messages to prevent blocking the user experience. It will retry the summarization on the next message execution loop.
* **Concurrent Memory Append**: If the agent writes multiple nodes simultaneously, thread memory updates must apply a row lock on the session ID.

---

## 12. Test Requirements
* **Unit Testing**:
  * Verify token counting functionality is within 5% error margin of tiktoken.
  * Test sliding window and chunking splits.
* **Integration Testing**:
  * Write messages, run mock summarization, assert raw row counts in database diminish while summary row exists.
* **Agent/Workflow Evaluation**:
  * Assert that vector search retrieves the correct profile preferences from mock conversations with cosine similarity >= 0.78.

---

## 13. Dependencies
* This feature depends on:
  * [langgraph-foundation.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/langgraph-foundation.md) (F3.1)
* This feature is a dependency for:
  * [career-strategy-reviews.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-strategy-reviews.md) (F7.4)
