from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.rag.embeddings.service import embedding_service
from app.services.agent.models import HybridRetrievalRequest, RetrievalCandidate
from langchain_google_genai import ChatGoogleGenerativeAI

logger = get_logger(__name__)


class HybridRetrievalService:
    """
    Implements a multi-stage search pipeline:
    1. BM25 search on PostgreSQL.
    2. Dense vector search on Qdrant.
    3. Fusion using Reciprocal Rank Fusion (RRF).
    4. Reranking using Gemini as a Cross-Encoder model.
    """

    def __init__(self) -> None:
        self.qdrant = QdrantClient(url=settings.qdrant_url)
        self.collection_name = "job_postings_vectors"
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

    async def generate_embeddings(self, text: str) -> List[float]:
        emb = await embedding_service.embed_text(text)
        return emb or [0.0] * 768

    async def index_job_posting(self, job_id: UUID, title: str, company_name: str, description: str, skills: List[str], location: str) -> None:
        """Helper to index job posting into Qdrant."""
        try:
            combined_text = f"{title} | {company_name} | {description} | {' '.join(skills)}"
            vector = await self.generate_embeddings(combined_text)
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[
                    qmodels.PointStruct(
                        id=str(job_id),
                        vector=vector,
                        payload={
                            "job_id": str(job_id),
                            "title": title,
                            "company_name": company_name,
                            "skills": skills,
                            "location": location,
                        }
                    )
                ]
            )
        except Exception as e:
            logger.error(f"Failed to index job posting in Qdrant: {e}")

    async def search(self, db: AsyncSession, request: HybridRetrievalRequest) -> List[RetrievalCandidate]:
        # 1. Get Query Vector
        query_vector = await self.generate_embeddings(request.query)

        # 2. Vector Search (Qdrant)
        vector_results = []
        try:
            q_res = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=request.rerank_top_k
            )
            for idx, hit in enumerate(q_res):
                vector_results.append({
                    "job_id": UUID(hit.payload["job_id"]),
                    "title": hit.payload["title"],
                    "company_name": hit.payload["company_name"],
                    "rank": idx + 1,
                    "score": hit.score
                })
        except Exception as e:
            logger.warning(f"Qdrant vector search failed, falling back to BM25: {e}")

        # 3. BM25 Search (Postgres)
        bm25_results = []
        try:
            # Sanitize search query for plainto_tsquery
            cleaned_query = request.query.replace("'", " ").replace('"', ' ')
            sql = text("""
                SELECT jp.id, jp.title, c.name as company_name, ts_rank_cd(jp.search_vector, plainto_tsquery('english', :query)) as rank
                FROM job_postings jp
                JOIN companies c ON jp.company_id = c.id
                WHERE jp.search_vector @@ plainto_tsquery('english', :query)
                  AND jp.is_active = true
                ORDER BY rank DESC
                LIMIT :limit
            """)
            result = await db.execute(sql, {"query": cleaned_query, "limit": request.rerank_top_k})
            for idx, row in enumerate(result.fetchall()):
                bm25_results.append({
                    "job_id": row.id if isinstance(row.id, UUID) else UUID(row.id),
                    "title": row.title,
                    "company_name": row.company_name,
                    "rank": idx + 1
                })
        except Exception as e:
            logger.warning(f"Postgres BM25 search failed, falling back to Vector: {e}")

        if not vector_results and not bm25_results:
            return []

        # 4. Reciprocal Rank Fusion (RRF)
        # RRF_score = sum(1 / (60 + rank))
        candidates_map = {}
        for r in vector_results:
            jid = r["job_id"]
            candidates_map[jid] = {
                "job_id": jid,
                "title": r["title"],
                "company_name": r["company_name"],
                "vector_rank": r["rank"],
                "bm25_rank": None,
                "retrieval_sources": ["vector"]
            }

        for r in bm25_results:
            jid = r["job_id"]
            if jid in candidates_map:
                candidates_map[jid]["bm25_rank"] = r["rank"]
                candidates_map[jid]["retrieval_sources"].append("bm25")
            else:
                candidates_map[jid] = {
                    "job_id": jid,
                    "title": r["title"],
                    "company_name": r["company_name"],
                    "vector_rank": None,
                    "bm25_rank": r["rank"],
                    "retrieval_sources": ["bm25"]
                }

        # Calculate RRF Scores
        k = 60
        merged_candidates = []
        for jid, cand in candidates_map.items():
            rrf_score = 0.0
            if cand["vector_rank"] is not None:
                rrf_score += 1.0 / (k + cand["vector_rank"])
            if cand["bm25_rank"] is not None:
                rrf_score += 1.0 / (k + cand["bm25_rank"])
            cand["rrf_score"] = rrf_score
            merged_candidates.append(cand)

        # Sort by RRF score descending and take top rerank_top_k
        merged_candidates.sort(key=lambda x: x["rrf_score"], reverse=True)
        top_candidates = merged_candidates[:request.rerank_top_k]

        # 5. Rerank using Gemini (Cross-Encoder style)
        reranked_results = []
        try:
            # We fetch job descriptions for top candidates to rerank accurately
            job_ids = [str(c["job_id"]) for c in top_candidates]
            desc_query = text("SELECT id, description FROM job_postings WHERE id = ANY(:ids)")
            desc_res = await db.execute(desc_query, {"ids": job_ids})
            descriptions = {row.id: row.description for row in desc_res.fetchall()}

            candidates_data = []
            for cand in top_candidates:
                jid_str = str(cand["job_id"])
                desc = descriptions.get(cand["job_id"]) or descriptions.get(jid_str) or ""
                candidates_data.append({
                    "id": jid_str,
                    "title": cand["title"],
                    "company_name": cand["company_name"],
                    "description": desc[:500]  # truncate to prevent context limits
                })

            prompt = f"""
            Task: Rerank the following job postings based on their relevance to the user's query.
            Query: "{request.query}"

            Job Candidates:
            {json.dumps(candidates_data, indent=2)}

            Output a valid JSON array of objects. Each object must contain 'id' and 'relevance_score' (a float between 0.0 and 1.0).
            Order them by relevance_score descending. Do not include any other text or code blocks.
            """
            response = await self.llm.ainvoke(prompt)
            content = response.content
            if isinstance(content, str):
                # strip markdown if LLM outputs it
                if content.strip().startswith("```"):
                    lines = content.strip().split("\n")
                    content = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])
                scores = json.loads(content)
                scores_map = {UUID(s["id"]): float(s["relevance_score"]) for s in scores}
            else:
                scores_map = {}

            for cand in top_candidates:
                score = scores_map.get(cand["job_id"], cand["rrf_score"])
                reranked_results.append(
                    RetrievalCandidate(
                        job_id=cand["job_id"],
                        title=cand["title"],
                        company_name=cand["company_name"],
                        bm25_rank=cand["bm25_rank"],
                        vector_rank=cand["vector_rank"],
                        rrf_score=cand["rrf_score"],
                        final_score=score,
                        retrieval_sources=cand["retrieval_sources"]
                    )
                )

        except Exception as e:
            logger.warning(f"Gemini reranking failed, falling back to RRF scores: {e}")
            for cand in top_candidates:
                # normalize RRF score to [0, 1] range roughly
                normalized_score = min(cand["rrf_score"] * 30.0, 1.0)
                reranked_results.append(
                    RetrievalCandidate(
                        job_id=cand["job_id"],
                        title=cand["title"],
                        company_name=cand["company_name"],
                        bm25_rank=cand["bm25_rank"],
                        vector_rank=cand["vector_rank"],
                        rrf_score=cand["rrf_score"],
                        final_score=normalized_score,
                        retrieval_sources=cand["retrieval_sources"]
                    )
                )

        # Sort by final score descending and limit results
        reranked_results.sort(key=lambda x: x.final_score, reverse=True)
        return reranked_results[:request.limit]
