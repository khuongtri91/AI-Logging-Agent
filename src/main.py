"""Streamlit entrypoint for the AI Logging Agent."""

import streamlit as st

from src.ui import (
    apply_page_styles,
    initialize_session_state,
    render_chat_interface,
    render_sidebar,
)


st.set_page_config(
    page_title="AI Log Analyzer",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    """Render the Streamlit application."""
    apply_page_styles()
    settings = initialize_session_state()
    render_sidebar(settings)
    render_chat_interface(
        st.session_state.agent,
        st.session_state.user_id,
        st.session_state.session_id,
    )


if __name__ == "__main__":
    main()
