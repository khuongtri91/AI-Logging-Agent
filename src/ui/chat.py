import streamlit as st

from src.ui.state import append_message, convert_to_langchain_messages


def render_chat_interface(agent) -> None:
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
        with st.spinner("Analyzing logs..."):
            response = agent.process_query(prompt, chat_history=chat_history)
            st.markdown(response)

    append_message("assistant", response)


def render_chat_messages(messages: list[dict]) -> None:
    """Render existing Streamlit chat messages."""
    if not messages:
        st.info("Start by asking what log files are available.")
        return

    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
