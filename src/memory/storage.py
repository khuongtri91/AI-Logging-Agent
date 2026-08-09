import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils import get_settings


class UserMemoryStorage:
    """Resolve and initialize file-backed memory paths under one user directory."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        root_dir = Path(base_dir) if base_dir is not None else Path(get_settings().log_directory)
        self.base_dir = (root_dir / "users").resolve()

    def get_storage_dir(self, user_id: str = "default-user") -> Path:
        """Return the storage directory for one user, creating it if needed."""
        safe_user_id = _validate_storage_id(user_id)
        storage_dir = (self.base_dir / safe_user_id).resolve()
        _ensure_child_path(self.base_dir, storage_dir)
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir

    def get_session(self, user_id: str, session_id: str) -> Path:
        """Return the JSON file path for a user's chat session."""
        safe_session_id = _validate_storage_id(session_id)
        return self.get_sessions_dir(user_id) / f"session_{safe_session_id}.json"

    def get_sessions_dir(self, user_id: str) -> Path:
        """Return the session directory for one user, creating it if needed."""
        sessions_dir = self.get_storage_dir(user_id) / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        return sessions_dir

    def create_session(self, user_id: str, session_id: str) -> Path:
        """Create an empty session file if it does not exist and return its path."""
        session_path = self.get_session(user_id, session_id)
        if not session_path.exists():
            now = datetime.now().isoformat()
            write_json(
                session_path,
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "created_at": now,
                    "updated_at": now,
                    "messages": [],
                },
            )
        return session_path

    def list_sessions(self, user_id: str) -> list[str]:
        """Return stored session IDs for one user, newest first."""
        session_paths = sorted(
            self.get_sessions_dir(user_id).glob("session_*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return [session_path.stem.removeprefix("session_") for session_path in session_paths]

    def clear_sessions(self, user_id: str) -> None:
        """Delete every stored chat session for one user."""
        for session_path in self.get_sessions_dir(user_id).glob("session_*.json"):
            session_path.unlink()

    def get_incident_file(self, user_id: str) -> Path:
        """Return the JSON file path for a user's incident memory."""
        return self.get_incidents_dir(user_id) / "incident.json"

    def get_incidents_dir(self, user_id: str) -> Path:
        """Return the incident directory for one user, creating it if needed."""
        incidents_dir = self.get_storage_dir(user_id) / "incidents"
        incidents_dir.mkdir(exist_ok=True)
        return incidents_dir


def read_json_file(path: Path, default: Any) -> Any:
    """Read a JSON file, returning default when the file does not exist."""
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in memory file: {path}") from exc


def write_json(path: Path, data: Any) -> None:
    """Write JSON data to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )


def _validate_storage_id(value: str) -> str:
    """Validate a path segment used in memory storage paths."""
    if not value or not value.strip():
        raise ValueError("Storage id must not be empty")

    normalized_value = value.strip()
    if normalized_value in {".", ".."}:
        raise ValueError("Storage id must not be a relative path segment")

    if any(separator in normalized_value for separator in ("/", "\\")):
        raise ValueError("Storage id must not contain path separators")

    return normalized_value


def _ensure_child_path(base_dir: Path, child_path: Path) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    resolved_base = base_dir.resolve()

    if resolved_base not in child_path.parents:
        raise ValueError(f"Memory path must stay inside {resolved_base}")
