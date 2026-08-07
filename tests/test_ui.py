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


def test_initialize_session_state_creates_agent_once(monkeypatch):
    settings = SimpleNamespace(gemini_api_model="gemini", temperature=0.1, log_directory="logs")
    agent = SimpleNamespace(settings=settings)
    fake_streamlit = SimpleNamespace(session_state=SessionState())

    monkeypatch.setattr(state, "st", fake_streamlit)
    monkeypatch.setattr(state, "get_settings", lambda: settings)
    monkeypatch.setattr(state, "LogAnalyzerAgent", lambda: agent)

    assert state.initialize_session_state() is settings
    assert fake_streamlit.session_state.messages == []
    assert fake_streamlit.session_state.agent is agent
    assert fake_streamlit.session_state.settings is settings


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


def test_render_chat_interface_processes_prompt(monkeypatch):
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
    monkeypatch.setattr(
        chat,
        "append_message",
        lambda role, content, steps=None: fake_streamlit.session_state.messages.append(
            {"role": role, "content": content, "steps": list(steps or [])}
        ),
    )

    chat.render_chat_interface(agent)

    assert ("process", "What errors?", 1) in calls
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


def test_render_sidebar_clears_chat(monkeypatch):
    calls = []
    fake_streamlit = SimpleNamespace(
        session_state=SessionState(messages=[{"role": "user", "content": "hello"}]),
        sidebar=nullcontext(),
        title=lambda text: calls.append(("title", text)),
        caption=lambda text: calls.append(("caption", text)),
        divider=lambda: calls.append(("divider", None)),
        subheader=lambda text: calls.append(("subheader", text)),
        text=lambda text: calls.append(("text", text)),
        markdown=lambda text: calls.append(("markdown", text)),
        code=lambda text, language=None: calls.append(("code", text, language)),
        button=lambda label, use_container_width=False: True,
        rerun=lambda: calls.append(("rerun", None)),
    )
    settings = SimpleNamespace(gemini_api_model="gemini", temperature=0.2, log_directory="logs")

    monkeypatch.setattr(sidebar, "st", fake_streamlit)

    sidebar.render_sidebar(settings)

    assert fake_streamlit.session_state.messages == []
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
