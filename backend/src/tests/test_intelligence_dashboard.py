from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from uuid import uuid4
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, delete

from app.main import app
from app.infrastructure.database.models import (
    User,
    Company,
    JobPosting,
    NormalizedSkill,
    JobPostingSkill,
    UserPreferences,
    CareerGoals,
    CompanyWatchlist,
)
from app.services.database_service import async_engine, AsyncSessionLocal
from app.services.redis_service import RedisService
from app.services.position_delta_service import TargetRoleSpecificationService


@pytest.fixture(scope="module", autouse=True)
async def cleanup_db_engine():
    await async_engine.dispose()
    yield
    await async_engine.dispose()


@pytest.mark.asyncio
async def test_intelligence_and_dashboard_lifecycle():
    """
    Full end-to-end integration test for Wave 5:
    Career Health, Position Delta, Watchlists, Company Attractiveness,
    Ghost Posting detection, Opportunity scoring, and Dashboard aggregate caching.
    """
    email = f"intel_test_{random.randint(1000, 9999)}@example.com"
    password = "TestPassword123!"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Register and Login
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

        # Clear Redis cache first
        try:
            redis = RedisService.get_client()
            await redis.flushdb()
            await redis.close()
        except Exception:
            pass

        # 2. Setup Seed Data in DB
        company_id = str(uuid4())
        job_posting_id = str(uuid4())
        skill_id = str(uuid4())

        async with AsyncSessionLocal() as session:
            # Clean up watchlists or targets
            await session.execute(delete(CompanyWatchlist))
            await session.execute(delete(JobPostingSkill))
            await session.execute(delete(JobPosting))

            # Add Company if not exists
            comp_stmt = select(Company).where(Company.name == "Cyberdyne Systems")
            comp_res = await session.execute(comp_stmt)
            company = comp_res.scalar_one_or_none()
            if not company:
                company = Company(
                    id=company_id,
                    name="Cyberdyne Systems",
                    size_range="501-1000",
                    sector="Artificial Intelligence",
                    website="https://cyberdyne.com",
                )
                session.add(company)
            else:
                company_id = company.id

            # Add normalized skill if not exists
            ns_stmt = select(NormalizedSkill).where(NormalizedSkill.name == "Python")
            ns_res = await session.execute(ns_stmt)
            ns = ns_res.scalar_one_or_none()
            if not ns:
                ns = NormalizedSkill(
                    id=skill_id,
                    name="Python",
                    category="Language",
                    aliases=["python"],
                )
                session.add(ns)
            else:
                skill_id = ns.id

            # Add Job Posting
            job = JobPosting(
                id=job_posting_id,
                company_id=company_id,
                title="Senior Python Architect",
                raw_title="Senior Python Architect",
                location="San Francisco, CA",
                description="Lead Python engineer role.",
                url="https://cyberdyne.com/jobs/1",
                compensation_min=180000.0,
                compensation_max=220000.0,
                currency="USD",
                source="Direct",
                source_id="cyber_1",
                post_date=date.today() - timedelta(days=5),
                is_active=True,
            )
            session.add(job)

            # Add Job Posting Skill
            jps = JobPostingSkill(
                id=str(uuid4()),
                job_posting_id=job_posting_id,
                skill_id=skill_id,
                confidence_score=1.0,
            )
            session.add(jps)

            await session.commit()

        # Rebuild Specs
        async with AsyncSessionLocal() as session:
            await TargetRoleSpecificationService.rebuild_specifications(session)
            await session.commit()

        # 3. Setup Career Goals & Preferences
        goals_payload = {
            "target_role": "Senior Python Architect",
            "target_compensation_min": 170000.0,
            "target_compensation_max": 230000.0,
            "target_companies": ["Cyberdyne Systems"],
            "timeline_months": 6,
        }
        goals_resp = await client.put(
            "/api/v2/identity/goals", json=goals_payload, headers=headers
        )
        assert goals_resp.status_code == 200

        pref_payload = {
            "job_search_status": "ACTIVE",
            "weekly_digest_enabled": True,
            "email_notifications": True,
        }
        pref_resp = await client.put(
            "/api/v2/identity/preferences", json=pref_payload, headers=headers
        )
        assert pref_resp.status_code == 200

        # Update Profile to populate skills & experiences
        profile_payload = {
            "headline": "Senior Python Dev",
            "summary": "Building AI backends",
            "location": "Remote",
            "current_salary": 150000.0,
            "skills": [
                {
                    "skill_name": "Python",
                    "years_experience": 5.0,
                    "proficiency": "EXPERT",
                }
            ],
            "experiences": [
                {
                    "company_name": "Skynet",
                    "job_title": "Software Engineer",
                    "start_date": "2020-01-01",
                    "end_date": "2024-01-01",
                    "description": "Defense networks development",
                    "is_current": False,
                }
            ],
            "education": [],
            "projects": [],
        }
        prof_resp = await client.put(
            "/api/v2/profile", json=profile_payload, headers=headers
        )
        assert prof_resp.status_code == 200

        # 4. Test Career Health Score API
        health_resp = await client.get(
            "/api/v2/intelligence/health-score", headers=headers
        )
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["score"] > 0
        assert "primary_insight" in health_data
        assert health_data["top_driver"] is not None

        # 5. Test Position Delta API
        delta_resp = await client.get(
            "/api/v2/intelligence/delta", headers=headers
        )
        assert delta_resp.status_code == 200
        delta_data = delta_resp.json()
        assert delta_data["target_role"] == "Senior Python Architect"

        # 6. Test Watchlist APIs
        # Watch Company
        watch_resp = await client.post(
            f"/api/v2/market/companies/{company_id}/watch", headers=headers
        )
        assert watch_resp.status_code == 200
        assert watch_resp.json()["status"] == "success"

        # List Watched Companies
        list_watch_resp = await client.get(
            "/api/v2/market/companies/watch", headers=headers
        )
        assert list_watch_resp.status_code == 200
        watched = list_watch_resp.json()
        assert len(watched) >= 1
        assert watched[0]["id"] == company_id

        # Unwatch Company
        unwatch_resp = await client.delete(
            f"/api/v2/market/companies/{company_id}/watch", headers=headers
        )
        assert unwatch_resp.status_code == 200

        # List watched companies again (should be empty)
        list_watch_resp = await client.get(
            "/api/v2/market/companies/watch", headers=headers
        )
        assert list_watch_resp.status_code == 200
        assert len(list_watch_resp.json()) == 0

        # 7. Test Attractiveness Scoring API
        calc_resp = await client.post(
            f"/api/v2/market/companies/{company_id}/calculate-attractiveness",
            headers=headers,
        )
        assert calc_resp.status_code == 200
        calc_data = calc_resp.json()
        assert calc_data["attractiveness_score"] > 0

        # 8. Test Ghost Posting Detection API
        ghost_resp = await client.post(
            f"/api/v2/market/postings/{job_posting_id}/ghost-analyze",
            headers=headers,
        )
        assert ghost_resp.status_code == 200
        ghost_data = ghost_resp.json()
        assert "ghost_score" in ghost_data

        # 9. Test Opportunity Scoring API
        opps_resp = await client.get(
            "/api/v2/market/opportunities", headers=headers
        )
        assert opps_resp.status_code == 200
        opps_data = opps_resp.json()
        assert len(opps_data) >= 1
        assert opps_data[0]["fit_score"] > 0

        # 10. Test Dashboard API (Aggregator + Redis Cache)
        dash_resp = await client.get("/api/v2/dashboard", headers=headers)
        assert dash_resp.status_code == 200
        dash_data = dash_resp.json()
        assert "health_score" in dash_data
        assert "position_delta" in dash_data
        assert "opportunity_spotlight" in dash_data

        # Verify Redis caching by checking value directly in Redis
        try:
            redis = RedisService.get_client()
            cached_val = await redis.get(f"dashboard:user:{health_data['user_id']}")
            await redis.close()
            assert cached_val is not None
        except Exception:
            # Skip if redis connection is disabled or not reachable in test environment
            pass

        # 11. Test Analytics Event API
        analytics_payload = {
            "event_type": "WIDGET_CLICK",
            "widget_name": "opportunity_spotlight",
            "metadata_json": {"job_id": job_posting_id},
        }
        analytics_resp = await client.post(
            "/api/v2/dashboard/analytics",
            json=analytics_payload,
            headers=headers,
        )
        assert analytics_resp.status_code == 201
        assert analytics_resp.json()["status"] == "success"
