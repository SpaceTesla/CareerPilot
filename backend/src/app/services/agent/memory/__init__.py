"""In-memory conversation buffer for the agent."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque, Dict, List

from langchain_core.messages import BaseMessage


class ConversationMemory:
    """Simple per-user conversation memory with a capped buffer."""

    def __init__(self, max_messages: int = 20) -> None:
        self.max_messages = max_messages
        self._store: Dict[str, Deque[BaseMessage]] = defaultdict(
            lambda: deque(maxlen=self.max_messages)
        )

    def _key(self, user_id: str | None) -> str:
        return user_id or "_anonymous"

    def get(self, user_id: str | None) -> List[BaseMessage]:
        """Return a copy of the stored history for a user."""
        key = self._key(user_id)
        history = self._store.get(key)
        if not history:
            return []
        return list(history)

    def append(self, user_id: str | None, message: BaseMessage) -> None:
        """Append a message to the user's history."""
        key = self._key(user_id)
        self._store[key].append(message)

    def clear(self, user_id: str | None = None) -> None:
        """Clear history for a specific user or the entire store."""
        if user_id is None:
            self._store.clear()
        else:
            key = self._key(user_id)
            self._store.pop(key, None)


__all__ = ["ConversationMemory"]
