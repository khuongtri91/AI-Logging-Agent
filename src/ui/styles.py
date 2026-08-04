import streamlit as st


def apply_page_styles() -> None:
    """Apply small layout refinements for the Streamlit shell."""
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 980px;
            padding-top: 2rem;
        }

        [data-testid="stSidebar"] code {
            white-space: pre-wrap;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
