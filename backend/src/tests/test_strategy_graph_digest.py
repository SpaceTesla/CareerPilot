from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4, UUID
from datetime import datetime, timezone, date
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import update

from app.main import app
from app.core.config import settings
from app.services.neo4j_service import Neo4jService
from app.services.graph_ingestion_pipeline import GraphIngestionPipeline
from app.services.career_graph_analytics_service import CareerGraphAnalyticsService
from app.services.gap_aware_retrieval_engine import GapAwareRetrievalEngine
from app.services.weekly_digest_service import DigestGenerationService, DigestDeliveryService
from app.services.strategy_review_service import StrategyReviewOrchestrator
from app.infrastructure.database.connection import SessionLocal
from app.infrastructure.database.models import (
    User,
    CareerProfile,
    Skill,
    Experience,
    Company,
    JobPosting,
    NormalizedSkill,
    JobPostingSkill,
    UserPreferences,
    CareerHealthScore,
    UserDigest,
    CareerStrategyReview,
    StrategyActionItem,
)


@pytest.fixture(autouse=True)
async def mock_neo4j_if_unavailable(monkeypatch):
    """
    Auto-detects if Neo4j is running. If not, patches get_session to return semantic mock records
    so integration test flows can compile and verify in isolated CI runs.
    """
    connected, _ = await Neo4jService.check_health()
    if not connected:
        # Mock session setup
        mock_session = AsyncMock()

        async def mock_run(query, **kwargs):
            mock_result = AsyncMock()

            # 1. Pathfinding career path query
            if "MATCH p = (start:Role" in query:
                mock_path = MagicMock()
                mock_rel = {"avg_duration_months": 15.0, "confidence": 0.8}
                mock_node1 = {"name": kwargs.get("start_role", "Senior Backend Engineer")}
                mock_node2 = {"name": kwargs.get("target_role", "AI Platform Engineer")}
                mock_path.nodes = [mock_node1, mock_node2]
                mock_path.relationships = [mock_rel]

                record = {"p": mock_path}
                async def mock_iterator():
                    yield record
                mock_result.__aiter__ = lambda x: mock_iterator()

            # 2. Bridge skills for path step
            elif "MATCH (ro:Role {name: $target_name})-[req:REQUIRES_SKILL]" in query:
                records = [{"skill_name": "LangGraph"}, {"skill_name": "Qdrant"}]
                async def mock_iterator():
                    for r in records:
                        yield r
                mock_result.__aiter__ = lambda x: mock_iterator()

            # 3. Related skills co-occurrence query
            elif "MATCH (s:Skill {canonical_name: $skill_name}) " in query and "HAS_SKILL" in query:
                records = [
                    {"skill_name": "TypeScript", "weight": 5},
                    {"skill_name": "Next.js", "weight": 3},
                ]
                async def mock_iterator():
                    for r in records:
                        yield r
                mock_result.__aiter__ = lambda x: mock_iterator()

            # 4. Related skills co-occurrence inside gap analysis estimate
            elif "MATCH (s1:Skill {canonical_name: $skill})" in query:
                record = {"related_skill": "Python", "cooccurrence": 5}
                mock_result.single = AsyncMock(return_value=record)

            # 5. Adjacent opportunity query
            elif "MATCH (p:CandidateProfile {profile_id: $profile_id})-[h:HAS_SKILL]" in query:
                record = {
                    "job_posting_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
                    "title": "AI Platform Engineer",
                    "missing": ["LangGraph"],
                    "total_count": 3
                }
                async def mock_iterator():
                    yield record
                mock_result.__aiter__ = lambda x: mock_iterator()

            # 6. Default counts
            elif "RETURN count(" in query:
                mock_record = {"node_count": 12, "edge_count": 18}
                mock_result.single = AsyncMock(return_value=mock_record)

            return mock_result

        mock_session.run = mock_run

        @asynccontextmanager
        async def get_mock_session():
            yield mock_session

        monkeypatch.setattr(Neo4jService, "get_session", get_mock_session)


