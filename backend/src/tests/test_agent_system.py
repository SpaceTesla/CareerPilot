from __future__ import annotations

import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import json
import random
from datetime import date, datetime, timezone
from uuid import uuid4, UUID
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, delete
from unittest.mock import patch, MagicMock

from app.main import app
from app.infrastructure.database.models import (
    User,
    CareerProfile,
    Skill,
    CareerGoals,
    AgentSession,
    AgentRun,
    AgentDecisionLog,
    ResearchMemory,
    AgentIntelligenceReport,
    AgentApprovalRequest
)
from app.services.database_service import async_engine, AsyncSessionLocal
from langchain_core.messages import AIMessage


# Mock Tavily Client
class MockTavilyClient:
    def __init__(self, api_key=None):
        pass
    def search(self, query, max_results=5):
        return {
            "results": [
                {
                    "url": "https://cyberdyne.jobs",
                    "content": "Cyberdyne Systems ML team is hiring Python developers."
                }
            ]
        }


# Mock LLM ainvoke function
async def mock_ainvoke(self, prompt, *args, **kwargs):
    prompt_str = str(prompt)
    if "Supervisor Agent" in prompt_str:
        if "Executed Research Agent" in prompt_str:
            # Research already done, route to intelligence_agent
            return AIMessage(
                content=json.dumps({
                    "next_node": "intelligence_agent",
                    "reasoning": "Research completed. Ready for intelligence synthesis.",
                    "required_context": []
                })
            )
        elif "Executed Intelligence Agent" in prompt_str:
            # Intelligence done, route to end
            return AIMessage(
                content=json.dumps({
                    "next_node": "end",
                    "reasoning": "All workflows complete.",
                    "required_context": []
                })
            )
        else:
            # First, route to research
            return AIMessage(
                content=json.dumps({
                    "next_node": "research_agent",
                    "reasoning": "Researching target company info.",
                    "required_context": []
                })
            )
    elif "Company and Role Intelligence Researcher" in prompt_str:
        return AIMessage(
            content=json.dumps({
                "company_name": "Cyberdyne Systems",
                "company_domain": "cyberdyne.com",
                "role_category": "ml-engineer",
                "requirements": {
                    "critical": ["Python"],
                    "preferred": [],
                    "bonus": []
                },
                "signals": {
                    "hiring_velocity": "high",
                    "tech_stack": ["Python"],
                    "organizational_notes": "Defense AI focus."
                },
                "confidence_score": 0.95
            })
        )
    elif "Career Intelligence synthesis agent" in prompt_str:
        return AIMessage(
            content=json.dumps({
                "summary_explanation": "You are well-aligned with Cyberdyne Systems.",
                "evidence_trail": [
                    {
                        "claim": "Strong Python experience matches Cyberdyne ML stack.",
                        "source_reference": "profile_skills",
                        "source_type": "resume_experience",
                        "confidence_rating": "high"
                    }
                ],
                "profile_roadmap": [
                    {
                        "priority_order": 1,
                        "actionable_task": "Highlight defense-focused Python backends.",
                        "estimated_impact": "+15% fit improvement",
                        "associated_gaps": []
                    }
                ],
                "compensation_context": {
                    "market_percentile": 82.0,
                    "salary_range_min": 160000,
                    "salary_range_max": 210000,
                    "negotiation_advice": "Strong leverage with expert Python proficiency."
                }
            })
        )
    # Default fallback
    return AIMessage(content=json.dumps({"next_node": "end"}))


@pytest.fixture(scope="module", autouse=True)
async def cleanup_db_engine():
    await async_engine.dispose()
    yield
    await async_engine.dispose()


