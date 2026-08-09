import streamlit as st

from src.ui.helper import (
    append_message,
    convert_to_langchain_messages,
    persist_chat_messages,
    refresh_agent_context,
)
from src.ui.progress import StreamlitProgress
from src.ui.types import AgentProcessor, ChatMessage


def render_chat_interface(
    agent: AgentProcessor | None,
    user_id: str,
    session_id: str | None,
) -> None:
    """Render the chat history and process a new user prompt."""
    st.title("AI Log Analyzer")
    st.caption("Ask questions about the log files available to this project.")

    if session_id is None:
        st.info("Create a new chat from the sidebar to begin.")
        return

    if agent is None:
        st.error("Unable to initialize the selected chat session.")
        return

    render_chat_messages(st.session_state.messages)

    prompt = st.chat_input("Ask about your logs")
    if not prompt:
        return

    append_message("user", prompt)
    persist_chat_messages(user_id, session_id, st.session_state.messages)

    with st.chat_message("user"):
        st.markdown(prompt)

    chat_history = convert_to_langchain_messages(st.session_state.messages[:-1])
    refresh_agent_context(user_id)

    with st.chat_message("assistant"):
        status = st.status("Analyzing...", expanded=True)
        progress = StreamlitProgress(status)
        try:
            response = agent.process_query(
                prompt,
                callbacks=progress,
                chat_history=chat_history,
            )
        except Exception as exc:
            progress.on_error(str(exc))
            response = f"Error: {exc}"

        st.markdown(response)
        progress.complete()

    append_message("assistant", response, progress.steps)
    persist_chat_messages(user_id, session_id, st.session_state.messages)


def render_chat_messages(messages: list[ChatMessage]) -> None:
    """Render existing Streamlit chat messages."""
    if not messages:
        st.info("Start by asking what log files are available.")
        return

    for message in messages:
        with st.chat_message(message["role"]):
            steps = message.get("steps", [])
            if steps:
                with st.expander(
                    f"{len(steps)} step{'s' if len(steps) != 1 else ''}",
                    expanded=False,
                ):
                    for step in steps:
                        st.write(f"**{step['label']}** - {step['detail']}")
            st.markdown(message["content"])
