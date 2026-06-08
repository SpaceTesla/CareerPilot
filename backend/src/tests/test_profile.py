from __future__ import annotations

import random
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.infrastructure.database.models import (
    CareerProfile,
    Education,
    Experience,
    Project,
    Skill,
)
from app.main import app
from app.schemas.profile import (
    EducationSchema,
    ExperienceSchema,
    ProficiencyLevel,
    ProfileUpdate,
    SkillSchema,
)
from app.services.database_service import async_engine, DatabaseService
from app.services.llm_parser_service import LLMParserService, RelaxedProfile
from app.services.profile_service import ProfileService

@pytest.fixture(scope="module", autouse=True)
async def cleanup_db_engine():
    await async_engine.dispose()
    yield
    await async_engine.dispose()


# ── 1. Unit Tests for Schema Validations & Services ───────────────────────


def test_experience_date_validation():
    """Ensure experience start_date cannot be later than end_date when not current."""
    with pytest.raises(ValidationError):
        ExperienceSchema(
            company_name="Tech Corp",
            job_title="Engineer",
            start_date=date(2025, 1, 1),
            end_date=date(2024, 1, 1),
            description="Doing stuff",
            is_current=False,
        )


def test_education_date_validation():
    """Ensure education start_date cannot be later than end_date."""
    with pytest.raises(ValidationError):
        EducationSchema(
            institution="University of Tech",
            degree="BS",
            field_of_study="CS",
            start_date=date(2025, 1, 1),
            end_date=date(2024, 1, 1),
        )


def test_profile_update_max_current_experiences():
    """Ensure at most two active experiences can be set concurrently."""
    with pytest.raises(ValidationError):
        ProfileUpdate(
            experiences=[
                ExperienceSchema(
                    company_name="Company A",
                    job_title="Dev A",
                    start_date=date(2020, 1, 1),
                    is_current=True,
                    description="Job 1",
                ),
                ExperienceSchema(
                    company_name="Company B",
                    job_title="Dev B",
                    start_date=date(2020, 1, 1),
                    is_current=True,
                    description="Job 2",
                ),
                ExperienceSchema(
                    company_name="Company C",
                    job_title="Dev C",
                    start_date=date(2020, 1, 1),
                    is_current=True,
                    description="Job 3",
                ),
            ]
        )


def test_profile_completeness_score():
    """Ensure completeness score calculations yield expected weights:
    skills: 30%, experience: 40%, education: 15%, projects: 15%.
    """
    p = CareerProfile(id="test-profile-id", user_id="test-user-id")
    assert ProfileService.calculate_completeness(p) == 0

    p.skills = [
        Skill(
            id="s1",
            profile_id="p1",
            skill_name="Python",
            years_experience=3.0,
            proficiency="EXPERT",
        )
    ]
    assert ProfileService.calculate_completeness(p) == 30

    p.experiences = [
        Experience(
            id="e1",
            profile_id="p1",
            company_name="A",
            job_title="B",
            start_date=date(2020, 1, 1),
            description="C",
            is_current=True,
        )
    ]
    assert ProfileService.calculate_completeness(p) == 70

    p.education = [
        Education(
            id="ed1",
            profile_id="p1",
            institution="U",
            start_date=date(2015, 1, 1),
        )
    ]
    assert ProfileService.calculate_completeness(p) == 85

    p.projects = [
        Project(
            id="pr1",
            profile_id="p1",
            project_name="P",
            description="D",
        )
    ]
    assert ProfileService.calculate_completeness(p) == 100


def test_llm_parser_confidence_score():
    """Verify confidence score calculations and deductions work appropriately."""
    # Fully populated mock
    full_profile = RelaxedProfile(
        headline="Tech Lead",
        summary="Experienced dev",
        location="SF",
        current_salary=150000.0,
        skills=[{"skill_name": "Python"}],
        experiences=[
            {"company_name": "A", "job_title": "B", "start_date": "2020-01-01"}
        ],
        education=[{"institution": "Univ", "start_date": "2010-01-01"}],
        projects=[{"project_name": "P", "description": "D"}],
        self_evaluation_score=0.9,
    )
    score = LLMParserService.calculate_confidence(full_profile)
    assert score == 0.9

    # Missing general profile fields (deducts 0.20 total)
    missing_general = RelaxedProfile(
        headline=None,
        summary=None,
        location=None,
        skills=[{"skill_name": "Python"}],
        experiences=[
            {"company_name": "A", "job_title": "B", "start_date": "2020-01-01"}
        ],
        education=[{"institution": "Univ", "start_date": "2010-01-01"}],
        self_evaluation_score=0.9,
    )
    score = LLMParserService.calculate_confidence(missing_general)
    # Deductions: headline (-0.05), summary (-0.10), location (-0.05) -> -0.20
    assert abs(score - 0.70) < 0.001


# ── 2. Integration Tests for API Routers ─────────────────────────────────


