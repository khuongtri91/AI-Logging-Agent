import streamlit as st

from src.ui import (
    AgentProcessor,
    ChatMessage,
    StreamlitProgress,
    append_message,
    convert_to_langchain_messages,
)


def render_chat_interface(agent: AgentProcessor) -> None:
    """Render the chat history and process a new user prompt."""
    st.title("AI Log Analyzer")
    st.caption("Ask questions about the log files available to this project.")

    render_chat_messages(st.session_state.messages)

    prompt = st.chat_input("Ask about your logs")
    if not prompt:
        return

    append_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    chat_history = convert_to_langchain_messages(st.session_state.messages[:-1])

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
