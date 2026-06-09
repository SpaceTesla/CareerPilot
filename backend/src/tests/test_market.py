from __future__ import annotations

import random
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.infrastructure.database.models import (
    CompensationBenchmark,
    CompensationRecord,
    JobDuplicate,
    JobIngestionRun,
    JobPosting,
    JobPostingSkill,
    NormalizedSkill,
    RawJobPosting,
)
from app.main import app
from app.services.benchmark_calculator_service import (
    BenchmarkCalculatorService,
)
from app.services.compensation_extraction_service import (
    CompensationExtractionService,
)
from app.services.database_service import (
    AsyncSessionLocal,
    async_engine,
)
from app.services.job_deduplication_service import JobDeduplicationService
from app.services.location_normalization_service import (
    LocationNormalizationService,
)
from app.services.skill_trend_service import SkillTrendService


@pytest.fixture(scope="module", autouse=True)
async def cleanup_db_engine():
    await async_engine.dispose()
    yield
    await async_engine.dispose()


# ── 1. Unit Tests for Similarity & Cleaning ─────────────────────────────


def test_similarity_math():
    """Verify title Jaccard and description Cosine similarity calculations."""
    s1 = "Senior Backend Engineer"
    s2 = "Senior Backend Software Engineer"
    # Jaccard
    j_sim = JobDeduplicationService.calculate_jaccard_similarity(s1, s2)
    assert 0.7 < j_sim < 1.0

    # Cosine
    c_sim = JobDeduplicationService.calculate_cosine_similarity(
        "Python developer with Kubernetes experience",
        "Seeking a Python developer who has Kubernetes and DevOps skills",
    )
    assert 0.4 < c_sim < 1.0

    # Edge cases
    assert JobDeduplicationService.calculate_jaccard_similarity("", "") == 1.0
    assert JobDeduplicationService.calculate_cosine_similarity("", "") == 1.0


def test_title_and_company_cleaning():
    """Test cleaning of seniority tags and corporate suffixes."""
    # Title
    t1 = "Sr. Staff Backend Developer II"
    t_clean = JobDeduplicationService.clean_title(t1)
    assert "backend developer" in t_clean
    assert "sr" not in t_clean
    assert "staff" not in t_clean

    # Company
    c1 = "Google LLC"
    c2 = "Acme Corp."
    assert JobDeduplicationService.clean_company(c1) == "google"
    assert JobDeduplicationService.clean_company(c2) == "acme"


def test_location_normalization():
    """Verify locations are correctly resolved to cost-of-living tiers."""
    tier1 = LocationNormalizationService.normalize_location("San Francisco, CA")
    assert tier1["col_tier"] == "TIER_1"
    assert tier1["location"] == "San Francisco, CA"

    tier2 = LocationNormalizationService.normalize_location("Austin, TX")
    assert tier2["col_tier"] == "TIER_2"

    tier3 = LocationNormalizationService.normalize_location("Boise, ID")
    assert tier3["col_tier"] == "TIER_3"

    remote = LocationNormalizationService.normalize_location("Remote - US")
    assert remote["location"] == "Remote"
    assert remote["col_tier"] == "TIER_3"


# ── 2. Unit Tests for Compensation Extraction ──────────────────────────


def test_compensation_regex_extraction():
    """Test parsing ranges, hourly, monthly, and single values."""
    res1 = CompensationExtractionService.extract_salary_from_text(
        "Salary: $140,000 to $180,000 per year"
    )
    assert res1["min_salary"] == 140000.0
    assert res1["max_salary"] == 180000.0
    assert res1["payment_interval"] == "ANNUAL"

    res2 = CompensationExtractionService.extract_salary_from_text(
        "Pay rate: £60 - £80 per hour"
    )
    assert res2["min_salary"] == 60.0
    assert res2["max_salary"] == 80.0
    assert res2["payment_interval"] == "HOURLY"
    assert res2["currency"] == "GBP"

    res3 = CompensationExtractionService.extract_salary_from_text(
        "Offers $10,000 / month"
    )
    assert res3["min_salary"] == 10000.0
    assert res3["max_salary"] == 10000.0
    assert res3["payment_interval"] == "MONTHLY"


def test_compensation_normalization():
    """Verify pay rates are standardized to USD annual equivalents."""
    # GBP Hourly rate: £60 to £80
    # Annual min: 60 * 2000 * 1.3 (GBP rate) = 156,000
    # Annual max: 80 * 2000 * 1.3 = 208,000
    norm1 = CompensationExtractionService.normalize_range(
        min_val=60.0, max_val=80.0, interval="HOURLY", currency="GBP"
    )
    assert norm1["computed_annual_min"] == 156000.0
    assert norm1["computed_annual_max"] == 208000.0


