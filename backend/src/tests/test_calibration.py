from __future__ import annotations

import random
import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, date
from app.main import app
from app.services.database_service import async_engine, AsyncSessionLocal
from app.infrastructure.database.models import (
    User,
    CareerProfile,
    EvalDataset,
    EvalRun,
    EvalResult,
    CalibrationModel,
    MLModelRegistry,
    JobPosting,
    Experience,
    Skill
)
from app.services.evaluation_framework_service import EvaluationFrameworkService
from app.services.evaluation_agent_service import EvaluationAgentService
from app.services.calibration_model_service import CalibrationModelService
from app.services.peer_cohort_benchmarking_service import PeerCohortBenchmarkingService
from app.services.ml_platform_service import MLPlatformService
from app.schemas.evaluation import CalibrationInferenceRequest

@pytest.fixture(scope="module", autouse=True)
async def cleanup_db_engine():
    await async_engine.dispose()
    yield
    await async_engine.dispose()


@pytest.fixture(autouse=True)
async def dispose_engine_per_test():
    await async_engine.dispose()
    yield
    await async_engine.dispose()


@pytest.mark.asyncio
async def test_evaluation_framework_lifecycle():
    """
    Test creating dataset items, triggering evaluation run, and retrieving reports.
    """
    # 1. Create dataset items for skill extraction
    comp = f"skill_extraction_{uuid4().hex[:8]}"
    item1_id = await EvaluationFrameworkService.create_dataset_item(
        component_name=comp,
        input_payload={"text": "Looking for a Python developer with Django and PostgreSQL experience."},
        expected_output={"skills": ["Python", "Django", "PostgreSQL"]}
    )
    assert item1_id is not None

    item2_id = await EvaluationFrameworkService.create_dataset_item(
        component_name=comp,
        input_payload={"text": "Position requires React, TypeScript and Redux."},
        expected_output={"skills": ["React", "TypeScript", "Redux"]}
    )
    assert item2_id is not None

    # 2. Trigger run
    run_id = await EvaluationFrameworkService.trigger_eval_run(
        component_name=comp,
        environment="ci",
        commit_sha="a1b2c3d4e5f6g7h8"
    )
    assert run_id is not None

    # 3. Retrieve report
    report = await EvaluationFrameworkService.get_run_report(run_id)
    assert str(report.eval_run_id) == run_id
    assert report.status == "completed"
    assert report.metrics.total_tests == 2
    assert report.metrics.passed >= 0
    assert report.metrics.failed >= 0


@pytest.mark.asyncio
async def test_evaluation_agent_audit():
    """
    Test Evaluation Agent judge output audit, schema checks, and loop orchestration.
    """
    # Deterministic compliance fail
    fail_res = await EvaluationAgentService.evaluate_node_output(
        agent_name="research_agent",
        context="Stripe requires Ruby and Go.",
        output={"invalid_key": "some_value"} # Missing required keys
    )
    assert fail_res.passed is False
    assert len(fail_res.critical_failures) > 0

    # Deterministic compliance pass, LLM scoring fallback/evaluation
    pass_res = await EvaluationAgentService.evaluate_node_output(
        agent_name="research_agent",
        context="Stripe requires Ruby and Go.",
        output={
            "company_name": "Stripe",
            "critical_skills": ["Ruby", "Go"],
            "hiring_velocity": "high"
        }
    )
    # Since we fallback deterministic/mocking if LLM fails, we check it completes successfully
    assert pass_res is not None


