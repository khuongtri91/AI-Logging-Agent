from contextlib import nullcontext
from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from src.ui import chat, helper, progress, sidebar, state, styles


class SessionState(dict):
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


class FakeStatus:
    def __init__(self):
        self.updates = []
        self.writes = []

    def update(self, **kwargs):
        self.updates.append(kwargs)

    def write(self, text):
        self.writes.append(text)


class FakeStoredMessage:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self, mode="json"):
        return dict(self.payload)


def test_initialize_session_state_uses_cached_stores_and_default_user(monkeypatch):
    settings = SimpleNamespace(
        gemini_api_model="gemini",
        temperature=0.1,
        log_directory="logs",
        default_user_id="configured-user",
    )
    chat_store = SimpleNamespace()
    incident_store = SimpleNamespace(
        get_incidents_for_prompt=lambda user_id: ["incident"],
        format_for_prompt=lambda incidents: "incident context",
    )
    fake_streamlit = SimpleNamespace(session_state=SessionState())

    monkeypatch.setattr(state, "st", fake_streamlit)
    monkeypatch.setattr(state, "get_settings", lambda: settings)
    chat_store_calls = []
    incident_store_calls = []
    monkeypatch.setattr(
        state,
        "get_chat_store",
        lambda: chat_store_calls.append(None) or chat_store,
    )
    monkeypatch.setattr(
        state,
        "get_incident_store",
        lambda: incident_store_calls.append(None) or incident_store,
    )

    assert state.initialize_session_state() is settings
    assert state.initialize_session_state() is settings
    assert fake_streamlit.session_state.messages == []
    assert fake_streamlit.session_state.agent is None
    assert fake_streamlit.session_state.settings is settings
    assert fake_streamlit.session_state.user_id == "configured-user"
    assert fake_streamlit.session_state.session_id is None
    assert len(chat_store_calls) == 1
    assert len(incident_store_calls) == 1


def test_session_helpers_use_explicit_user_and_session_ids(monkeypatch):
    calls = []
    chat_store = SimpleNamespace(
        create_session=lambda user_id, session_id: calls.append(
            ("create", user_id, session_id)
        ),
        list_sessions=lambda user_id: calls.append(("list", user_id)) or ["saved-1"],
        load=lambda user_id, session_id: calls.append(("load", user_id, session_id))
        or [FakeStoredMessage({"role": "user", "content": "saved", "steps": []})],
        save=lambda user_id, session_id, messages: calls.append(
            ("save", user_id, session_id, messages)
        ),
    )
    agent = SimpleNamespace(set_incident_context=lambda context: setattr(agent, "context", context))
    incident_store = SimpleNamespace(
        get_incidents_for_prompt=lambda user_id: ["incident"],
        format_for_prompt=lambda incidents: "incident context",
    )
    fake_streamlit = SimpleNamespace(
        session_state=SessionState(
            chat_store=chat_store,
            incident_store=incident_store,
            agent=None,
        )
    )

    monkeypatch.setattr(helper, "st", fake_streamlit)
    monkeypatch.setattr(helper, "uuid4", lambda: SimpleNamespace(hex="new-session"))
    monkeypatch.setattr(
        helper,
        "get_log_analyzer_agent",
        lambda user_id, session_id: agent,
    )

    assert helper.create_chat_session("user-1") == "new-session"
    assert helper.list_chat_sessions("user-1") == ["saved-1"]
    assert helper.get_chat_session_label("user-1", "new-session") == "saved"
    helper.persist_chat_messages(
        "user-1",
        "new-session",
        [{"role": "assistant", "content": "saved", "steps": []}],
    )

    assert fake_streamlit.session_state.user_id == "user-1"
    assert fake_streamlit.session_state.session_id == "new-session"
    assert fake_streamlit.session_state.messages == [
        {"role": "user", "content": "saved", "steps": []}
    ]
    assert fake_streamlit.session_state.agent is agent
    assert agent.context == "incident context"
    assert ("create", "user-1", "new-session") in calls
    assert ("load", "user-1", "new-session") in calls
    assert ("list", "user-1") in calls
    assert calls[-1][0:3] == ("save", "user-1", "new-session")


