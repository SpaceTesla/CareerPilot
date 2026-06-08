from __future__ import annotations

import random

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.services.auth_service import AuthService

# 1. Unit Tests


def test_password_hashing():
    """
    Assert bcrypt correctly hashes and validates password strings.
    """
    password = "MySecurePassword123!"
    hashed = AuthService.hash_password(password)
    assert hashed != password
    assert AuthService.verify_password(password, hashed) is True
    assert AuthService.verify_password("wrong_password", hashed) is False


def test_token_lifespan():
    """
    Assert JWT access tokens expire in exactly 15 minutes.
    """
    # Create access token and decode it
    import time
    from uuid import uuid4
    user_id = uuid4()
    access_token = AuthService.create_access_token(user_id)
    secret = settings.jwt_secret or "replace-with-strong-secret"
    payload = jwt.decode(
        access_token, secret, algorithms=[settings.jwt_algorithm]
    )

    # Check expiration timestamp
    exp = payload["exp"]
    now = int(time.time())
    expected_exp = now + 15 * 60

    # Allow 5 seconds buffer for execution time
    assert abs(exp - expected_exp) < 5


# 2. Integration Tests


@pytest.mark.asyncio
async def test_auth_and_identity_cycle():
    """
    Test the full Auth cycle: Register -> Login -> Use access token on protected
    resource -> Refresh access token -> Revoke refresh token (race condition test).
    Also validates career goal inputs.
    """
    email = f"test_{random.randint(1000, 9999)}@example.com"
    password = "TestPassword123!"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Step 1: Register
        register_response = await client.post(
            "/api/v2/auth/register", json={"email": email, "password": password}
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        assert user_data["email"] == email
        assert "id" in user_data

        # Step 2: Login
        login_response = await client.post(
            "/api/v2/auth/login", json={"email": email, "password": password}
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "bearer"

        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]

        # Step 3: Access protected resource (Preferences)
        headers = {"Authorization": f"Bearer {access_token}"}
        pref_response = await client.get(
            "/api/v2/identity/preferences", headers=headers
        )
        assert pref_response.status_code == 200
        pref_data = pref_response.json()
        assert pref_data["job_search_status"] == "PASSIVE"
        assert pref_data["weekly_digest_enabled"] is True

        # Step 4: Update preferences
        update_pref_response = await client.put(
            "/api/v2/identity/preferences",
            json={
                "job_search_status": "ACTIVE",
                "weekly_digest_enabled": False,
                "email_notifications": True,
            },
            headers=headers,
        )
        assert update_pref_response.status_code == 200
        updated_pref_data = update_pref_response.json()
        assert updated_pref_data["job_search_status"] == "ACTIVE"
        assert updated_pref_data["weekly_digest_enabled"] is False

        # Step 5: Get goals
        goals_response = await client.get("/api/v2/identity/goals", headers=headers)
        assert goals_response.status_code == 200
        goals_data = goals_response.json()
        assert goals_data["target_role"] == ""
        assert goals_data["target_compensation_min"] == 0.0

        # Step 6: Update goals
        update_goals_response = await client.put(
            "/api/v2/identity/goals",
            json={
                "target_role": "AI Platform Engineer",
                "target_compensation_min": 180000.00,
                "target_compensation_max": 230000.00,
                "target_companies": ["Google", "Anthropic"],
                "timeline_months": 6,
            },
            headers=headers,
        )
        assert update_goals_response.status_code == 200
        updated_goals_data = update_goals_response.json()
        assert updated_goals_data["target_role"] == "AI Platform Engineer"
        assert updated_goals_data["target_compensation_min"] == 180000.00
        assert updated_goals_data["target_companies"] == ["Google", "Anthropic"]

        # Step 7: Validate validation rules (min > max compensation)
        invalid_goals_response = await client.put(
            "/api/v2/identity/goals",
            json={
                "target_role": "AI Platform Engineer",
                "target_compensation_min": 250000.00,
                "target_compensation_max": 200000.00,
                "target_companies": ["Google"],
                "timeline_months": 6,
            },
            headers=headers,
        )
        assert invalid_goals_response.status_code == 422

        # Step 8: Refresh token
        refresh_response = await client.post(
            "/api/v2/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == 200
        new_token_data = refresh_response.json()
        assert "access_token" in new_token_data
        assert "refresh_token" in new_token_data

        new_access_token = new_token_data["access_token"]

        # Test protected endpoint with new access token
        new_headers = {"Authorization": f"Bearer {new_access_token}"}
        pref_response_after_refresh = await client.get(
            "/api/v2/identity/preferences", headers=new_headers
        )
        assert pref_response_after_refresh.status_code == 200

        # Step 9: Test token rotation race condition / double-click grace period
        cached_refresh_response = await client.post(
            "/api/v2/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert cached_refresh_response.status_code == 200
        cached_token_data = cached_refresh_response.json()
        assert cached_token_data["refresh_token"] == new_token_data["refresh_token"]


@pytest.mark.asyncio
async def test_protected_route_unauthorized(monkeypatch):
    """
    Ensure routes block requests with invalid, missing, or expired tokens.
    """
    # Force authentication to be required
    monkeypatch.setattr(settings, "auth_required", True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v2/identity/preferences")
        assert response.status_code == 401

        response = await client.get(
            "/api/v2/identity/preferences",
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert response.status_code == 401