@pytest.mark.asyncio
async def test_profile_api_endpoints():
    """Test full integration lifecycle: Get empty profile, Update,
    Upload Resume (short & normal), Sync Resume, and Version Restore.
    """
    email = f"profile_test_{random.randint(1000, 9999)}@example.com"
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
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        # Step 2: Get profile (should auto-create empty profile)
        get_resp = await client.get("/api/v2/profile", headers=headers)
        assert get_resp.status_code == 200
        profile_data = get_resp.json()
        assert "id" in profile_data
        assert profile_data["headline"] is None
        assert len(profile_data["skills"]) == 0

        # Step 3: Update profile directly
        update_payload = {
            "headline": "Lead Python Developer",
            "summary": "10+ years backend expertise",
            "location": "New York, NY",
            "current_salary": 160000.0,
            "skills": [
                {
                    "skill_name": "Python",
                    "years_experience": 8.5,
                    "proficiency": "EXPERT",
                },
                {
                    "skill_name": "FastAPI",
                    "years_experience": 4.0,
                    "proficiency": "ADVANCED",
                },
            ],
            "experiences": [
                {
                    "company_name": "Acme Corp",
                    "job_title": "Senior Engineer",
                    "start_date": "2022-01-01",
                    "description": "Led backend API migration",
                    "is_current": True,
                }
            ],
            "education": [
                {
                    "institution": "MIT",
                    "degree": "MS",
                    "field_of_study": "Computer Science",
                    "start_date": "2018-09-01",
                    "end_date": "2020-06-01",
                }
            ],
            "projects": [
                {
                    "project_name": "CareerPilot",
                    "description": "AI-powered job portal",
                    "role_description": "Architect",
                    "url": "https://github.com/test/careerpilot",
                }
            ],
        }

        put_resp = await client.put(
            "/api/v2/profile", json=update_payload, headers=headers
        )
        assert put_resp.status_code == 200
        updated_data = put_resp.json()
        assert updated_data["headline"] == "Lead Python Developer"
        assert len(updated_data["skills"]) == 2
        assert updated_data["experiences"][0]["company_name"] == "Acme Corp"

        # Step 4: Test Upload Resume - Scanned document check (short text < 50 chars)
        short_file = {"file": ("scanned.pdf", b"too short", "application/pdf")}
        upload_short_resp = await client.post(
            "/api/v2/profile/upload", files=short_file, headers=headers
        )
        assert upload_short_resp.status_code == 422

        # Step 5: Test Upload Resume - Successful path with mocked parsing
        mock_extracted_text = (
            "John Doe Resume. Skills: Python, SQL. Experience: Staff Software Engineer "
            "at Google from 2021-01-01 to Present. Education: BS CS at Stanford."
        )

        with (
            patch(
                "app.services.resume_extractor_service.ResumeExtractorService.extract_text",
                return_value=mock_extracted_text,
            ),
            patch(
                "app.services.llm_parser_service.LLMParserService.parse_resume_text",
                new_callable=AsyncMock,
            ) as mock_parser,
        ):
            # Define mocked LLM parser output
            mock_parsed_data = ProfileUpdate(
                headline="Staff Software Engineer",
                summary="Staff Engineer at Google",
                location="Mountain View, CA",
                current_salary=Decimal("220000.00"),
                skills=[
                    SkillSchema(
                        skill_name="Python",
                        years_experience=Decimal("5.0"),
                        proficiency=ProficiencyLevel.EXPERT,
                    )
                ],
                experiences=[
                    ExperienceSchema(
                        company_name="Google",
                        job_title="Staff Software Engineer",
                        start_date=date(2021, 1, 1),
                        is_current=True,
                        description="Core infra",
                    )
                ],
                education=[
                    EducationSchema(
                        institution="Stanford",
                        degree="BS",
                        field_of_study="Computer Science",
                        start_date=date(2017, 9, 1),
                        end_date=date(2021, 6, 1),
                    )
                ],
                projects=[],
            )
            mock_parser.return_value = (mock_parsed_data, 0.95)

            normal_file = {"file": ("john_doe.pdf", b"A" * 100, "application/pdf")}
            upload_success_resp = await client.post(
                "/api/v2/profile/upload", files=normal_file, headers=headers
            )
            assert upload_success_resp.status_code == 200
            upload_result = upload_success_resp.json()
            assert "resume_id" in upload_result
            assert float(upload_result["confidence_score"]) == 0.95
            assert upload_result["parsed_data"]["headline"] == "Staff Software Engineer"

            resume_id = upload_result["resume_id"]

            # Step 6: Sync resume endpoint (Commit parsed payload)
            sync_payload = {
                "resume_id": resume_id,
                "override_data": upload_result["parsed_data"],
            }
            # Add a slight modification to the sync payload to verify overrides
            sync_payload["override_data"]["headline"] = "Senior Staff Software Engineer"

            sync_resp = await client.post(
                "/api/v2/profile/sync-resume", json=sync_payload, headers=headers
            )
            assert sync_resp.status_code == 200
            synced_profile = sync_resp.json()
            assert synced_profile["headline"] == "Senior Staff Software Engineer"

        # Step 7: Get Versions list (should have at least two versions now)
        versions_resp = await client.get("/api/v2/profile/versions", headers=headers)
        assert versions_resp.status_code == 200
        versions = versions_resp.json()
        assert len(versions) >= 2
        # Sort by version number to be sure
        versions = sorted(versions, key=lambda v: v["version_number"])
        v1_num = versions[0]["version_number"]

        # Step 8: Restore version 1 (which had 'Lead Python Developer' headline)
        restore_resp = await client.post(
            f"/api/v2/profile/versions/{v1_num}/restore", headers=headers
        )
        assert restore_resp.status_code == 200
        restored_profile = restore_resp.json()
        assert restored_profile["headline"] == "Lead Python Developer"
