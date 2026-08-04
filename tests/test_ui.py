from contextlib import nullcontext
from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from src.ui import chat, sidebar, state, styles


class SessionState(dict):
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


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
    monkeypatch.setattr(state, "st", fake_streamlit)

    state.append_message("user", "hello")
    state.append_message("assistant", "hi")

    messages = state.convert_to_langchain_messages(
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "system", "content": "ignored"},
        ]
    )

    assert fake_streamlit.session_state.messages == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    assert isinstance(messages[0], HumanMessage)
    assert isinstance(messages[1], AIMessage)
    assert [message.content for message in messages] == ["hello", "hi"]


def test_render_chat_interface_processes_prompt(monkeypatch):
    calls = []
    fake_streamlit = SimpleNamespace(
        session_state=SessionState(messages=[{"role": "assistant", "content": "prior answer"}]),
        title=lambda text: calls.append(("title", text)),
        caption=lambda text: calls.append(("caption", text)),
        chat_input=lambda label: "What errors?",
        chat_message=lambda role: nullcontext(calls.append(("chat_message", role))),
        markdown=lambda text: calls.append(("markdown", text)),
        spinner=lambda label: nullcontext(calls.append(("spinner", label))),
        info=lambda text: calls.append(("info", text)),
    )
    agent = SimpleNamespace(
        process_query=lambda prompt, chat_history=None: calls.append(
            ("process", prompt, len(chat_history or []))
        )
        or "answer"
    )

    monkeypatch.setattr(chat, "st", fake_streamlit)
    monkeypatch.setattr(
        chat,
        "append_message",
        lambda role, content: fake_streamlit.session_state.messages.append(
            {"role": role, "content": content}
        ),
    )

    chat.render_chat_interface(agent)

    assert ("process", "What errors?", 1) in calls
    assert fake_streamlit.session_state.messages[-2:] == [
        {"role": "user", "content": "What errors?"},
        {"role": "assistant", "content": "answer"},
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
