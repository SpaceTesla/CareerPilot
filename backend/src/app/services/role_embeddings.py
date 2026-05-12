"""
Pre-computed and cached role-requirement embeddings.

Role requirement skill lists are embedded once at first use and cached
in memory for the lifetime of the process.  The gap score returned is a
hybrid:

  • Semantic score  — cosine similarity between resume skills embedding
                      and role requirements embedding (0-100).
  • Exact score     — set intersection (used for the displayed lists of
                      missing_required / missing_recommended).

The final gap_score exposed to callers uses the semantic approach when
embeddings are available, falling back to the exact approach otherwise.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.logging import get_logger
from app.infrastructure.rag.embeddings.service import embedding_service

logger = get_logger(__name__)

# ── Role requirement definitions ─────────────────────────────────────────────

ROLE_REQUIREMENTS: dict[str, dict[str, list[str]]] = {
    "backend": {
        "required": ["Python", "SQL", "API", "Database"],
        "recommended": ["Django", "Flask", "PostgreSQL", "REST", "Docker"],
    },
    "frontend": {
        "required": ["JavaScript", "HTML", "CSS", "React"],
        "recommended": ["TypeScript", "Next.js", "TailwindCSS", "Git"],
    },
    "fullstack": {
        "required": ["JavaScript", "Python", "React", "SQL"],
        "recommended": ["Node.js", "TypeScript", "Docker", "AWS"],
    },
    "devops": {
        "required": ["Docker", "CI/CD", "Linux", "Git"],
        "recommended": ["Kubernetes", "AWS", "Terraform", "Jenkins"],
    },
    "data scientist": {
        "required": ["Python", "SQL", "Statistics", "Machine Learning"],
        "recommended": ["Pandas", "NumPy", "Scikit-learn", "TensorFlow", "Jupyter"],
    },
    "ml engineer": {
        "required": ["Python", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch"],
        "recommended": ["MLOps", "Docker", "Kubernetes", "AWS", "Data Pipelines",
                        "Model Deployment", "Hugging Face", "LangChain"],
    },
    "ai engineer": {
        "required": ["Python", "Machine Learning", "Deep Learning", "NLP", "Computer Vision"],
        "recommended": ["TensorFlow", "PyTorch", "LLM", "RAG", "Vector Databases",
                        "LangChain", "Transformers"],
    },
    "data engineer": {
        "required": ["Python", "SQL", "ETL", "Data Pipelines"],
        "recommended": ["Apache Spark", "Airflow", "Kafka", "AWS", "Snowflake", "dbt"],
    },
    "cloud": {
        "required": ["Cloud Platforms", "Linux", "Networking", "Security"],
        "recommended": ["AWS", "Azure", "GCP", "Terraform", "Kubernetes", "CI/CD"],
    },
    "mobile": {
        "required": ["Mobile Development", "UI/UX", "API Integration"],
        "recommended": ["React Native", "Flutter", "Swift", "Kotlin", "Firebase"],
    },
    "general": {
        "required": ["Programming", "Problem Solving"],
        "recommended": ["Git", "Communication", "Teamwork"],
    },
}

# Cache: role_key → embedding vector
_role_embedding_cache: dict[str, list[float] | None] = {}
_cache_lock = asyncio.Lock()


def _normalize_role(role: str | None) -> str:
    """Map free-text role to one of the keys in ROLE_REQUIREMENTS."""
    if not role:
        return "general"
    r = role.lower()
    if "backend" in r:
        return "backend"
    if "frontend" in r or "front-end" in r:
        return "frontend"
    if "fullstack" in r or "full-stack" in r or "full stack" in r:
        return "fullstack"
    if "devops" in r or "dev ops" in r:
        return "devops"
    if "data scientist" in r or "data science" in r:
        return "data scientist"
    if "ml engineer" in r or "machine learning" in r:
        return "ml engineer"
    if "ai engineer" in r or "artificial intelligence" in r:
        return "ai engineer"
    if "data engineer" in r:
        return "data engineer"
    if "cloud" in r or "aws" in r or "azure" in r or "gcp" in r:
        return "cloud"
    if "mobile" in r or "ios" in r or "android" in r:
        return "mobile"
    return "general"


def get_role_requirements(role: str | None) -> dict[str, list[str]]:
    """Return the requirements dict for the normalised role."""
    key = _normalize_role(role)
    return ROLE_REQUIREMENTS.get(key, ROLE_REQUIREMENTS["general"])


async def _get_role_embedding(role_key: str) -> list[float] | None:
    """Return (and cache) the embedding for a role's combined skill list."""
    if role_key in _role_embedding_cache:
        return _role_embedding_cache[role_key]

    async with _cache_lock:
        # Double-check after acquiring lock
        if role_key in _role_embedding_cache:
            return _role_embedding_cache[role_key]

        req = ROLE_REQUIREMENTS.get(role_key, ROLE_REQUIREMENTS["general"])
        all_skills = req["required"] + req["recommended"]
        embedding = await embedding_service.embed_skills(all_skills)
        _role_embedding_cache[role_key] = embedding
        return embedding


async def compute_semantic_gap_score(
    resume_skills: list[str],
    role: str | None,
    resume_embedding: list[float] | None = None,
) -> float:
    """
    Compute a semantic skills-gap score (0-100) using cosine similarity
    between the resume skills embedding and the role requirements embedding.

    Falls back to the exact set-intersection score when embeddings are
    unavailable.
    """
    role_key = _normalize_role(role)
    req = ROLE_REQUIREMENTS.get(role_key, ROLE_REQUIREMENTS["general"])
    required = set(req["required"])
    recommended = set(req["recommended"])
    current = set(resume_skills)

    # Exact fallback score
    all_required = required | recommended
    matching = current & all_required
    exact_score = (len(matching) / len(all_required) * 100) if all_required else 0.0

    if not embedding_service.available:
        return round(exact_score, 1)

    # Get or compute resume embedding
    res_emb = resume_embedding
    if res_emb is None:
        res_emb = await embedding_service.embed_skills(list(current))
    if res_emb is None:
        return round(exact_score, 1)

    role_emb = await _get_role_embedding(role_key)
    if role_emb is None:
        return round(exact_score, 1)

    similarity = embedding_service.cosine_similarity(res_emb, role_emb)
    # Convert cosine similarity [-1,1] → 0-100 score
    semantic_score = max(0.0, min(100.0, (similarity + 1) / 2 * 100))

    # Blend: 60% semantic, 40% exact (named skills are still informative)
    blended = 0.6 * semantic_score + 0.4 * exact_score
    return round(blended, 1)
