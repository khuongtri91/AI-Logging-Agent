from collections.abc import Sequence
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from src.memory.storage import UserMemoryStorage, read_json_file, write_json
from src.memory.types import ChatMessageRecord, ChatSessionRecord


class ChatStore:
    """File-backed conversation store."""

    def __init__(self, storage: UserMemoryStorage | None = None) -> None:
        self.storage = storage or UserMemoryStorage()

    def load(self, user_id: str, session_id: str) -> list[ChatMessageRecord]:
        """Load messages for one chat session. Returns an empty list if no file exists."""
        session_path = self.storage.get_session(user_id, session_id)
        data = read_json_file(session_path, default=None)
        if data is None:
            return []

        session = ChatSessionRecord.model_validate(data)
        return session.messages

    def create_session(self, user_id: str, session_id: str) -> None:
        """Create an empty chat session when it does not already exist."""
        self.storage.create_session(user_id, session_id)

    def list_sessions(self, user_id: str) -> list[str]:
        """Return a user's stored session IDs, newest first."""
        return self.storage.list_sessions(user_id)

    def save(
        self,
        user_id: str,
        session_id: str,
        messages: Sequence[ChatMessageRecord],
    ) -> None:
        """Write the full message list to one chat session file."""
        session_path = self.storage.create_session(user_id, session_id)
        chat_data = _load_existing_session(session_path)
        now = datetime.now().isoformat()

        session = ChatSessionRecord(
            user_id=user_id,
            session_id=session_id,
            created_at=chat_data.created_at if chat_data else now,
            updated_at=now,
            messages=[ChatMessageRecord.model_validate(message) for message in messages],
        )
        write_json(session_path, session.model_dump(mode="json"))

    def clear(self, user_id: str, session_id: str) -> None:
        """Delete one stored chat session."""
        session_path = self.storage.get_session(user_id, session_id)
        if session_path.exists():
            session_path.unlink()

    def clear_all(self, user_id: str) -> None:
        """Delete every stored chat session for a user."""
        self.storage.clear_sessions(user_id)


def _load_existing_session(session_path: Path) -> ChatSessionRecord | None:
    raw_chat_data = read_json_file(session_path, default=None)
    if raw_chat_data is None:
        return None

    return ChatSessionRecord.model_validate(raw_chat_data)


@lru_cache
def get_chat_store() -> ChatStore:
    """Return the shared stateless chat store resource."""
    return ChatStore()
