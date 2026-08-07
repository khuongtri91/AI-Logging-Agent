"""Streamlit UI components for the AI Logging Agent."""

from src.ui.types import (
    AgentProcessor,
    ChatMessage,
    ChatRole,
    ProgressCallback,
    ProgressState,
    ProgressStep,
    StreamlitStatus,
)

__all__ = [
    "AgentProcessor",
    "ChatMessage",
    "ChatRole",
    "ProgressCallback",
    "ProgressState",
    "ProgressStep",
    "StreamlitStatus",
    "StreamlitProgress",
    "append_message",
    "apply_page_styles",
    "build_tool_labels",
    "convert_to_langchain_messages",
    "format_tool_label",
    "initialize_session_state",
    "render_chat_interface",
    "render_chat_messages",
    "render_sidebar",
    "summarize_result",
]


def __getattr__(name: str) -> object:
    if name in {
        "append_message",
        "build_tool_labels",
        "convert_to_langchain_messages",
        "format_tool_label",
    }:
        from src.ui.helper import (
            append_message,
            build_tool_labels,
            convert_to_langchain_messages,
            format_tool_label,
        )

        return {
            "append_message": append_message,
            "build_tool_labels": build_tool_labels,
            "convert_to_langchain_messages": convert_to_langchain_messages,
            "format_tool_label": format_tool_label,
        }[name]

    if name in {"StreamlitProgress", "summarize_result"}:
        from src.ui.progress import StreamlitProgress, summarize_result

        return {
            "StreamlitProgress": StreamlitProgress,
            "summarize_result": summarize_result,
        }[name]

    if name in {"render_chat_interface", "render_chat_messages"}:
        from src.ui.chat import render_chat_interface, render_chat_messages

        return {
            "render_chat_interface": render_chat_interface,
            "render_chat_messages": render_chat_messages,
        }[name]

    if name == "render_sidebar":
        from src.ui.sidebar import render_sidebar

        return render_sidebar

    if name == "initialize_session_state":
        from src.ui.state import initialize_session_state

        return initialize_session_state

    if name == "apply_page_styles":
        from src.ui.styles import apply_page_styles

        return apply_page_styles

    raise AttributeError(f"module 'src.ui' has no attribute {name!r}")
