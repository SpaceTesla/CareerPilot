from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional
from uuid import UUID, uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.database.models import InteractionMemory, InteractionSummary
from app.infrastructure.rag.embeddings.service import embedding_service
from app.services.agent.models import MessageModel, ThreadMemory
from langchain_google_genai import ChatGoogleGenerativeAI

logger = get_logger(__name__)


class InteractionMemoryService:
    """
    Dual-memory service:
    1. Raw conversation dialogue in PostgreSQL (interaction_memories).
    2. Vector embeddings in Qdrant (interaction_memory_vectors) for long-term semantic search.
    3. Memory summarizer to compress older turns when context grows.
    """

    def __init__(self) -> None:
        self.qdrant = QdrantClient(url=settings.qdrant_url)
        self.collection_name = "interaction_memory_vectors"
        self._ensure_collection()
        self.llm = ChatGoogleGenerativeAI(
            model=settings.model_name,
            temperature=0.0,
        )

    def _ensure_collection(self) -> None:
        try:
            collections = self.qdrant.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=768,  # models/embedding-001 dimension
                        distance=qmodels.Distance.COSINE,
                    ),
                )
                logger.info(f"Qdrant collection '{self.collection_name}' created.")
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}")

    async def store_message(
        self, db: AsyncSession, thread_id: str, user_id: UUID, role: str, content: str
    ) -> MessageModel:
        msg_id = uuid4()
        tokens_count = max(1, len(content) // 4)

        try:
            # 1. Save to PostgreSQL
            db_msg = InteractionMemory(
                id=str(msg_id),
                thread_id=thread_id,
                user_id=str(user_id),
                role=role,
                content=content,
                tokens_count=tokens_count,
                created_at=datetime.utcnow(),
            )
            db.add(db_msg)
            await db.commit()

            # 2. Index in Qdrant
            try:
                emb = await embedding_service.embed_text(content)
                if emb:
                    self.qdrant.upsert(
                        collection_name=self.collection_name,
                        points=[
                            qmodels.PointStruct(
                                id=str(msg_id),
                                vector=emb,
                                payload={
                                    "user_id": str(user_id),
                                    "thread_id": thread_id,
                                    "memory_id": str(msg_id),
                                    "text_chunk": content,
                                    "created_at": int(datetime.utcnow().timestamp()),
                                }
                            )
                        ]
                    )
            except Exception as ex:
                logger.warning(f"Failed to upsert message embedding to Qdrant: {ex}")
                # We do not crash here, as per AC 1 Postgres write succeeded.

            # 3. Check for sliding window summarization threshold (15 messages)
            try:
                # Count unsummarized messages
                stmt = select(InteractionMemory).where(
                    InteractionMemory.thread_id == thread_id,
                    InteractionMemory.summary_id == None
                ).order_by(InteractionMemory.created_at.asc())
                result = await db.execute(stmt)
                unsummarized_msgs = result.scalars().all()

                if len(unsummarized_msgs) > 15:
                    logger.info(f"Thread {thread_id} unsummarized message count ({len(unsummarized_msgs)}) exceeds 15. Summarizing...")
                    await self.summarize_thread_history(db, thread_id, unsummarized_msgs)
            except Exception as ex:
                logger.warning(f"Auto-summarization failed: {ex}")

            return MessageModel(
                id=msg_id,
                role=role,
                content=content,
                tokens_count=tokens_count,
                created_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Failed to store message: {e}")
            await db.rollback()
            raise

    async def retrieve_contextual_memories(
        self, db: AsyncSession, thread_id: str, query: str, limit: int = 5
    ) -> List[str]:
        try:
            query_vector = await embedding_service.embed_text(query)
            if not query_vector:
                return []

            # Vector search in Qdrant
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="thread_id",
                            match=qmodels.MatchValue(value=thread_id)
                        )
                    ]
                ),
                limit=limit
            )
            return [hit.payload["text_chunk"] for hit in results]
        except Exception as e:
            logger.warning(f"Failed to retrieve contextual memories: {e}")
            return []

    async def summarize_thread_history(
        self, db: AsyncSession, thread_id: str, msgs_to_summarize: List[InteractionMemory] | None = None
    ) -> Optional[str]:
        try:
            if msgs_to_summarize is None:
                stmt = select(InteractionMemory).where(
                    InteractionMemory.thread_id == thread_id,
                    InteractionMemory.summary_id == None
                ).order_by(InteractionMemory.created_at.asc())
                result = await db.execute(stmt)
                msgs_to_summarize = list(result.scalars().all())

            # Only summarize if there's enough history (we summarize the first 10 messages)
            if len(msgs_to_summarize) < 10:
                return None

            archive_batch = msgs_to_summarize[:10]
            chat_context = "\n".join(f"{m.role}: {m.content}" for m in archive_batch)

            prompt = f"""
            Summarize the following conversation history between the user and assistant.
            Highlight the user's primary preferences (such as role type, location preferences, salary goals), key achievements discussed, and tools mentioned.
            Keep the summary highly condensed and actionable.

            Conversation:
            {chat_context}

            Summary:
            """
            response = await self.llm.ainvoke(prompt)
            summary_text = response.content if isinstance(response.content, str) else ""

            # Save summary to PostgreSQL
            summary_id = uuid4()
            db_summary = InteractionSummary(
                id=str(summary_id),
                thread_id=thread_id,
                summary_text=summary_text,
                start_message_timestamp=archive_batch[0].created_at,
                end_message_timestamp=archive_batch[-1].created_at,
                created_at=datetime.utcnow(),
            )
            db.add(db_summary)

            # Update messages with summary ID link
            archive_ids = [m.id for m in archive_batch]
            update_stmt = update(InteractionMemory).where(
                InteractionMemory.id.in_(archive_ids)
            ).values(summary_id=str(summary_id))
            await db.execute(update_stmt)
            await db.commit()

            logger.info(f"Summarized 10 messages for thread {thread_id} under summary_id {summary_id}")
            return summary_text

        except Exception as e:
            logger.error(f"Failed to summarize thread history: {e}")
            await db.rollback()
            return None

    async def clear_memory(self, db: AsyncSession, thread_id: str) -> None:
        try:
            # Delete from PostgreSQL
            stmt = delete(InteractionMemory).where(InteractionMemory.thread_id == thread_id)
            await db.execute(stmt)
            stmt_sum = delete(InteractionSummary).where(InteractionSummary.thread_id == thread_id)
            await db.execute(stmt_sum)
            await db.commit()

            # Delete from Qdrant
            self.qdrant.delete(
                collection_name=self.collection_name,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="thread_id",
                                match=qmodels.MatchValue(value=thread_id)
                            )
                        ]
                    )
                )
            )
        except Exception as e:
            logger.error(f"Failed to clear thread memory: {e}")
            await db.rollback()
            raise

    async def run_memory_expiration_cleanup(self, db: AsyncSession) -> int:
        """Deletes raw interaction memory records older than 30 days that have been summarized."""
        try:
            limit_date = datetime.utcnow() - timedelta(days=30)
            stmt = delete(InteractionMemory).where(
                InteractionMemory.created_at < limit_date,
                InteractionMemory.summary_id != None
            )
            res = await db.execute(stmt)
            await db.commit()
            return res.rowcount
        except Exception as e:
            logger.error(f"Failed to run memory expiration cleanup: {e}")
            await db.rollback()
            return 0
