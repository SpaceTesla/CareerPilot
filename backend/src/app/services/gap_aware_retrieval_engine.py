from __future__ import annotations

import time
from uuid import uuid4, UUID
from datetime import datetime, timezone

from sqlalchemy import select, insert
from sqlalchemy.orm import joinedload

from app.core.logging import get_logger
from app.core.config import settings
from app.services.neo4j_service import Neo4jService
from app.infrastructure.database.connection import SessionLocal
from app.infrastructure.database.models import JobPosting, GapRetrievalLog
from app.utils.event_bus import EventBus
from app.schemas.market_graph import RelatedSkillItem

logger = get_logger(__name__)


class SkillGapEstimate:
    def __init__(self, skill_name: str, difficulty_estimate: str, estimated_learning_hours: int, reason: str):
        self.skill_name = skill_name
        self.difficulty_estimate = difficulty_estimate
        self.estimated_learning_hours = estimated_learning_hours
        self.reason = reason

    def dict(self) -> dict:
        return {
            "skill_name": self.skill_name,
            "difficulty_estimate": self.difficulty_estimate,
            "estimated_learning_hours": self.estimated_learning_hours,
            "reason": self.reason
        }


class GapScoringService:
    """
    Computes penalty deductions for missing skills based on learning difficulty.
    """

    @classmethod
    def calculate_adjusted_score(cls, base_score: float, gaps: list[SkillGapEstimate]) -> float:
        """
        Deducts points from fit score based on skill gaps.
        EASY = -2 points, MODERATE = -5 points, HARD = -10 points.
        """
        penalty = 0.0
        for gap in gaps:
            diff = gap.difficulty_estimate.upper()
            if diff == "EASY":
                penalty += 2.0
            elif diff == "MODERATE":
                penalty += 5.0
            elif diff == "HARD":
                penalty += 10.0
            else:
                penalty += 5.0

        adjusted = max(0.0, min(100.0, base_score - penalty))
        return round(adjusted, 2)


