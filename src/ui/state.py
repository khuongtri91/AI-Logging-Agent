import streamlit as st

from src.agents import LogAnalyzerAgent
from src.utils import Settings, get_settings


def initialize_session_state() -> Settings:
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