def test_get_chat_session_label_limits_the_first_user_message(monkeypatch):
    chat_store = SimpleNamespace(
        load=lambda user_id, session_id: [
            FakeStoredMessage({"role": "assistant", "content": "Welcome", "steps": []}),
            FakeStoredMessage(
                {"role": "user", "content": "01234567890123456789 more", "steps": []}
            ),
        ]
    )
    fake_streamlit = SimpleNamespace(session_state=SessionState(chat_store=chat_store))

    monkeypatch.setattr(helper, "st", fake_streamlit)

    assert helper.get_chat_session_label("user-1", "session-1") == "01234567890123456789"


def test_get_chat_session_label_names_empty_sessions(monkeypatch):
    chat_store = SimpleNamespace(load=lambda user_id, session_id: [])
    fake_streamlit = SimpleNamespace(session_state=SessionState(chat_store=chat_store))

    monkeypatch.setattr(helper, "st", fake_streamlit)

    assert helper.get_chat_session_label("user-1", "session-1") == "Untitled chat"


def test_append_and_convert_messages(monkeypatch):
    fake_streamlit = SimpleNamespace(session_state=SessionState(messages=[]))
    monkeypatch.setattr(helper, "st", fake_streamlit)

    helper.append_message("user", "hello")
    helper.append_message("assistant", "hi")

    messages = helper.convert_to_langchain_messages(
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "system", "content": "ignored"},
        ]
    )

    assert fake_streamlit.session_state.messages == [
        {"role": "user", "content": "hello", "steps": []},
        {"role": "assistant", "content": "hi", "steps": []},
    ]
    assert isinstance(messages[0], HumanMessage)
    assert isinstance(messages[1], AIMessage)
    assert [message.content for message in messages] == ["hello", "hi"]


def test_tool_label_helpers_build_labels_from_tool_names():
    tools = [
        SimpleNamespace(name="list_log_files"),
        SimpleNamespace(name="restart_kubernetes_pod"),
    ]

    assert helper.format_tool_label("list_log_files") == "List log files"
    assert helper.format_tool_label("") == "Unknown tool"
    assert helper.build_tool_labels(tools) == {
        "list_log_files": "List log files",
        "restart_kubernetes_pod": "Restart kubernetes pod",
    }


def test_render_chat_interface_processes_prompt_and_persists(monkeypatch):
    calls = []
    fake_streamlit = SimpleNamespace(
        session_state=SessionState(messages=[{"role": "assistant", "content": "prior answer"}]),
        title=lambda text: calls.append(("title", text)),
        caption=lambda text: calls.append(("caption", text)),
        chat_input=lambda label: "What errors?",
        chat_message=lambda role: nullcontext(calls.append(("chat_message", role))),
        markdown=lambda text: calls.append(("markdown", text)),
        status=lambda label, expanded=False: FakeStatus(),
        info=lambda text: calls.append(("info", text)),
    )
    agent = SimpleNamespace(
        process_query=lambda prompt, callbacks=None, chat_history=None: calls.append(
            ("process", prompt, len(chat_history or []))
        )
        or "answer"
    )

    monkeypatch.setattr(chat, "st", fake_streamlit)
    monkeypatch.setattr(chat, "refresh_agent_context", lambda user_id: calls.append(("refresh", user_id)))
    monkeypatch.setattr(
        chat,
        "persist_chat_messages",
        lambda user_id, session_id, messages: calls.append(
            ("persist", user_id, session_id, len(messages))
        ),
    )
    monkeypatch.setattr(
        chat,
        "append_message",
        lambda role, content, steps=None: fake_streamlit.session_state.messages.append(
            {"role": role, "content": content, "steps": list(steps or [])}
        ),
    )

    chat.render_chat_interface(agent, "user-1", "session-1")

    assert ("refresh", "user-1") in calls
    assert ("process", "What errors?", 1) in calls
    assert calls.count(("persist", "user-1", "session-1", 2)) == 1
    assert calls.count(("persist", "user-1", "session-1", 3)) == 1
    assert fake_streamlit.session_state.messages[-2:] == [
        {"role": "user", "content": "What errors?", "steps": []},
        {"role": "assistant", "content": "answer", "steps": []},
    ]


