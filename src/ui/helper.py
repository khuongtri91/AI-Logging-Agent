from collections.abc import Sequence
from typing import Protocol

import streamlit as st
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.tools import get_agent_tools
from src.ui import ChatMessage, ChatRole, ProgressStep


class NamedTool(Protocol):
    """Minimal tool shape needed for UI label generation."""

    name: str


def append_message(
    role: ChatRole,
    content: str,
    steps: Sequence[ProgressStep] | None = None,
) -> None:
    """Append one Streamlit chat message to session state."""
    message: ChatMessage = {
        "role": role,
        "content": content,
        "steps": list(steps or []),
    }
    st.session_state.messages.append(message)


def convert_to_langchain_messages(messages: Sequence[ChatMessage]) -> list[BaseMessage]:
    """Convert Streamlit message dictionaries to LangChain chat messages."""
    langchain_messages: list[BaseMessage] = []

    for message in messages:
        role = message.get("role")
        content = message.get("content", "")

        if role == "user":
            langchain_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))

    return langchain_messages


def format_tool_label(tool_name: str) -> str:
    """Convert a snake_case tool name to a readable label."""
    label = tool_name.strip().replace("_", " ")
    if not label:
        return "Unknown tool"

    return f"{label[0].upper()}{label[1:]}"


def build_tool_labels(tools: Sequence[NamedTool] | None = None) -> dict[str, str]:
    """Build labels for every registered agent tool."""
    selected_tools = list(tools) if tools is not None else get_agent_tools()
    return {tool.name: format_tool_label(tool.name) for tool in selected_tools}
