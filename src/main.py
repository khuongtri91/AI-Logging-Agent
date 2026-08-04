"""Streamlit entrypoint for the AI Logging Agent."""

import streamlit as st

from src.ui.chat import render_chat_interface
from src.ui.sidebar import render_sidebar
from src.ui.state import initialize_session_state
from src.ui.styles import apply_page_styles


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
    render_chat_interface(st.session_state.agent)


if __name__ == "__main__":
    main()