def test_render_chat_messages_shows_empty_state(monkeypatch):
    calls = []
    fake_streamlit = SimpleNamespace(info=lambda text: calls.append(("info", text)))
    monkeypatch.setattr(chat, "st", fake_streamlit)

    chat.render_chat_messages([])

    assert calls == [("info", "Start by asking what log files are available.")]


def test_reset_actions_open_chat_clear_confirmation(monkeypatch):
    calls = []
    fake_streamlit = SimpleNamespace(
        session_state=SessionState(
            messages=[{"role": "user", "content": "hello"}],
            user_id="user-1",
            session_id="session-1",
        ),
        divider=lambda: calls.append(("divider", None)),
        container=lambda **kwargs: nullcontext(),
        button=lambda label, **kwargs: label == "Clear chat",
    )

    monkeypatch.setattr(sidebar, "st", fake_streamlit)
    monkeypatch.setattr(
        sidebar,
        "_confirm_clear_chat",
        lambda: calls.append(("confirm_chat", None)),
    )

    sidebar._render_reset_actions()

    assert ("confirm_chat", None) in calls
    assert fake_streamlit.session_state.messages == [{"role": "user", "content": "hello"}]
    assert fake_streamlit.session_state.session_id == "session-1"


def test_reset_actions_open_memory_clear_confirmation(monkeypatch):
    calls = []
    fake_streamlit = SimpleNamespace(
        session_state=SessionState(
            messages=[],
            user_id="user-1",
            session_id="session-1",
        ),
        divider=lambda: calls.append(("divider", None)),
        container=lambda **kwargs: nullcontext(),
        button=lambda label, **kwargs: label == "Clear memory",
    )

    monkeypatch.setattr(sidebar, "st", fake_streamlit)
    monkeypatch.setattr(
        sidebar,
        "_confirm_clear_memory",
        lambda: calls.append(("confirm_memory", None)),
    )

    sidebar._render_reset_actions()

    assert ("confirm_memory", None) in calls


def test_delete_all_chats_resets_session_state(monkeypatch):
    calls = []
    chat_store = SimpleNamespace(clear_all=lambda user_id: calls.append(("chat_clear_all", user_id)))
    fake_streamlit = SimpleNamespace(
        session_state=SessionState(
            messages=[{"role": "user", "content": "hello"}],
            user_id="user-1",
            session_id="session-1",
            agent=object(),
            chat_store=chat_store,
        ),
        rerun=lambda: calls.append(("rerun", None)),
    )

    monkeypatch.setattr(sidebar, "st", fake_streamlit)

    sidebar._delete_all_chats()

    assert ("chat_clear_all", "user-1") in calls
    assert ("rerun", None) in calls
    assert fake_streamlit.session_state.messages == []
    assert fake_streamlit.session_state.session_id is None
    assert fake_streamlit.session_state.agent is None


def test_delete_all_incidents_refreshes_agent_context(monkeypatch):
    calls = []
    incident_store = SimpleNamespace(clear=lambda user_id: calls.append(("memory_clear", user_id)))
    fake_streamlit = SimpleNamespace(
        session_state=SessionState(
            user_id="user-1",
            incident_store=incident_store,
        ),
        rerun=lambda: calls.append(("rerun", None)),
    )

    monkeypatch.setattr(sidebar, "st", fake_streamlit)
    monkeypatch.setattr(
        sidebar,
        "refresh_agent_context",
        lambda user_id: calls.append(("refresh", user_id)),
    )

    sidebar._delete_all_incidents()

    assert ("memory_clear", "user-1") in calls
    assert ("refresh", "user-1") in calls
    assert ("rerun", None) in calls


def test_render_chat_sessions_creates_a_session(monkeypatch):
    calls = []
    fake_streamlit = SimpleNamespace(
        session_state=SessionState(user_id="user-1", session_id=None),
        divider=lambda: calls.append(("divider", None)),
        subheader=lambda text: calls.append(("subheader", text)),
        button=lambda label, **kwargs: label == "New chat",
        rerun=lambda: calls.append(("rerun", None)),
    )

    monkeypatch.setattr(sidebar, "st", fake_streamlit)
    monkeypatch.setattr(
        sidebar,
        "create_chat_session",
        lambda user_id: calls.append(("create", user_id)),
    )
    monkeypatch.setattr(sidebar, "list_chat_sessions", lambda user_id: ["session-1"])

    sidebar._render_chat_sessions()

    assert ("create", "user-1") in calls
    assert ("rerun", None) in calls


