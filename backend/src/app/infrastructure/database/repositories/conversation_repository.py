from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.infrastructure.database.models import Conversation, Message


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, conversation_id: str) -> Conversation | None:
        return self.session.get(Conversation, conversation_id)

    def get_by_user(self, user_id: str, limit: int = 50) -> list[Conversation]:
        """Get all conversations for a user, ordered by most recent first."""
        return (
            self.session.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .all()
        )

    def get_messages(
        self, conversation_id: str, limit: int = 100
    ) -> list[Message]:
        """Get all messages in a conversation, ordered by timestamp."""
        return (
            self.session.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp)
            .limit(limit)
            .all()
        )

    def create_conversation(
        self, user_id: str, title: str | None = None
    ) -> Conversation:
        conv = Conversation(id=str(uuid.uuid4()), user_id=user_id, title=title)
        self.session.add(conv)
        self.session.flush()
        return conv

    def update_conversation_title(
        self, conversation_id: str, title: str
    ) -> Conversation | None:
        """Update the title of a conversation."""
        conv = self.get_by_id(conversation_id)
        if conv:
            conv.title = title
            self.session.flush()
        return conv

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        conv = self.get_by_id(conversation_id)
        if conv:
            # Delete all messages first
            self.session.query(Message).filter(
                Message.conversation_id == conversation_id
            ).delete()
            self.session.delete(conv)
            self.session.flush()
            return True
        return False

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
