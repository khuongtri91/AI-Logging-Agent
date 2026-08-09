import streamlit as st

from src.memory import get_chat_store, get_incident_store
from src.utils import Settings, get_settings


def initialize_session_state(user_id: str | None = None) -> Settings:
    """Initialize Streamlit-owned state exactly once per browser session."""
    try:
        if "settings" not in st.session_state:
            st.session_state.settings = get_settings()

        settings = st.session_state.settings
        active_user_id = user_id or settings.default_user_id
        if st.session_state.get("user_id") != active_user_id:
            st.session_state.user_id = active_user_id
            st.session_state.session_id = None
            st.session_state.messages = []
            st.session_state.agent = None

        if "session_id" not in st.session_state:
            st.session_state.session_id = None
        if "chat_store" not in st.session_state:
            st.session_state.chat_store = get_chat_store()
        if "incident_store" not in st.session_state:
            st.session_state.incident_store = get_incident_store()

        if "messages" not in st.session_state:
            st.session_state.messages = []

        if "agent" not in st.session_state:
            st.session_state.agent = None
    except Exception as exc:
        st.error(f"Configuration error: {exc}")
        st.stop()

    return st.session_state.settings
