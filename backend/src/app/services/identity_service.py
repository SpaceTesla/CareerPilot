from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import CareerGoals, User, UserPreferences
from app.schemas.auth import (
    CareerGoalsUpdate,
    UserCreate,
    UserPreferencesUpdate,
)
from app.services.auth_service import AuthService
from app.utils.event_bus import EventBus


class IdentityService:
    """
    Manages user profile, preferences, and career goals.
    """

    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
        """
        Creates a new user account, initialization profiles, empty preferences,
        and empty career goals. Emits `identity.user_registered` event.
        """
        # Check if user exists
        stmt = select(User).where(User.email == user_in.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            # Constant time fallback to prevent email enumeration
            AuthService.hash_password("dummy_password")
            raise HTTPException(status_code=409, detail="User already exists")

        # Create user
        user_id = str(uuid4())
        hashed_pwd = AuthService.hash_password(user_in.password)
        db_user = User(
            id=user_id,
            email=user_in.email,
            password_hash=hashed_pwd,
            is_active=True,
        )
        db.add(db_user)

        # Create default preferences
        db_pref = UserPreferences(
            id=str(uuid4()),
            user_id=user_id,
            job_search_status="PASSIVE",
            weekly_digest_enabled=True,
            digest_delivery_day=1,
            digest_delivery_hour=9,
            email_notifications=True,
        )
        db.add(db_pref)

        # Create default career goals
        db_goals = CareerGoals(
            id=str(uuid4()),
            user_id=user_id,
            target_role="",
            target_compensation_min=0.0,
            target_compensation_max=0.0,
            target_companies=[],
            timeline_months=12,
        )
        db.add(db_goals)

        await db.flush()

        # Emit user registered event
        await EventBus.publish(
            "identity.user_registered",
            {"user_id": user_id, "email": user_in.email},
        )

        return db_user

    @staticmethod
    async def get_preferences(db: AsyncSession, user_id: UUID) -> UserPreferences:
        """
        Fetches settings record for a user.
        """
        stmt = select(UserPreferences).where(UserPreferences.user_id == str(user_id))
        result = await db.execute(stmt)
        pref = result.scalar_one_or_none()
        if not pref:
            raise HTTPException(status_code=404, detail="Preferences not found")
        return pref

    @staticmethod
    async def update_preferences(
        db: AsyncSession, user_id: UUID, pref_in: UserPreferencesUpdate
    ) -> UserPreferences:
        """
        Updates user preferences.
        """
        stmt = select(UserPreferences).where(UserPreferences.user_id == str(user_id))
        result = await db.execute(stmt)
        pref = result.scalar_one_or_none()
        if not pref:
            raise HTTPException(status_code=404, detail="Preferences not found")

        pref.job_search_status = pref_in.job_search_status.value
        pref.weekly_digest_enabled = pref_in.weekly_digest_enabled
        pref.digest_delivery_day = pref_in.digest_delivery_day
        pref.digest_delivery_hour = pref_in.digest_delivery_hour
        pref.email_notifications = pref_in.email_notifications
        await db.flush()
        return pref

    @staticmethod
    async def get_goals(db: AsyncSession, user_id: UUID) -> CareerGoals:
        """
        Fetches career goals record for a user.
        """
        stmt = select(CareerGoals).where(CareerGoals.user_id == str(user_id))
        result = await db.execute(stmt)
        goals = result.scalar_one_or_none()
        if not goals:
            raise HTTPException(status_code=404, detail="Goals not found")
        return goals

    @staticmethod
    async def update_goals(
        db: AsyncSession, user_id: UUID, goals_in: CareerGoalsUpdate
    ) -> CareerGoals:
        """
        Updates career goals. Emits `identity.goals_updated` event.
        """
        stmt = select(CareerGoals).where(CareerGoals.user_id == str(user_id))
        result = await db.execute(stmt)
        goals = result.scalar_one_or_none()
        if not goals:
            raise HTTPException(status_code=404, detail="Goals not found")

        goals.target_role = goals_in.target_role
        goals.target_compensation_min = goals_in.target_compensation_min
        goals.target_compensation_max = goals_in.target_compensation_max
        goals.target_companies = goals_in.target_companies
        goals.timeline_months = goals_in.timeline_months
        await db.flush()

        # Emit goals updated event
        await EventBus.publish(
            "identity.goals_updated",
            {
                "user_id": str(user_id),
                "target_role": goals_in.target_role,
                "target_compensation_min": goals_in.target_compensation_min,
                "target_compensation_max": goals_in.target_compensation_max,
            },
        )

        return goals
