from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.infrastructure.database.models import Conversation, Message


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, conversation_id: str) -> Conversation | None:
        return self.session.get(Conversation, conversation_id)

    def create_conversation(
        self, user_id: str, title: str | None = None
    ) -> Conversation:
        conv = Conversation(id=str(uuid.uuid4()), user_id=user_id, title=title)
        self.session.add(conv)
        self.session.flush()
        return conv

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata_json=metadata or {},
        )
        self.session.add(msg)
        self.session.flush()
        return msg
