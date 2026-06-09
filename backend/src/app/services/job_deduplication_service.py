from __future__ import annotations

import json
import math
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import (
    Company,
    DedupeAuditLog,
    JobDuplicate,
    JobPosting,
)
from app.utils.event_bus import EventBus

logger = get_logger(__name__)


class JobDeduplicationService:
    """
    Job Deduplication Service (F2.2). Compares incoming job postings against
    active postings, auto-merging duplicates (>0.85) and queueing marginal duplicates (0.75-0.85).
    """

    @staticmethod
    def clean_title(title: str) -> str:
        """Strips seniority, numbers, and cleans whitespace."""
        t = title.lower().strip()
        tags = (
            r"\bsr\b",
            r"\bsenior\b",
            r"\bjunior\b",
            r"\bjr\b",
            r"\bi{2,3}\b",
            r"\biv\b",
            r"\bstaff\b",
            r"\blead\b",
            r"\bprincipal\b",
        )
        for tag in tags:
            t = re.sub(tag, "", t)
        return re.sub(r"\s+", " ", t).strip()

    @staticmethod
    def clean_company(name: str) -> str:
        """Removes corporate extensions like LLC, Inc., Corp."""
        c = name.lower().replace(".", "").replace(",", "").strip()
        suffixes = (
            r"\bllc\b",
            r"\binc\b",
            r"\bcorp\b",
            r"\bcorporation\b",
            r"\bltd\b",
            r"\bco\b",
            r"\blimited\b",
        )
        for suffix in suffixes:
            c = re.sub(suffix, "", c)
        return re.sub(r"\s+", " ", c).strip()


    @staticmethod
    def calculate_jaccard_similarity(s1: str, s2: str) -> float:
        """Computes Jaccard similarity between two token sets."""
        set1 = set(re.findall(r"\w+", s1.lower()))
        set2 = set(re.findall(r"\w+", s2.lower()))
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        return len(set1.intersection(set2)) / len(set1.union(set2))

    @staticmethod
    def calculate_cosine_similarity(text1: str, text2: str) -> float:
        """Computes Cosine similarity of token frequencies."""
        words1 = re.findall(r"\w+", text1.lower())
        words2 = re.findall(r"\w+", text2.lower())
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0

        freq1 = {}
        for w in words1:
            freq1[w] = freq1.get(w, 0) + 1
        freq2 = {}
        for w in words2:
            freq2[w] = freq2.get(w, 0) + 1

        dot = sum(v * freq2.get(w, 0) for w, v in freq1.items())
        mag1 = math.sqrt(sum(v**2 for v in freq1.values()))
        mag2 = math.sqrt(sum(v**2 for v in freq2.values()))

        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    @staticmethod
    def generate_fingerprint(title: str, company: str, description: str) -> str:
        """
        Generates a stable SHA-256 fingerprint for a cleaned job posting description/details.
        """
        import hashlib

        text = f"{title.lower().strip()}|{company.lower().strip()}|{description.lower().strip()[:200]}"
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    async def evaluate_and_deduplicate(
        db: AsyncSession, incoming_job: JobPosting
    ) -> Optional[str]:
        """
        Compares incoming_job against existing postings from the same company and location.
        Merges automatically if similarity > 0.85, queues for review if between 0.75 and 0.85.
        Returns the primary job posting ID if merged, else None.
        """
        # Exclude comparing the job with itself
        stmt = (
            select(JobPosting)
            .where(
                JobPosting.company_id == incoming_job.company_id,
                JobPosting.id != incoming_job.id,
                JobPosting.is_primary == True,  # noqa: E712 - compare with active primaries
            )
        )
        res = await db.execute(stmt)
        active_jobs = res.scalars().all()

        best_match: Optional[JobPosting] = None
        best_score = 0.0
        best_similarities: Dict[str, float] = {}

        for existing in active_jobs:
            # Title similarity (Jaccard of cleaned tokens)
            t_sim = JobDeduplicationService.calculate_jaccard_similarity(
                JobDeduplicationService.clean_title(incoming_job.raw_title),
                JobDeduplicationService.clean_title(existing.raw_title),
            )

            # Company similarity (We already filtered by company_id, so it is 1.0)
            c_sim = 1.0

            # Description similarity (Cosine of tokens)
            d_sim = JobDeduplicationService.calculate_cosine_similarity(
                incoming_job.description, existing.description
            )

            # Location similarity multiplier / boundary (e.g. strict location mismatch drops score)
            # If locations differ, we apply a location penalty
            loc_penalty = 1.0
            if incoming_job.location.lower() != existing.location.lower():
                # If one is remote and the other is local, allow it with a slight penalty
                if "remote" in incoming_job.location.lower() or "remote" in existing.location.lower():
                    loc_penalty = 0.90
                else:
                    loc_penalty = 0.70

            # Composite Score
            score = ((0.3 * t_sim) + (0.3 * c_sim) + (0.4 * d_sim)) * loc_penalty

            if score > best_score:
                best_score = score
                best_match = existing
                best_similarities = {"title": t_sim, "company": c_sim, "description": d_sim}

        if best_match and best_score >= 0.75:
            if best_score > 0.85:
                # 1. AUTO MERGE
                incoming_job.is_primary = False
                incoming_job.is_active = False
                incoming_job.merged_into_id = best_match.id
                incoming_job.deduplicated_to_id = best_match.id

                # Save duplicate record
                dup = JobDuplicate(
                    id=str(uuid4()),
                    primary_job_id=best_match.id,
                    duplicate_job_id=incoming_job.id,
                    confidence_score=Decimal(str(round(best_score, 3))),
                    title_similarity=Decimal(str(round(best_similarities["title"], 3))),
                    company_similarity=Decimal(str(round(best_similarities["company"], 3))),
                    description_similarity=Decimal(
                        str(round(best_similarities["description"], 3))
                    ),
                    status="AUTO_MERGED",
                )
                db.add(dup)

                # Save audit log
                audit = DedupeAuditLog(
                    id=str(uuid4()),
                    action="MERGE",
                    primary_job_id=best_match.id,
                    merged_job_id=incoming_job.id,
                    merge_details={
                        "title": incoming_job.raw_title,
                        "url": incoming_job.url,
                        "description_length": len(incoming_job.description),
                        "score": best_score,
                    },
                )
                db.add(audit)
                await db.flush()

                # Publish merged event
                await EventBus.publish(
                    "market.jobs.merged",
                    {
                        "primary_job_id": best_match.id,
                        "merged_job_id": incoming_job.id,
                        "source_merged": incoming_job.source,
                        "primary_source": best_match.source,
                    },
                )

                logger.info(f"Auto-merged job {incoming_job.id} into {best_match.id} (Score: {best_score:.3f})")
                return best_match.id
            else:
                # 2. QUEUE FOR REVIEW (0.75 to 0.85)
                dup = JobDuplicate(
                    id=str(uuid4()),
                    primary_job_id=best_match.id,
                    duplicate_job_id=incoming_job.id,
                    confidence_score=Decimal(str(round(best_score, 3))),
                    title_similarity=Decimal(str(round(best_similarities["title"], 3))),
                    company_similarity=Decimal(str(round(best_similarities["company"], 3))),
                    description_similarity=Decimal(
                        str(round(best_similarities["description"], 3))
                    ),
                    status="PENDING_REVIEW",
                )
                db.add(dup)
                await db.flush()
                logger.info(
                    f"Flagged potential duplicate job {incoming_job.id} matching {best_match.id} "
                    f"(Score: {best_score:.3f}). Queued for review."
                )

        return None

    @staticmethod
    async def resolve_duplicate_pair(
        db: AsyncSession, duplicate_pair_id: str, action: str, operator_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approves or rejects a merge proposal from the pending duplicates review queue.
        """
        # Fetch duplicate pair
        stmt = select(JobDuplicate).where(JobDuplicate.id == duplicate_pair_id)
        res = await db.execute(stmt)
        dup = res.scalar_one_or_none()

        if not dup:
            raise ValueError("Duplicate job pair not found.")

        if dup.status != "PENDING_REVIEW":
            raise ValueError(f"Duplicate job pair is already resolved (status: {dup.status}).")

        primary_job_stmt = select(JobPosting).where(JobPosting.id == dup.primary_job_id)
        duplicate_job_stmt = select(JobPosting).where(JobPosting.id == dup.duplicate_job_id)

        primary_job = (await db.execute(primary_job_stmt)).scalar_one_or_none()
        duplicate_job = (await db.execute(duplicate_job_stmt)).scalar_one_or_none()

        if not primary_job or not duplicate_job:
            raise ValueError("Primary or duplicate job posting record missing.")

        if action.upper() == "APPROVE":
            # Apply merge
            duplicate_job.is_primary = False
            duplicate_job.is_active = False
            duplicate_job.merged_into_id = primary_job.id
            duplicate_job.deduplicated_to_id = primary_job.id

            dup.status = "APPROVED"
            dup.resolved_at = datetime.utcnow()
            dup.reviewed_by = operator_id

            # Save audit log
            audit = DedupeAuditLog(
                id=str(uuid4()),
                action="MERGE",
                primary_job_id=primary_job.id,
                merged_job_id=duplicate_job.id,
                merge_details={
                    "title": duplicate_job.raw_title,
                    "url": duplicate_job.url,
                    "description_length": len(duplicate_job.description),
                    "operator_resolution": True,
                },
            )
            db.add(audit)

            # Publish merged event
            await EventBus.publish(
                "market.jobs.merged",
                {
                    "primary_job_id": primary_job.id,
                    "merged_job_id": duplicate_job.id,
                    "source_merged": duplicate_job.source,
                    "primary_source": primary_job.source,
                },
            )
        else:
            dup.status = "REJECTED"
            dup.resolved_at = datetime.utcnow()
            dup.reviewed_by = operator_id

            # Save audit log
            audit = DedupeAuditLog(
                id=str(uuid4()),
                action="IGNORE",
                primary_job_id=primary_job.id,
                merged_job_id=duplicate_job.id,
                merge_details={"operator_resolution": False, "action": "REJECT"},
            )
            db.add(audit)

        await db.flush()

        return {
            "duplicate_pair_id": dup.id,
            "status": dup.status,
            "primary_job_id": primary_job.id,
            "merged_job_id": duplicate_job.id if action.upper() == "APPROVE" else None,
            "message": "Jobs successfully merged." if action.upper() == "APPROVE" else "Merge proposal rejected.",
        }