@pytest.mark.asyncio
@patch("app.services.agent.research.TavilyClient", MockTavilyClient)
@patch("langchain_google_genai.ChatGoogleGenerativeAI.ainvoke", mock_ainvoke)
async def test_agent_system_lifecycle():
    """
    End-to-end integration test for Wave 6: Agent System.
    Validates agent sessions, LangGraph background execution,
    caching research memories, and human-in-the-loop review.
    """
    email = f"agent_test_{random.randint(1000, 9999)}@example.com"
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

        # Retrieve user ID
        current_user_id = tokens.get("user_id")
        if not current_user_id:
            # Parse from access_token or just fetch from DB
            async with AsyncSessionLocal() as session:
                stmt = select(User).where(User.email == email)
                res = await session.execute(stmt)
                user = res.scalar_one()
                current_user_id = user.id

        # 2. Seed profile and career goals
        async with AsyncSessionLocal() as session:
            # Create Career Profile
            profile = CareerProfile(
                id=str(uuid4()),
                user_id=current_user_id,
                headline="Senior Developer",
                summary="AI backend developer",
                location="San Francisco, CA",
                current_salary=150000.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(profile)

            # Create Skills
            skill = Skill(
                id=str(uuid4()),
                profile_id=profile.id,
                skill_name="Python",
                years_experience=5.0,
                proficiency="EXPERT",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(skill)

            # Update default Career Goals created during register
            goals_stmt = select(CareerGoals).where(CareerGoals.user_id == current_user_id)
            goals_res = await session.execute(goals_stmt)
            goals = goals_res.scalar_one()
            goals.target_role = "Senior Python Engineer"
            goals.target_compensation_min = 160000.0
            goals.target_compensation_max = 220000.0
            goals.target_companies = ["Cyberdyne Systems"]
            goals.timeline_months = 6
            goals.updated_at = datetime.utcnow()
            await session.commit()

        # 3. Create Agent Session
        sess_resp = await client.post(
            "/api/v2/agents/session",
            json={"user_id": current_user_id},
            headers=headers
        )
        assert sess_resp.status_code == 201
        sess_data = sess_resp.json()
        thread_id = sess_data["thread_id"]
        assert thread_id is not None
        assert sess_data["status"] == "active"

        # 4. Trigger Workflow Run
        run_resp = await client.post(
            "/api/v2/agents/run",
            json={
                "thread_id": thread_id,
                "user_message": "Find alignment for Cyberdyne Systems Senior Python Engineer role.",
                "bypass_human_gate": False
            },
            headers=headers
        )
        assert run_resp.status_code == 202
        run_data = run_resp.json()
        assert run_data["status"] == "processing"

        # Give it a short moment for background task to initialize
        import asyncio
        await asyncio.sleep(1.0)

        # 5. Fetch Session State
        state_resp = await client.get(
            f"/api/v2/agents/session/{thread_id}/state",
            headers=headers
        )
        assert state_resp.status_code == 200
        state_data = state_resp.json()
        assert state_data["thread_id"] == thread_id

        # 6. Fetch Supervisor routing decisions
        dec_resp = await client.get(
            f"/api/v2/supervisor/sessions/{thread_id}/decisions",
            headers=headers
        )
        assert dec_resp.status_code == 200
        dec_data = dec_resp.json()
        assert "decisions" in dec_data

        # 7. Test ad-hoc research analyze API
        res_resp = await client.post(
            "/api/v2/research/analyze",
            json={
                "company_name": "Cyberdyne Systems",
                "job_description_raw": "Seeking staff engineer with Python skills",
                "bypass_cache": True
            },
            headers=headers
        )
        assert res_resp.status_code == 202
        res_data = res_resp.json()
        assert res_data["status"] == "queued"

        # 8. Test get cached company research
        comp_resp = await client.get(
            "/api/v2/research/company/Cyberdyne Systems",
            headers=headers
        )
        assert comp_resp.status_code == 200
        comp_data = comp_resp.json()
        assert comp_data["company_name"] == "Cyberdyne Systems"
        assert "Python" in comp_data["requirements"]["critical"]

        # 9. Test Human-in-the-loop: manually create approval request to check APIs
        approval_id = str(uuid4())
        async with AsyncSessionLocal() as session:
            app_req = AgentApprovalRequest(
                id=approval_id,
                user_id=current_user_id,
                thread_id=thread_id,
                action_type="submit_job_application",
                payload={"job_title": "Senior Python Architect", "company_name": "Cyberdyne Systems"},
                status="pending",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(app_req)
            await session.commit()

        # List pending approvals
        list_resp = await client.get(
            "/api/v2/approvals/pending",
            headers=headers
        )
        assert list_resp.status_code == 200
        pending_list = list_resp.json()
        assert len(pending_list) >= 1
        assert pending_list[0]["id"] == approval_id

        # Take action (Approve/Edit)
        action_resp = await client.post(
            f"/api/v2/approvals/{approval_id}/action",
            json={
                "action": "approved",
                "edited_payload": {"job_title": "Lead Python Engineer", "company_name": "Cyberdyne Systems"}
            },
            headers=headers
        )
        assert action_resp.status_code == 200
        action_data = action_resp.json()
        assert action_data["status"] == "edited"
        assert action_data["workflow_status"] == "resumed"
