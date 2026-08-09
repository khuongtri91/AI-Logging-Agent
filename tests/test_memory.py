import json

import pytest

from src.memory import (
    ChatMessageRecord,
    ChatStore,
    IncidentCreateInput,
    IncidentStore,
    UserMemoryStorage,
)


def test_chat_store_saves_and_loads_session_messages(tmp_path):
    storage = UserMemoryStorage(base_dir=tmp_path / "logs")
    store = ChatStore(storage=storage)
    messages = [
        ChatMessageRecord(role="user", content="What errors?"),
        ChatMessageRecord(
            role="assistant",
            content="I found timeout errors.",
            steps=[{"label": "Search logs", "detail": "[OK] found 2 matches"}],
        ),
    ]

    store.save("user-1", "chat-1", messages)

    session_path = (
        tmp_path / "logs" / "users" / "user-1" / "sessions" / "session_chat-1.json"
    )
    persisted = json.loads(session_path.read_text(encoding="utf-8"))

    assert session_path.exists()
    assert persisted["user_id"] == "user-1"
    assert persisted["session_id"] == "chat-1"
    assert persisted["messages"][0]["role"] == "user"
    assert store.load("user-1", "chat-1") == messages


def test_chat_store_loads_missing_session_as_empty_list(tmp_path):
    store = ChatStore(storage=UserMemoryStorage(base_dir=tmp_path / "logs"))

    assert store.load("user-1", "missing") == []


def test_create_session_initializes_empty_session_file(tmp_path):
    storage = UserMemoryStorage(base_dir=tmp_path / "logs")

    session_path = storage.create_session("user-1", "chat-1")
    session = json.loads(session_path.read_text(encoding="utf-8"))

    assert session_path == (
        tmp_path / "logs" / "users" / "user-1" / "sessions" / "session_chat-1.json"
    )
    assert session["messages"] == []
    assert session["created_at"] == session["updated_at"]


def test_chat_store_creates_and_lists_sessions(tmp_path):
    store = ChatStore(storage=UserMemoryStorage(base_dir=tmp_path / "logs"))

    store.create_session("user-1", "chat-1")
    store.create_session("user-1", "chat-2")

    assert set(store.list_sessions("user-1")) == {"chat-1", "chat-2"}

    store.clear_all("user-1")

    assert store.list_sessions("user-1") == []


def test_storage_rejects_path_traversal_segments(tmp_path):
    storage = UserMemoryStorage(base_dir=tmp_path / "logs")

    with pytest.raises(ValueError, match="Storage id"):
        storage.get_storage_dir("../user-1")

    with pytest.raises(ValueError, match="Storage id"):
        storage.get_session("user-1", "nested/chat")


def test_chat_store_raises_for_invalid_json(tmp_path):
    storage = UserMemoryStorage(base_dir=tmp_path / "logs")
    session_path = storage.get_session("user-1", "chat-1")
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON"):
        ChatStore(storage=storage).load("user-1", "chat-1")


def test_incident_store_adds_searches_formats_and_clears_incidents(tmp_path):
    storage = UserMemoryStorage(base_dir=tmp_path / "logs")
    store = IncidentStore(storage=storage)

    first = store.add(
        "user-1",
        IncidentCreateInput(
            summary="Checkout service returned 500 errors",
            severity="P1",
            root_cause="Database connection pool exhausted",
            affected_systems="checkout-api",
            resolution="Increased pool size",
            session_id="chat-1",
        ),
    )
    second = store.add(
        "user-1",
        IncidentCreateInput(
            summary="Worker queue latency increased",
            severity="P2",
            affected_systems="worker",
        ),
    )

    incident_path = tmp_path / "logs" / "users" / "user-1" / "incidents" / "incident.json"

    assert incident_path.exists()
    assert len(first.id) == 32
    assert len(second.id) == 32
    assert first.id.isalnum()
    assert second.id.isalnum()
    assert first.id != second.id
    assert json.loads(incident_path.read_text(encoding="utf-8"))[0]["id"] == first.id
    assert store.count("user-1") == 2
    assert [incident.id for incident in store.get_all("user-1")] == [second.id, first.id]
    assert store.get_recent("user-1", count=1) == [second]
    assert store.search("user-1", "database") == [first]

    prompt_context = store.format_for_prompt(store.get_all("user-1"))

    assert "PAST INCIDENTS (from long-term memory):" in prompt_context
    assert "[P1] Checkout service returned 500 errors" in prompt_context
    assert "Root cause: Database connection pool exhausted" in prompt_context
    assert "Resolution: Increased pool size" in prompt_context

    store.clear("user-1")

    assert store.count("user-1") == 0
    assert not incident_path.exists()


def test_incident_store_selects_prompt_context_from_saved_incident_severity(tmp_path):
    storage = UserMemoryStorage(base_dir=tmp_path / "logs")
    store = IncidentStore(storage=storage)
    p1_incident = store.add(
        "user-1",
        IncidentCreateInput(summary="Production unavailable", severity="P1"),
    )
    for index in range(5):
        store.add(
            "user-1",
            IncidentCreateInput(
                summary=f"P2 incident {index}",
                severity="P2",
            ),
        )
    store.add(
        "user-1",
        IncidentCreateInput(summary="Informational incident", severity="info"),
    )
    store.add(
        "user-1",
        IncidentCreateInput(summary="P3 incident", severity="P3"),
    )

    incidents = store.get_incidents_for_prompt("user-1")

    assert [incident.summary for incident in incidents] == [
        p1_incident.summary,
        "P2 incident 4",
        "P2 incident 3",
        "P2 incident 2",
        "P2 incident 1",
    ]
    assert all(incident.severity in {"P1", "P2"} for incident in incidents)
