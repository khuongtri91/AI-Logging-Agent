import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from src.agents import LogAnalyzerAgent
from src.utils import get_settings


def initialize_session_state():
    """Initialize Streamlit-owned state exactly once per browser session."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "agent" not in st.session_state:
        try:
            st.session_state.settings = get_settings()
            st.session_state.agent = LogAnalyzerAgent()
        except Exception as exc:
            st.error(f"Configuration error: {exc}")
            st.stop()

    if "settings" not in st.session_state:
        st.session_state.settings = st.session_state.agent.settings

    return st.session_state.settings


def append_message(role: str, content: str) -> None:
    """Append one Streamlit chat message to session state."""
    st.session_state.messages.append({"role": role, "content": content})


def convert_to_langchain_messages(messages: list[dict]) -> list:
    """Convert Streamlit message dictionaries to LangChain chat messages."""
    langchain_messages = []

    for message in messages:
        role = message.get("role")
        content = message.get("content", "")

        if role == "user":
            langchain_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))

    return langchain_messages
