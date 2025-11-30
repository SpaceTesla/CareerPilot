"""Repository for user session management."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.infrastructure.database.models import UserSession, ResumeProfile


class SessionRepository:
    """Repository for managing user sessions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, session_id: str) -> UserSession | None:
        """Get a session by ID."""
        return self.session.get(UserSession, session_id)

    def get_by_user(self, user_id: str, limit: int = 20) -> list[UserSession]:
        """Get all sessions for a user, ordered by last accessed."""
        return (
            self.session.query(UserSession)
            .filter(UserSession.user_id == user_id)
            .order_by(desc(UserSession.last_accessed_at))
            .limit(limit)
            .all()
        )

    def get_active_session(self, user_id: str) -> UserSession | None:
        """Get the currently active session for a user."""
        return (
            self.session.query(UserSession)
            .filter(UserSession.user_id == user_id, UserSession.is_active == True)
            .order_by(desc(UserSession.last_accessed_at))
            .first()
        )

    def create_session(
        self,
        user_id: str,
        profile_id: str,
        name: str | None = None,
    ) -> UserSession:
        """Create a new session and set it as active."""
        # Deactivate other sessions for this user
        self.session.query(UserSession).filter(
            UserSession.user_id == user_id
        ).update({"is_active": False})

        # Create new session
        new_session = UserSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            profile_id=profile_id,
            name=name,
            is_active=True,
        )
        self.session.add(new_session)
        self.session.flush()
        return new_session

    def switch_session(self, session_id: str, user_id: str) -> UserSession | None:
        """Switch to a different session (set it as active)."""
        target_session = self.get_by_id(session_id)
        if not target_session or target_session.user_id != user_id:
            return None

        # Deactivate all other sessions
        self.session.query(UserSession).filter(
            UserSession.user_id == user_id
        ).update({"is_active": False})

        # Activate the target session
        target_session.is_active = True
        target_session.last_accessed_at = datetime.utcnow()
        self.session.flush()

        return target_session

    def update_last_accessed(self, session_id: str) -> None:
        """Update the last accessed timestamp."""
        session = self.get_by_id(session_id)
        if session:
            session.last_accessed_at = datetime.utcnow()
            self.session.flush()

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        session = self.get_by_id(session_id)
        if session:
            self.session.delete(session)
            self.session.flush()
            return True
        return False

    def get_session_with_profile(
        self, session_id: str
    ) -> dict[str, Any] | None:
        """Get session with associated profile data."""
        session = self.get_by_id(session_id)
        if not session:
            return None

        profile = self.session.get(ResumeProfile, session.profile_id)
        if not profile:
            return None

        return {
            "session_id": session.id,
            "user_id": session.user_id,
            "profile_id": session.profile_id,
            "name": session.name or profile.name or "Unnamed Resume",
            "is_active": session.is_active,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "last_accessed_at": session.last_accessed_at.isoformat() if session.last_accessed_at else None,
            "profile": {
                "name": profile.name,
                "email": profile.email,
                "summary": profile.summary[:100] + "..." if profile.summary and len(profile.summary) > 100 else profile.summary,
            },
        }

    def list_sessions_with_profiles(
        self, user_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """List all sessions with their profile data."""
        sessions = self.get_by_user(user_id, limit)
        result = []

        for session in sessions:
            profile = self.session.get(ResumeProfile, session.profile_id)
            result.append({
                "session_id": session.id,
                "user_id": session.user_id,
                "profile_id": session.profile_id,
                "name": session.name or (profile.name if profile else None) or "Unnamed Resume",
                "is_active": session.is_active,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "last_accessed_at": session.last_accessed_at.isoformat() if session.last_accessed_at else None,
            })

        return result