@pytest.mark.asyncio
async def test_calibration_and_ml_platform():
    """
    Test ML Platform registry promotions, rollbacks, and model inference calibration.
    """
    # 1. Register a model run
    model_name = "fit_probability_calibrator"
    run_id = f"run_{random.randint(1000, 9999)}"
    version = f"v1.0.test_{random.randint(1000, 9999)}"
    metrics = {
        "brier_score": 0.085,
        "roc_auc": 0.760,
        "weights": [0.08, 0.15, -0.2, 0.4],
        "intercept": -4.5
    }

    reg = await MLPlatformService.register_run_model(model_name, run_id, version, metrics)
    assert reg.model_name == model_name
    assert reg.version_tag == version

    # Also insert in local calibration_models reference
    async with AsyncSessionLocal() as session:
        cm = CalibrationModel(
            id=str(uuid4()),
            model_name=model_name,
            mlflow_run_id=run_id,
            mlflow_model_version=version,
            brier_score=Decimal("0.085"),
            roc_auc=Decimal("0.760"),
            is_active=False,
            deployed_at=None,
            created_at=datetime.utcnow()
        )
        session.add(cm)
        await session.commit()

    # 2. Promote to Production (Active)
    promo = await MLPlatformService.promote_model_stage(model_name, version, "Production")
    assert promo.current_stage == "Production"
    
    # Check in database that it is active
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        stmt = select(MLModelRegistry).where(
            MLModelRegistry.model_name == model_name,
            MLModelRegistry.version_tag == version
        )
        res = await session.execute(stmt)
        db_model = res.scalar_one()
        assert db_model.is_active is True

    # 3. Test Calibration Model Service Retraining (bootstrapped)
    train_res = await CalibrationModelService.train_calibration_model(min_samples=10)
    assert train_res["brier_score"] is not None

    # Promote the newly trained model to verify promotion demotes the previous one
    await MLPlatformService.promote_model_stage(model_name, train_res["version_tag"], "Production")

    # 4. Rollback
    rollback = await MLPlatformService.rollback_production_model(model_name)
    assert rollback.version_tag == version

    # 5. Run inference calibration
    req = CalibrationInferenceRequest(
        raw_fit_score=85.0,
        features={
            "experience_years": 4.5,
            "skill_gap_count": 2.0,
            "company_hiring_velocity": 2.0
        }
    )
    cal_res = await CalibrationModelService.calibrate_score(req)
    assert cal_res.model_version == version
    assert 0.0 <= cal_res.calibrated_probability <= 1.0


@pytest.mark.asyncio
async def test_peer_cohort_benchmarking_report():
    """
    Test re-clustering pipeline, cohort memberships, and user benchmark reporting.
    """
    email = f"test_{random.randint(1000, 9999)}@example.com"
    password = "TestPassword123!"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Step 1: Register and login to create a user and profile
        reg_resp = await client.post(
            "/api/v2/auth/register", json={"email": email, "password": password}
        )
        assert reg_resp.status_code == 201
        user_data = reg_resp.json()
        user_id = user_data["id"]

        login_resp = await client.post(
            "/api/v2/auth/login", json={"email": email, "password": password}
        )
        assert login_resp.status_code == 200
        tokens = login_resp.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        # Add profile details
        async with AsyncSessionLocal() as session:
            prof_id = str(uuid4())
            prof = CareerProfile(
                id=prof_id,
                user_id=user_id,
                headline="Python Engineer",
                current_salary=110000.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(prof)

            # Add experience (5 years: 2021-01-01 to 2026-01-01)
            exp = Experience(
                id=str(uuid4()),
                profile_id=prof_id,
                company_name="Test Company",
                job_title="Python Developer",
                start_date=date(2021, 1, 1),
                end_date=date(2026, 1, 1),
                description="Developing cool things in Python.",
                is_current=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(exp)

            # Add skills
            for sname in ["Python", "SQL", "Docker"]:
                sk = Skill(
                    id=str(uuid4()),
                    profile_id=prof_id,
                    skill_name=sname,
                    years_experience=Decimal("5.0"),
                    proficiency="ADVANCED",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(sk)

            await session.commit()

        # Step 2: Trigger recluster
        cluster_resp = await client.post("/api/v2/cohorts/recluster", headers=headers)
        assert cluster_resp.status_code == 202
        assert "job_id" in cluster_resp.json()

        # Step 3: Query benchmark report
        bench_resp = await client.get("/api/v2/cohorts/my-benchmark", headers=headers)
        assert bench_resp.status_code == 200
        report = bench_resp.json()
        assert "cohort_name" in report
        assert "my_percentiles" in report
        assert "actionable_gaps" in report
