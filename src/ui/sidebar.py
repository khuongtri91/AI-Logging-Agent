import streamlit as st


EXAMPLE_PROMPTS = [
    "What log files are available?",
    "Read the app.log file",
    "What errors are in error.log?",
    "Search for database in app.log",
]


def render_sidebar(settings) -> None:
    """Render sidebar controls and project context."""
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
        st.markdown("- `list_log_files`\n- `read_log_file`\n- `search_logs`")

        st.divider()
        st.subheader("Examples")
        for prompt in EXAMPLE_PROMPTS:
            st.code(prompt, language=None)

        st.divider()
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
