from __future__ import annotations

import time
import datetime
from collections import defaultdict
from uuid import uuid4

from sqlalchemy.orm import joinedload

from app.core.logging import get_logger
from app.services.neo4j_service import Neo4jService
from app.utils.event_bus import EventBus

logger = get_logger(__name__)


class GraphIngestionPipeline:
    """
    Asynchronous data synchronization pipeline from PostgreSQL to Neo4j.
    """

    @classmethod
    async def sync_profile_nodes(cls, profiles: list[dict]) -> None:
        """
        Syncs candidate profiles and skills taxonomy to Neo4j.
        """
        async with Neo4jService.get_session() as session:
            for p in profiles:
                profile_id = p["profile_id"]
                # 1. Merge CandidateProfile
                await session.run(
                    "MERGE (p:CandidateProfile {profile_id: $profile_id}) "
                    "ON CREATE SET p.anonymized = true",
                    profile_id=profile_id,
                )

                # 2. Merge Skills and HAS_SKILL relationships
                for s in p.get("skills", []):
                    skill_name = s["skill_name"]
                    await session.run(
                        "MERGE (sk:Skill {canonical_name: $skill_name}) "
                        "ON CREATE SET sk.category = $category",
                        skill_name=skill_name,
                        category=s.get("category", "Technical"),
                    )
                    await session.run(
                        "MATCH (p:CandidateProfile {profile_id: $profile_id}), "
                        "(sk:Skill {canonical_name: $skill_name}) "
                        "MERGE (p)-[r:HAS_SKILL]->(sk)",
                        profile_id=profile_id,
                        skill_name=skill_name,
                    )

                # 3. Merge experiences, company, and role nodes
                for exp in p.get("experiences", []):
                    company_name = exp["company_name"]
                    job_title = exp["job_title"]
                    start_date = str(exp["start_date"])
                    end_date = str(exp["end_date"]) if exp.get("end_date") else None

                    # Merge Company
                    await session.run(
                        "MERGE (c:Company {name: $company_name})",
                        company_name=company_name,
                    )

                    # Merge Role
                    await session.run(
                        "MERGE (ro:Role {name: $job_title})",
                        job_title=job_title,
                    )

                    # Merge EMPLOYED_AT
                    await session.run(
                        "MATCH (p:CandidateProfile {profile_id: $profile_id}), "
                        "(c:Company {name: $company_name}) "
                        "MERGE (p)-[r:EMPLOYED_AT]->(c) "
                        "SET r.start_date = $start_date, r.end_date = $end_date",
                        profile_id=profile_id,
                        company_name=company_name,
                        start_date=start_date,
                        end_date=end_date,
                    )

                    # Merge HIRED_ROLE
                    await session.run(
                        "MATCH (c:Company {name: $company_name}), "
                        "(ro:Role {name: $job_title}) "
                        "MERGE (c)-[r:HIRED_ROLE]->(ro)",
                        company_name=company_name,
                        job_title=job_title,
                    )

    @classmethod
    async def sync_transition_edges(cls, experiences: list[dict]) -> None:
        """
        Pairs sequential experience records to build/update transition edges.
        """
        profile_exps = defaultdict(list)
        for exp in experiences:
            profile_exps[exp["profile_id"]].append(exp)

        async with Neo4jService.get_session() as session:
            transitions = defaultdict(list)

            for profile_id, exps in profile_exps.items():

                def get_start_date(x):
                    sd = x.get("start_date")
                    if isinstance(sd, str):
                        return datetime.date.fromisoformat(sd)
                    elif isinstance(sd, datetime.datetime):
                        return sd.date()
                    return sd

                def get_end_date(x):
                    ed = x.get("end_date")
                    if isinstance(ed, str):
                        return datetime.date.fromisoformat(ed)
                    elif isinstance(ed, datetime.datetime):
                        return ed.date()
                    return ed

                # Sort experiences ascending
                sorted_exps = sorted(exps, key=get_start_date)

                for i in range(len(sorted_exps) - 1):
                    exp_from = sorted_exps[i]
                    exp_to = sorted_exps[i + 1]

                    role_from = exp_from["job_title"]
                    role_to = exp_to["job_title"]

                    sd_from = get_start_date(exp_from)
                    ed_from = get_end_date(exp_from)

                    if not ed_from:
                        ed_from = get_start_date(exp_to)

                    duration_days = (ed_from - sd_from).days
                    duration_months = max(1.0, round(duration_days / 30.4, 1))

                    transitions[(role_from, role_to)].append(duration_months)

            for (role_from, role_to), durations in transitions.items():
                freq = len(durations)
                avg_duration = round(sum(durations) / freq, 1)
                confidence = round(min(1.0, 0.5 + (freq * 0.1)), 2)

                await session.run("MERGE (:Role {name: $role_from})", role_from=role_from)
                await session.run("MERGE (:Role {name: $role_to})", role_to=role_to)

                await session.run(
                    "MATCH (rf:Role {name: $role_from}), (rt:Role {name: $role_to}) "
                    "MERGE (rf)-[t:TRANSITIONED_TO]->(rt) "
                    "ON CREATE SET t.frequency_count = $freq, "
                    "t.avg_duration_months = $avg_duration, t.confidence = $confidence "
                    "ON MATCH SET t.frequency_count = $freq, "
                    "t.avg_duration_months = $avg_duration, t.confidence = $confidence",
                    role_from=role_from,
                    role_to=role_to,
                    freq=freq,
                    avg_duration=avg_duration,
                    confidence=confidence,
                )

    @classmethod
    async def sync_job_postings_skills(cls, job_postings: list[dict]) -> None:
        """
        Syncs job postings requirements as REQUIRES_SKILL relationships.
        """
        async with Neo4jService.get_session() as session:
            for jp in job_postings:
                job_id = jp.get("id") or str(uuid4())
                title = jp["title"]
                company_name = jp["company_name"]
                status = jp.get("status", "ACTIVE")
                skills = jp.get("skills", [])

                await session.run("MERGE (r:Role {name: $title})", title=title)
                await session.run("MERGE (c:Company {name: $company_name})", company_name=company_name)

                # Merge JobPosting node
                await session.run(
                    "MERGE (j:JobPosting {id: $job_id}) "
                    "ON CREATE SET j.title = $title, j.company_name = $company_name, j.status = $status "
                    "ON MATCH SET j.title = $title, j.company_name = $company_name, j.status = $status",
                    job_id=job_id,
                    title=title,
                    company_name=company_name,
                    status=status,
                )

                for s in skills:
                    skill_name = s["skill_name"]
                    relevance_score = s.get("relevance_score", 1.0)
                    is_mandatory = s.get("is_mandatory", True)

                    await session.run(
                        "MERGE (sk:Skill {canonical_name: $skill_name})",
                        skill_name=skill_name,
                    )

                    # JobPosting -> Skill
                    await session.run(
                        "MATCH (j:JobPosting {id: $job_id}), (sk:Skill {canonical_name: $skill_name}) "
                        "MERGE (j)-[req:REQUIRES_SKILL]->(sk) "
                        "ON CREATE SET req.relevance_score = $relevance_score, req.is_mandatory = $is_mandatory "
                        "ON MATCH SET req.relevance_score = $relevance_score, req.is_mandatory = $is_mandatory",
                        job_id=job_id,
                        skill_name=skill_name,
                        relevance_score=relevance_score,
                        is_mandatory=is_mandatory,
                    )

                    # Role -> Skill
                    await session.run(
                        "MATCH (ro:Role {name: $title}), (sk:Skill {canonical_name: $skill_name}) "
                        "MERGE (ro)-[req:REQUIRES_SKILL]->(sk) "
                        "ON CREATE SET req.relevance_score = $relevance_score, req.is_mandatory = $is_mandatory "
                        "ON MATCH SET req.relevance_score = $relevance_score, req.is_mandatory = $is_mandatory",
                        title=title,
                        skill_name=skill_name,
                        relevance_score=relevance_score,
                        is_mandatory=is_mandatory,
                    )

                    # Company -> Skill
                    await session.run(
                        "MATCH (c:Company {name: $company_name}), (sk:Skill {canonical_name: $skill_name}) "
                        "MERGE (c)-[req:REQUIRES_SKILL]->(sk) "
                        "ON CREATE SET req.relevance_score = $relevance_score, req.is_mandatory = $is_mandatory "
                        "ON MATCH SET req.relevance_score = $relevance_score, req.is_mandatory = $is_mandatory",
                        company_name=company_name,
                        skill_name=skill_name,
                        relevance_score=relevance_score,
                        is_mandatory=is_mandatory,
                    )

    @classmethod
    async def sync_all_data(cls) -> dict:
        """
        Queries all profile and job posting records from PostgreSQL and syncs them to Neo4j.
        """
        from app.infrastructure.database.connection import SessionLocal
        from app.infrastructure.database.models import (
            CareerProfile,
            JobPosting,
            NormalizedSkill,
            JobPostingSkill,
        )

        start_time = time.time()

        with SessionLocal() as db_session:
            profiles = (
                db_session.query(CareerProfile)
                .options(
                    joinedload(CareerProfile.skills),
                    joinedload(CareerProfile.experiences),
                )
                .all()
            )

            profile_dicts = []
            experiences_list = []
            for p in profiles:
                skills_dicts = [{"skill_name": sk.skill_name, "category": "Technical"} for sk in p.skills]
                exps_dicts = []
                for exp in p.experiences:
                    exp_d = {
                        "profile_id": p.id,
                        "company_name": exp.company_name,
                        "job_title": exp.job_title,
                        "start_date": exp.start_date,
                        "end_date": exp.end_date,
                    }
                    exps_dicts.append(exp_d)
                    experiences_list.append(exp_d)

                profile_dicts.append(
                    {
                        "profile_id": p.id,
                        "skills": skills_dicts,
                        "experiences": exps_dicts,
                    }
                )

            # Map normalized skills to avoid slow ORM traversing
            skills_by_id = {s.id: s for s in db_session.query(NormalizedSkill).all()}

            postings = (
                db_session.query(JobPosting)
                .options(
                    joinedload(JobPosting.company),
                    joinedload(JobPosting.skills),
                )
                .all()
            )

            posting_dicts = []
            for jp in postings:
                skills_list = []
                for jps in jp.skills:
                    norm_sk = skills_by_id.get(jps.skill_id)
                    if norm_sk:
                        skills_list.append(
                            {
                                "skill_name": norm_sk.name,
                                "relevance_score": float(jps.confidence_score or 1.0),
                                "is_mandatory": True,
                            }
                        )
                posting_dicts.append(
                    {
                        "id": jp.id,
                        "title": jp.title,
                        "company_name": jp.company.name if jp.company else "Unknown",
                        "skills": skills_list,
                        "status": "ACTIVE" if jp.is_active else "INACTIVE",
                    }
                )

        # Ingest to Neo4j
        await cls.sync_profile_nodes(profile_dicts)
        await cls.sync_transition_edges(experiences_list)
        await cls.sync_job_postings_skills(posting_dicts)

        # Retrieve counts
        nodes_updated = 0
        edges_updated = 0
        try:
            async with Neo4jService.get_session() as session:
                nodes_res = await session.run("MATCH (n) RETURN count(n) as node_count")
                nodes_record = await nodes_res.single()
                nodes_updated = nodes_record["node_count"] if nodes_record else 0

                edges_res = await session.run("MATCH ()-[r]->() RETURN count(r) as edge_count")
                edges_record = await edges_res.single()
                edges_updated = edges_record["edge_count"] if edges_record else 0
        except Exception as e:
            logger.warning(f"Failed to fetch counts from Neo4j: {e}")

        duration_ms = int((time.time() - start_time) * 1000)

        # Publish event
        try:
            await EventBus.publish(
                "market.graph.synced",
                {
                    "event_id": str(uuid4()),
                    "event_type": "market.graph.synced",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
                    "payload": {
                        "sync_run_id": str(uuid4()),
                        "nodes_updated": int(nodes_updated),
                        "edges_updated": int(edges_updated),
                        "duration_ms": duration_ms,
                    },
                },
            )
        except Exception as ev_err:
            logger.error(f"Failed to publish market.graph.synced event: {ev_err}")

        return {
            "nodes_updated": nodes_updated,
            "edges_updated": edges_updated,
            "duration_ms": duration_ms,
        }

    @classmethod
    async def run_centrality_recomputation(cls) -> None:
        """
        Degree centrality computation update job for Skill nodes.
        """
        query = (
            "MATCH (s:Skill)<-[r:HAS_SKILL]-(p) "
            "WITH s, count(r) as degree "
            "SET s.popularity_score = degree"
        )
        async with Neo4jService.get_session() as session:
            await session.run(query)
            logger.info("Recomputed skill centrality metrics in Neo4j.")
