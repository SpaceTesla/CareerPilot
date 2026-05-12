from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.database.models import PortalSession


class PortalSessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(
        self, user_id: str, portal: str, storage_state: dict[str, Any]
    ) -> PortalSession:
        """Create or update the saved session for this user+portal pair."""
        stmt = (
            select(PortalSession)
            .where(PortalSession.user_id == user_id)
            .where(PortalSession.portal == portal)
        )
        existing = self.session.scalars(stmt).first()
        if existing:
            existing.storage_state = storage_state
            self.session.flush()
            return existing

        ps = PortalSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            portal=portal,
            storage_state=storage_state,
        )
        self.session.add(ps)
        self.session.flush()
        return ps

    def get(self, user_id: str, portal: str) -> PortalSession | None:
        stmt = (
            select(PortalSession)
            .where(PortalSession.user_id == user_id)
            .where(PortalSession.portal == portal)
        )
        return self.session.scalars(stmt).first()

    def delete(self, user_id: str, portal: str) -> bool:
        ps = self.get(user_id, portal)
        if not ps:
            return False
        self.session.delete(ps)
        self.session.flush()
        return True

    def list_for_user(self, user_id: str) -> list[PortalSession]:
        stmt = select(PortalSession).where(PortalSession.user_id == user_id)
        return list(self.session.scalars(stmt).all())
