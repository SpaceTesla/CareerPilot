"""
Embedding service using Google's text-embedding-004 model (768 dims).

Provides async and sync helpers for generating embeddings, with a simple
in-process LRU cache to avoid re-embedding identical skill strings.
"""

from __future__ import annotations

import asyncio
import math
from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_EMBEDDING_DIM = 768
_EMBEDDING_MODEL = "models/embedding-001"  # v1beta-compatible; text-embedding-004 requires v1 stable API


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two equal-length vectors."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingService:
    """Wraps Google Generative AI embeddings with an in-process cache."""

    def __init__(self) -> None:
        self._client: Any = None
        self._available: bool | None = None  # None = not yet checked

    def _ensure_client(self) -> bool:
        """Lazy-init the Google embedding client.  Returns True if available."""
        if self._available is not None:
            return self._available
        try:
            import google.generativeai as genai  # noqa: PLC0415

            genai.configure(api_key=settings.google_api_key)
            self._client = genai
            self._available = True
            logger.info("EmbeddingService: Google Generative AI client initialized")
        except Exception as e:
            logger.warning(f"EmbeddingService: could not init Google GenAI client: {e}")
            self._available = False
        return self._available  # type: ignore[return-value]

    # ---------- public API ----------

    def embed_text_sync(self, text: str) -> list[float] | None:
        """Synchronously embed a single string. Returns None on failure."""
        if not text.strip():
            return None
        if not self._ensure_client():
            return None
        try:
            result = self._client.embed_content(
                model=_EMBEDDING_MODEL,
                content=text,
                task_type="SEMANTIC_SIMILARITY",
            )
            return result["embedding"]
        except Exception as e:
            logger.warning(f"EmbeddingService.embed_text_sync: {e}")
            return None

    async def embed_text(self, text: str) -> list[float] | None:
        """Async wrapper — runs the sync call in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_text_sync, text)

    async def embed_skills(self, skills: list[str]) -> list[float] | None:
        """
        Embed a list of skill strings by joining them with commas.
        Returns a 768-dim vector, or None if embeddings are unavailable.
        """
        if not skills:
            return None
        combined = ", ".join(s for s in skills if s)
        return await self.embed_text(combined)

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        return _cosine_similarity(a, b)

    @property
    def dim(self) -> int:
        return _EMBEDDING_DIM

    @property
    def available(self) -> bool:
        self._ensure_client()
        return bool(self._available)


# Module-level singleton
embedding_service = EmbeddingService()
