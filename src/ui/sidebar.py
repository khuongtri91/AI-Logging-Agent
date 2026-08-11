import streamlit as st

from src.memory import IncidentCreateInput
from src.tools import get_agent_tools
from src.ui.helper import (
    create_chat_session,
    get_chat_session_label,
    list_chat_sessions,
    refresh_agent_context,
    select_chat_session,
)
from src.utils import P1_SEVERITY, P2_SEVERITY, Settings


EXAMPLE_PROMPTS = [
    "What log files are available?",
    "Read the app.log file",
    "What errors are in error.log?",
    "Search for database in app.log",
]


def render_sidebar(settings: Settings) -> None:
    """Render sidebar controls, runtime metadata, and memory management."""
    with st.sidebar:
        st.title("AI Log Analyzer")
        st.caption("Level 1 log analysis agent")

        st.divider()
        st.subheader("Runtime")
        st.text(f"Model: {settings.gemini_api_model}")
        st.text(f"Temperature: {settings.temperature}")
        st.text(f"Logs: {settings.log_directory}")

        st.divider()
        st.subheader("Tools")
        st.markdown("\n".join(f"- `{tool.name}`" for tool in get_agent_tools()))

        st.divider()
        st.subheader("Examples")
        for prompt in EXAMPLE_PROMPTS:
            st.code(prompt, language=None)

        _render_chat_sessions()
        _render_memory_section()
        _render_incident_form()
        _render_reset_actions()


def _render_memory_section() -> None:
    incident_store = st.session_state.incident_store
    user_id = st.session_state.user_id
    incident_count = incident_store.count(user_id)

    st.divider()
    st.subheader("Memory")
    st.markdown(f"- Chat messages: **{len(st.session_state.messages)}**")
    st.markdown(f"- Past incidents: **{incident_count}**")

    if incident_count <= 0:
        return

    with st.expander("Recent incidents", expanded=False):
        for incident in incident_store.get_recent(user_id, count=5):
            st.write(
                f"**[{incident.severity}]** {incident.summary}\n"
                f"_{incident.timestamp[:10]}_"
            )


def _render_chat_sessions() -> None:
    user_id = st.session_state.user_id
    active_session_id = st.session_state.session_id

    st.divider()
    st.subheader("Chats")
    if st.button("New chat"):
        create_chat_session(user_id)
        st.rerun()
        return

    for session_id in list_chat_sessions(user_id):
        label = get_chat_session_label(user_id, session_id)
        button_type = "primary" if session_id == active_session_id else "secondary"
        if st.button(
            label,
            key=f"chat-session-{session_id}",
            type=button_type,
        ):
            if session_id != active_session_id:
                select_chat_session(user_id, session_id)
                st.rerun()
            return


def _render_incident_form() -> None:
    st.divider()
    st.subheader("Save incident")
    with st.form("save_incident", clear_on_submit=True):
        summary = st.text_input(
            "Summary",
            placeholder="RDS connection exhaustion on orders-db-prod",
        )
        severity = st.selectbox("Severity", [P1_SEVERITY, P2_SEVERITY, "P3", "info"])
        root_cause = st.text_input(
            "Root cause",
            placeholder="3 pods x 50 conn = 150 max",
        )
        resolution = st.text_input(
            "Resolution",
            placeholder="RDS reboot, pool resize to 30",
        )
        affected_systems = st.text_input(
            "Affected systems",
            placeholder="orders-db-prod, backend pods",
        )
        submitted = st.form_submit_button("Save to memory")

    if not submitted or not summary.strip():
        return

    incident = IncidentCreateInput(
        summary=summary.strip(),
        severity=severity,
        root_cause=root_cause.strip(),
        resolution=resolution.strip(),
        affected_systems=affected_systems.strip(),
        session_id=st.session_state.session_id or "",
    )
    st.session_state.incident_store.add(st.session_state.user_id, incident)
    refresh_agent_context(st.session_state.user_id)
    st.rerun()


def _render_reset_actions() -> None:
    st.divider()
    with st.container(horizontal=True):
        clear_chat = st.button("Clear chat")
        clear_memory = st.button("Clear memory")

    if clear_chat:
        _confirm_clear_chat()

    if clear_memory:
        _confirm_clear_memory()


@st.dialog("Clear all chats?", dismissible=False)
def _confirm_clear_chat() -> None:
    """Confirm permanent deletion of every stored chat for the current user."""
    st.warning("This permanently deletes all of your saved chat sessions.")
    with st.container(horizontal=True):
        cancel = st.button("Cancel", key="cancel-clear-chats")
        confirmed = st.button(
            "Delete all chats",
            key="confirm-clear-chats",
            type="primary",
        )

    if cancel:
        st.rerun()
    if confirmed:
        _delete_all_chats()


@st.dialog("Clear incident memory?", dismissible=False)
def _confirm_clear_memory() -> None:
    """Confirm permanent deletion of all saved incident memory for the current user."""
    st.warning("This permanently deletes all of your saved incident memory.")
    with st.container(horizontal=True):
        cancel = st.button("Cancel", key="cancel-clear-memory")
        confirmed = st.button(
            "Delete incident memory",
            key="confirm-clear-memory",
            type="primary",
        )

    if cancel:
        st.rerun()
    if confirmed:
        _delete_all_incidents()


def _delete_all_chats() -> None:
    """Delete every persisted chat and reset the current UI session."""
    st.session_state.chat_store.clear_all(st.session_state.user_id)
    st.session_state.messages = []
    st.session_state.session_id = None
    st.session_state.agent = None
    st.rerun()


def _delete_all_incidents() -> None:
    """Delete every persisted incident and refresh agent memory context."""
    st.session_state.incident_store.clear(st.session_state.user_id)
    refresh_agent_context(st.session_state.user_id)
    st.rerun()