class GapAwareRetrievalEngine:
    """
    Orchestrates gap-aware career matching queries leveraging Neo4j and PostgreSQL.
    """

    @classmethod
    async def analyze_skill_gap(cls, user_skills: list[str], missing_skills: list[str]) -> list[SkillGapEstimate]:
        """
        Evaluates missing skills against candidate's background to estimate difficulty.
        """
        estimates = []
        async with Neo4jService.get_session() as session:
            for skill in missing_skills:
                # Find co-occurrence of this missing skill with user's skills
                query = (
                    "MATCH (s1:Skill {canonical_name: $skill})<-[:HAS_SKILL]-(p:CandidateProfile)-[:HAS_SKILL]->(s2:Skill) "
                    "WHERE s2.canonical_name IN $user_skills "
                    "RETURN s2.canonical_name as related_skill, count(p) as cooccurrence "
                    "ORDER BY cooccurrence DESC "
                    "LIMIT 1"
                )
                try:
                    result = await session.run(query, skill=skill, user_skills=user_skills)
                    record = await result.single()

                    if record:
                        related_skill = record["related_skill"]
                        cooc = record["cooccurrence"]

                        if cooc >= 3:
                            estimates.append(
                                SkillGapEstimate(
                                    skill_name=skill,
                                    difficulty_estimate="EASY",
                                    estimated_learning_hours=12,
                                    reason=f"You have experience with {related_skill}, which is closely related.",
                                )
                            )
                        else:
                            estimates.append(
                                SkillGapEstimate(
                                    skill_name=skill,
                                    difficulty_estimate="MODERATE",
                                    estimated_learning_hours=30,
                                    reason=f"You have experience with {related_skill}, which shares similar paradigms.",
                                )
                            )
                    else:
                        # Fallback for common tech pairings
                        is_easy = False
                        matched_rel = ""
                        for us in user_skills:
                            us_lower = us.lower()
                            s_lower = skill.lower()
                            if (
                                ("python" in us_lower and "langgraph" in s_lower)
                                or ("react" in us_lower and "next.js" in s_lower)
                                or ("javascript" in us_lower and "typescript" in s_lower)
                                or ("pytorch" in us_lower and "tensorflow" in s_lower)
                            ):
                                is_easy = True
                                matched_rel = us
                                break

                        if is_easy:
                            estimates.append(
                                SkillGapEstimate(
                                    skill_name=skill,
                                    difficulty_estimate="EASY",
                                    estimated_learning_hours=15,
                                    reason=f"You have experience with {matched_rel}, which makes learning this skill easy.",
                                )
                            )
                        else:
                            estimates.append(
                                SkillGapEstimate(
                                    skill_name=skill,
                                    difficulty_estimate="HARD",
                                    estimated_learning_hours=75,
                                    reason="This skill represents a new domain or technical stack for your background.",
                                )
                            )
                except Exception as e:
                    logger.warning(f"Error checking skill cooccurrence: {e}")
                    estimates.append(
                        SkillGapEstimate(
                            skill_name=skill,
                            difficulty_estimate="MODERATE",
                            estimated_learning_hours=40,
                            reason="Estimated based on industry standards.",
                        )
                    )
        return estimates

    @classmethod
    async def retrieve_adjacent_opportunities(
        cls, user_id: UUID, limit: int = 10, max_gaps: int = 2
    ) -> list[dict]:
        """
        Finds opportunities where candidate is near-fit with minor gaps, scoring via graph context.
        """
        start_time = time.time()
        adjacent_results = []

        profile_id = str(user_id)  # Using user_id as profile_id mapping for convenience

        # 1. Fetch user profile skills from Neo4j
        user_skills = []
        async with Neo4jService.get_session() as session:
            try:
                res = await session.run(
                    "MATCH (p:CandidateProfile {profile_id: $profile_id})-[h:HAS_SKILL]->(s:Skill) "
                    "RETURN s.canonical_name as name",
                    profile_id=profile_id,
                )
                user_skills = [r["name"] async for r in res]
            except Exception as e:
                logger.error(f"Error fetching user skills from Neo4j: {e}")

        if not user_skills:
            # Fallback to Postgres query for user skills
            from app.infrastructure.database.models import CareerProfile
            with SessionLocal() as db_session:
                prof = db_session.query(CareerProfile).filter(CareerProfile.user_id == str(user_id)).first()
                if prof:
                    user_skills = [s.skill_name for s in prof.skills]
                    profile_id = prof.id

        # 2. Run Neo4j adjacency query
        cypher_query = (
            "MATCH (p:CandidateProfile {profile_id: $profile_id})-[h:HAS_SKILL]->(s:Skill) "
            "WITH p, collect(s.canonical_name) as u_skills "
            "MATCH (j:JobPosting) WHERE j.status = 'ACTIVE' "
            "MATCH (j)-[r:REQUIRES_SKILL]->(js:Skill) "
            "WITH j, u_skills, collect(js.canonical_name) as j_skills "
            "WITH j, [x IN j_skills WHERE NOT x IN u_skills] as missing, j_skills "
            "WHERE size(missing) <= $max_gaps AND size(missing) > 0 "
            "RETURN j.id as job_posting_id, j.title as title, missing, size(j_skills) as total_count"
        )

        neo4j_matches = []
        async with Neo4jService.get_session() as session:
            try:
                res = await session.run(cypher_query, profile_id=profile_id, max_gaps=max_gaps)
                async for record in res:
                    neo4j_matches.append(
                        {
                            "job_posting_id": record["job_posting_id"],
                            "title": record["title"],
                            "missing_skills": record["missing"],
                            "total_skills_count": record["total_count"],
                        }
                    )
            except Exception as e:
                logger.error(f"Error running gap-aware Cypher match: {e}")

        # 3. Retrieve actual job postings from Postgres
        job_ids = [m["job_posting_id"] for m in neo4j_matches]
        job_postings_map = {}

        if job_ids:
            with SessionLocal() as db_session:
                jobs = db_session.query(JobPosting).options(joinedload(JobPosting.company)).filter(JobPosting.id.in_(job_ids)).all()
                for j in jobs:
                    job_postings_map[j.id] = j

        # 4. Formulate scoring and explanations
        for match in neo4j_matches:
            jid = match["job_posting_id"]
            job = job_postings_map.get(jid)
            if not job:
                continue

            missing = match["missing_skills"]
            gaps = await cls.analyze_skill_gap(user_skills, missing)

            # Base fit score calculation (ratio of matching skills)
            total = match["total_skills_count"] or 1
            matching_count = total - len(missing)
            base_score = round((matching_count / total) * 100.0, 1)

            # Apply gap penalty
            fit_score = GapScoringService.calculate_adjusted_score(base_score, gaps)

            # Compile explanation text
            gap_summary = ", ".join([f"{g.skill_name} ({g.difficulty_estimate.lower()})" for g in gaps])
            explanation = (
                f"{int(fit_score)}% Match. You possess all core requirements. "
                f"Adding {gap_summary} would make you a strong candidate."
            )

            adjacent_results.append(
                {
                    "job_posting": {
                        "id": job.id,
                        "title": job.title,
                        "company_name": job.company.name if job.company else "Unknown",
                        "location": job.location,
                    },
                    "fit_score": fit_score,
                    "addressable_gaps": [g.dict() for g in gaps],
                    "explanation": explanation,
                }
            )

        # Sort results by fit score descending
        adjacent_results.sort(key=lambda x: x["fit_score"], reverse=True)
        adjacent_results = adjacent_results[:limit]

        duration_ms = int((time.time() - start_time) * 1000)

        # 5. Log operation to gap_retrieval_logs
        try:
            with SessionLocal() as db_session:
                log_entry = GapRetrievalLog(
                    id=str(uuid4()),
                    user_id=str(user_id),
                    adjacent_results_count=len(adjacent_results),
                    pipeline_duration_ms=duration_ms,
                )
                db_session.add(log_entry)
                db_session.commit()
        except Exception as log_err:
            logger.error(f"Failed to save gap retrieval log entry: {log_err}")

        # 6. Publish Event
        try:
            await EventBus.publish(
                "retrieval.gap_aware_run_completed",
                {
                    "event_id": str(uuid4()),
                    "event_type": "retrieval.gap_aware_run_completed",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "payload": {
                        "user_id": str(user_id),
                        "results_count": len(adjacent_results),
                        "duration_ms": duration_ms,
                    },
                },
            )
        except Exception as ev_err:
            logger.error(f"Failed to publish retrieval.gap_aware_run_completed event: {ev_err}")

        return adjacent_results