@pytest.mark.asyncio
async def test_wave10_integration_lifecycle():
    """
    Full end-to-end integration test for Wave 10.
    Creates SQL data, runs Neo4j ingestion, pathfinder, gap-aware matching, weekly digest, and strategic reviews.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Register and Login to get a real valid JWT token and headers
        email = f"strategy_test_{uuid4().hex[:8]}@example.com"
        password = "TestPassword123!"
        
        reg_resp = await client.post(
            "/api/v2/auth/register", json={"email": email, "password": password}
        )
        assert reg_resp.status_code == 201
        
        login_resp = await client.post(
            "/api/v2/auth/login", json={"email": email, "password": password}
        )
        assert login_resp.status_code == 200
        tokens = login_resp.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # 2. Cleanup and seed database records using retrieved user ID
        with SessionLocal() as session:
            # Delete any existing test job postings with this ID to ensure idempotency
            session.query(JobPostingSkill).filter(JobPostingSkill.job_posting_id == "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d").delete()
            session.query(JobPosting).filter(JobPosting.id == "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d").delete()
            session.commit()

        with SessionLocal() as session:
            db_user = session.query(User).filter(User.email == email).first()
            user_id = db_user.id
            
            # Create profile since it is not created on register
            profile_id = str(uuid4())
            db_profile = CareerProfile(
                id=profile_id,
                user_id=user_id,
                headline="Senior Developer",
            )
            session.add(db_profile)
            session.flush()
            
            # Add skills and experience to profile
            db_skill1 = Skill(
                id=str(uuid4()),
                profile_id=profile_id,
                skill_name="Python",
                years_experience=5.0,
                proficiency="EXPERT"
            )
            session.add(db_skill1)
            
            db_skill2 = Skill(
                id=str(uuid4()),
                profile_id=profile_id,
                skill_name="React",
                years_experience=3.0,
                proficiency="INTERMEDIATE"
            )
            session.add(db_skill2)
            
            company_name = f"Acme Inc {str(uuid4())[:8]}"
            db_exp1 = Experience(
                id=str(uuid4()),
                profile_id=profile_id,
                company_name=company_name,
                job_title="Senior Backend Engineer",
                start_date=date(2020, 1, 1),
                description="Writing python code."
            )
            session.add(db_exp1)
            
            # Add a Company and Job Posting
            db_comp = Company(
                id=str(uuid4()),
                name=company_name,
            )
            session.add(db_comp)
            session.flush()
            
            db_job = JobPosting(
                id="7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d", # Matches mock query return id
                company_id=db_comp.id,
                title="AI Platform Engineer",
                raw_title="AI Platform Engineer",
                location="San Francisco, CA",
                description="Needs Python, Docker, and LangGraph",
                url="http://example.com/apply",
                source="Internal",
                source_id="src_ai_101",
                post_date=date.today(),
                is_active=True,
            )
            session.add(db_job)
            session.flush()
            
            # Link skill to job posting (get or create)
            db_norm_skill = session.query(NormalizedSkill).filter(NormalizedSkill.name == "LangGraph").first()
            if not db_norm_skill:
                db_norm_skill = NormalizedSkill(
                    id=str(uuid4()),
                    name="LangGraph",
                    category="AI",
                )
                session.add(db_norm_skill)
                session.flush()
            
            db_job_skill = JobPostingSkill(
                id=str(uuid4()),
                job_posting_id=db_job.id,
                skill_id=db_norm_skill.id,
                confidence_score=0.9,
            )
            session.add(db_job_skill)
            
            # Add career health score
            db_health = CareerHealthScore(
                id=str(uuid4()),
                user_id=user_id,
                score=75.0,
                skill_alignment_score=80.0,
                market_positioning_score=75.0,
                activity_health_score=70.0,
                compensation_alignment_score=75.0,
                profile_completeness_score=80.0,
                primary_insight="Good progress.",
                top_driver="Skill Alignment",
                top_detractor="Activity Health",
                computed_at=datetime.now(timezone.utc)
            )
            session.add(db_health)
            
            session.commit()

        # --- Test 1. Graph Sync ---
        sync_result = await GraphIngestionPipeline.sync_all_data()
        assert "nodes_updated" in sync_result

        # --- Test 2. Pathfinder Route ---
        resp_path = await client.get(
            "/api/v2/market/graph/path",
            params={
                "start_role": "Senior Backend Engineer",
                "target_role": "AI Platform Engineer",
                "max_steps": 2,
            },
            headers=headers
        )
        assert resp_path.status_code == 200
        assert "paths" in resp_path.json()

        # --- Test 3. Related Skills Route ---
        resp_rel = await client.get("/api/v2/market/graph/skills/React/related", headers=headers)
        assert resp_rel.status_code == 200
        assert resp_rel.json()["searched_skill"] == "React"
        assert len(resp_rel.json()["related_skills"]) > 0

        # --- Test 4. Adjacent Opportunities Route ---
        resp_adj = await client.get("/api/v2/market/retrieval/adjacent", params={"limit": 5}, headers=headers)
        assert resp_adj.status_code == 200
        assert "results" in resp_adj.json()

        # --- Test 5. Gap Analysis Route ---
        resp_gap = await client.get(
            "/api/v2/market/retrieval/gap-analysis",
            params={"job_posting_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d"},
            headers=headers
        )
        assert resp_gap.status_code == 200
        gap_payload = resp_gap.json()
        assert gap_payload["job_posting_id"] == "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d"
        assert "overall_gap_level" in gap_payload

        # --- Test 6. Weekly Digest queue & get API ---
        digest_ids = await DigestDeliveryService.queue_digests()
        assert len(digest_ids) > 0
        
        # Verify get history endpoint works
        # Overwrite user_id on digest for test queries to match current user
        with SessionLocal() as session:
            for did in digest_ids:
                session.execute(
                    update(UserDigest).where(UserDigest.id == did).values(user_id=user_id)
                )
            session.commit()
            
        resp_digests = await client.get("/api/v2/strategy/digests", headers=headers)
        assert resp_digests.status_code == 200
        assert len(resp_digests.json()["digests"]) > 0
        
        target_digest_id = resp_digests.json()["digests"][0]["id"]
        resp_digest_det = await client.get(f"/api/v2/strategy/digests/{target_digest_id}", headers=headers)
        assert resp_digest_det.status_code == 200
        assert "content" in resp_digest_det.json()

        # --- Test 7. Strategy Reviews initiate, detail, complete, and action item patch ---
        review_id = await StrategyReviewOrchestrator.initiate_review(UUID(user_id))
        assert review_id is not None
        
        # Overwrite user_id on review for test query mapping
        with SessionLocal() as session:
            session.execute(
                update(CareerStrategyReview).where(CareerStrategyReview.id == review_id).values(user_id=user_id)
            )
            session.commit()

        resp_reviews = await client.get("/api/v2/strategy/reviews", headers=headers)
        assert resp_reviews.status_code == 200
        assert len(resp_reviews.json()["reviews"]) > 0

        resp_rev_det = await client.get(f"/api/v2/strategy/reviews/{review_id}", headers=headers)
        assert resp_rev_det.status_code == 200
        rev_detail = resp_rev_det.json()
        assert len(rev_detail["action_items"]) > 0

        # Complete strategy review
        resp_comp = await client.post(
            f"/api/v2/strategy/reviews/{review_id}/complete",
            json={"feedback_text": "I will try my best", "accept_action_items": True},
            headers=headers
        )
        assert resp_comp.status_code == 200
        assert resp_comp.json()["status"] == "COMPLETED"

        # Patch action item status
        action_item_id = rev_detail["action_items"][0]["id"]
        resp_patch_item = await client.patch(
            f"/api/v2/strategy/reviews/action-items/{action_item_id}",
            json={"status": "COMPLETED"},
            headers=headers
        )
        assert resp_patch_item.status_code == 200
        assert resp_patch_item.json()["status"] == "COMPLETED"