def test_render_chat_sessions_selects_a_stored_session(monkeypatch):
    calls = []
    fake_streamlit = SimpleNamespace(
        session_state=SessionState(user_id="user-1", session_id="active-1"),
        divider=lambda: calls.append(("divider", None)),
        subheader=lambda text: calls.append(("subheader", text)),
        button=lambda label, **kwargs: label == "Saved session",
        rerun=lambda: calls.append(("rerun", None)),
    )

    monkeypatch.setattr(sidebar, "st", fake_streamlit)
    monkeypatch.setattr(sidebar, "list_chat_sessions", lambda user_id: ["saved-1"])
    monkeypatch.setattr(
        sidebar,
        "get_chat_session_label",
        lambda user_id, session_id: "Saved session",
    )
    monkeypatch.setattr(
        sidebar,
        "select_chat_session",
        lambda user_id, session_id: calls.append(("select", user_id, session_id)),
    )
    sidebar._render_chat_sessions()

    assert ("select", "user-1", "saved-1") in calls
    assert ("rerun", None) in calls


def test_apply_page_styles(monkeypatch):
    calls = []
    fake_streamlit = SimpleNamespace(
        markdown=lambda body, unsafe_allow_html=False: calls.append(
            ("markdown", ".block-container" in body, unsafe_allow_html)
        )
    )
    monkeypatch.setattr(styles, "st", fake_streamlit)

    styles.apply_page_styles()

    assert calls == [("markdown", True, True)]


def test_streamlit_progress_records_tool_steps():
    status = FakeStatus()
    progress_ui = progress.StreamlitProgress(status)

    progress_ui.on_thinking()
    progress_ui.on_reasoning("Inspecting the available logs")
    progress_ui.on_tool_start("list_log_files", {})
    progress_ui.on_tool_end("list_log_files", "app.log\nerror.log\nsystem.log")
    progress_ui.complete()

    assert status.updates == [
        {"label": "Thinking...", "state": "running"},
        {"label": "List log files...", "state": "running"},
        {"label": "Done - 1 tool used", "state": "complete", "expanded": False},
    ]
    assert status.writes == [
        "Inspecting the available logs...",
        "[OK] **List log files** - found 3 log files",
    ]
    assert progress_ui.steps == [
        {"label": "Reasoning", "detail": "Inspecting the available logs"},
        {"label": "List log files", "detail": "[OK] found 3 log files"},
    ]


def test_streamlit_progress_records_blocked_action_and_errors():
    status = FakeStatus()
    progress_ui = progress.StreamlitProgress(status)

    progress_ui.on_approval_skipped("restart_kubernetes_pod", {"pod_name": "api"})
    progress_ui.on_error("boom")
    progress_ui.complete()

    assert status.writes == [
        "[BLOCKED] **Restart kubernetes pod** - requires your approval",
    ]
    assert status.updates == [{"label": "Error", "state": "error"}]
    assert progress_ui.steps == [
        {"label": "Restart kubernetes pod", "detail": "[BLOCKED] requires approval"},
        {"label": "Error", "detail": "boom"},
    ]


def test_streamlit_progress_complete_without_tools():
    status = FakeStatus()
    progress_ui = progress.StreamlitProgress(status)

    progress_ui.complete()

    assert status.updates == [{"label": "Done", "state": "complete", "expanded": False}]


def test_summarize_result_handles_known_tools():
    assert progress.summarize_result("read_log_file", "File: app.log") == "log file read"
    assert progress.summarize_result("search_logs", "Found 2 matches\nLine 1") == "found 2 matches"
    assert progress.summarize_result("search_logs", "No matches found") == "search complete"
    assert progress.summarize_result("restart_kubernetes_pod", "Restarted") == "action initiated"
    assert progress.summarize_result("unknown_tool", "x" * 100) == "x" * 80