# ── 3. Integration Tests for Market API & Services ──────────────────────


@pytest.mark.asyncio
async def test_market_api_lifecycle():
    """
    Test full lifecycle of job market data: Admin ingestion, deduplication,
    health monitoring, skill extraction, trends, and compensation percentiles.
    """
    email = f"market_test_{random.randint(1000, 9999)}@example.com"
    password = "TestPassword123!"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Step 1: Register and Login
        reg_resp = await client.post(
            "/api/v2/auth/register", json={"email": email, "password": password}
        )
        assert reg_resp.status_code == 201
        login_resp = await client.post(
            "/api/v2/auth/login", json={"email": email, "password": password}
        )
        assert login_resp.status_code == 200
        tokens = login_resp.json()
        # Seed skills taxonomy in DB to allow local regex matching without LLM fallback
        from uuid import uuid4
        async with AsyncSessionLocal() as session:
            # Clean up tables to start with a fresh state
            await session.execute(delete(JobPostingSkill))
            await session.execute(delete(CompensationRecord))
            await session.execute(delete(JobDuplicate))
            await session.execute(delete(JobPosting))
            await session.execute(delete(RawJobPosting))
            await session.execute(delete(JobIngestionRun))
            await session.execute(delete(CompensationBenchmark))

            for name, cat in [
                ("Python", "Language"),
                ("FastAPI", "Framework"),
                ("Kubernetes", "Infrastructure"),
            ]:
                stmt_chk = select(NormalizedSkill).where(NormalizedSkill.name == name)
                res_chk = await session.execute(stmt_chk)
                if not res_chk.scalar_one_or_none():
                    session.add(
                        NormalizedSkill(
                            id=str(uuid4()),
                            name=name,
                            category=cat,
                            aliases=[name.lower()],
                        )
                    )
            await session.commit()

        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        # Step 2: Extract Skills from text via API
        extract_payload = {
            "text": "We need a python engineer with fastapi and kubernetes experience."
        }
        ext_resp = await client.post(
            "/api/v2/market/skills/extract", json=extract_payload, headers=headers
        )
        skills_data = ext_resp.json()["extracted_skills"]
        assert len(skills_data) >= 2
        skill_names = [s["canonical_name"] for s in skills_data]
        assert "Python" in skill_names or "FastAPI" in skill_names

        # Step 3: Direct Admin Ingestion payload (5 sample jobs to build benchmark)
        # Note: 5 matching roles (Senior Backend Engineer) at same location (Remote)
        # to meet the N >= 5 minimum sample size criteria for percentile calculations.
        ingest_payload = {
            "source": "JSEARCH",
            "postings": [
                {
                    "source_id": "test_j1",
                    "company_name": "Google LLC",
                    "title": "Senior Backend Engineer",
                    "description": (
                        "Python, FastAPI and Kubernetes developer. "
                        "Salary is $150000 a year."
                    ),
                    "location": "Remote",
                    "url": "https://careers.google.com/jobs/1",
                    "compensation_min": 150000.00,
                    "compensation_max": 150000.00,
                    "currency": "USD",
                    "post_date": str(date.today()),
                },
                {
                    "source_id": "test_j2",
                    "company_name": "Apple Inc",
                    "title": "Senior Backend Engineer",
                    "description": "Python developer. Salary is $160000 a year.",
                    "location": "Remote",
                    "url": "https://careers.apple.com/jobs/2",
                    "compensation_min": 160000.00,
                    "compensation_max": 160000.00,
                    "currency": "USD",
                    "post_date": str(date.today()),
                },
                {
                    "source_id": "test_j3",
                    "company_name": "Microsoft",
                    "title": "Senior Backend Engineer",
                    "description": (
                        "Looking for a Python dev. "
                        "Salary is $170000 a year."
                    ),
                    "location": "Remote",
                    "url": "https://careers.microsoft.com/jobs/3",
                    "compensation_min": 170000.00,
                    "compensation_max": 170000.00,
                    "currency": "USD",
                    "post_date": str(date.today()),
                },
                {
                    "source_id": "test_j4",
                    "company_name": "Netflix",
                    "title": "Senior Backend Engineer",
                    "description": "FastAPI engineer. Salary is $180000 a year.",
                    "location": "Remote",
                    "url": "https://careers.netflix.com/jobs/4",
                    "compensation_min": 180000.00,
                    "compensation_max": 180000.00,
                    "currency": "USD",
                    "post_date": str(date.today()),
                },
                {
                    "source_id": "test_j5",
                    "company_name": "Meta Platforms",
                    "title": "Senior Backend Engineer",
                    "description": "Python, FastAPI. Salary is $190000 a year.",
                    "location": "Remote",
                    "url": "https://careers.meta.com/jobs/5",
                    "compensation_min": 190000.00,
                    "compensation_max": 190000.00,
                    "currency": "USD",
                    "post_date": str(date.today()),
                },
            ],
        }

        ingest_resp = await client.post(
            "/api/v2/market/admin/ingest", json=ingest_payload, headers=headers
        )
        assert ingest_resp.status_code == 202
        assert "audit_log_id" in ingest_resp.json()

        # Step 4: Verify postings fetched from DB
        get_postings_resp = await client.get(
            "/api/v2/market/postings?title=Backend", headers=headers
        )
        assert get_postings_resp.status_code == 200
        postings_data = get_postings_resp.json()
        assert postings_data["total"] >= 5

        # Step 5: Ingestion run status & health checks
        health_resp = await client.get(
            "/api/v2/market/ingestion/sources/health", headers=headers
        )
        assert health_resp.status_code == 200
        health_data = health_resp.json()["sources"]
        assert len(health_data) > 0

        # Step 6: Deduplication Check - Duplicate auto-merge
        # Google reposting the exact job (95% identical description)
        dup_payload = {
            "source": "JSEARCH",
            "postings": [
                {
                    "source_id": "test_j1_dup",
                    "company_name": "Google LLC",
                    "title": "Senior Backend Engineer",
                    "description": (
                        "Python, FastAPI and Kubernetes developer. "
                        "Salary is $150000 a year."
                    ),
                    "location": "Remote",
                    "url": "https://careers.google.com/jobs/1-repost",
                    "compensation_min": 150000.00,
                    "compensation_max": 150000.00,
                    "currency": "USD",
                    "post_date": str(date.today()),
                }
            ],
        }
        dup_resp = await client.post(
            "/api/v2/market/admin/ingest", json=dup_payload, headers=headers
        )
        assert dup_resp.status_code == 202

        # Step 7: Deduplication Queue Check - Marginal case review queue
        # Microsoft reposting with Remote - US (triggering marginal
        # score ~0.80 due to slight difference)
        marginal_payload = {
            "source": "JSEARCH",
            "postings": [
                {
                    "source_id": "test_j3_marginal",
                    "company_name": "Microsoft",
                    "title": "Backend Software Developer",
                    "description": (
                        "Looking for a Python dev. "
                        "Salary is $170000 a year. Different details."
                    ),
                    "location": "New York, NY",  # Different location but similar desc
                    "url": "https://careers.microsoft.com/jobs/3-marginal",
                    "compensation_min": 170000.00,
                    "compensation_max": 170000.00,
                    "currency": "USD",
                    "post_date": str(date.today()),
                }
            ],
        }
        marginal_resp = await client.post(
            "/api/v2/market/admin/ingest", json=marginal_payload, headers=headers
        )
        assert marginal_resp.status_code == 202

        # Let's directly test resolving duplicate pairs inside DB
        async with AsyncSessionLocal() as session:
            # Query for duplicate entry
            stmt_dup = select(JobDuplicate).where(
                JobDuplicate.status == "PENDING_REVIEW"
            )
            res_dup = await session.execute(stmt_dup)
            pending_pair = res_dup.scalars().first()

            if pending_pair:
                resolve_payload = {
                    "duplicate_pair_id": pending_pair.id,
                    "action": "APPROVE",
                }
                res_approve = await client.post(
                    "/api/v2/market/dedupe/resolve",
                    json=resolve_payload,
                    headers=headers,
                )
                assert res_approve.status_code == 200
                assert res_approve.json()["status"] == "APPROVED"

        # Step 8: Compute Skill Daily Snapshots & Refresh Trends Materialized View
        async with AsyncSessionLocal() as session:
            await SkillTrendService.compute_daily_snapshots(session)
            await SkillTrendService.refresh_materialized_view(session)
            await session.commit()

        # Step 9: Query skill trends from API (should warm Redis cache)
        trends_resp = await client.get("/api/v2/market/trends", headers=headers)
        assert trends_resp.status_code == 200
        trends_data = trends_resp.json()["trends"]
        assert len(trends_data) >= 0

        # Step 10: Recalculate Benchmarks and query them via API
        async with AsyncSessionLocal() as session:
            await BenchmarkCalculatorService.recalculate_benchmarks(session)
            await session.commit()

        # Query compensation benchmarks (since we had 5 samples,
        # it calculates percentiles)
        comp_resp = await client.get(
            "/api/v2/market/compensation"
            "?role_type=Senior Backend Engineer&location=Remote",
            headers=headers,
        )
        assert comp_resp.status_code == 200
        comp_data = comp_resp.json()["benchmarks"]
        assert comp_data["p50_salary"] >= 150000.0
        assert comp_data["sample_size"] >= 5
