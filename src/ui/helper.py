from collections.abc import Sequence
from typing import Protocol
from uuid import uuid4

import streamlit as st
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents import get_log_analyzer_agent
from src.memory import ChatMessageRecord
from src.tools import get_agent_tools
from src.ui.types import ChatMessage, ChatRole, ProgressStep


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


def load_session_messages(user_id: str, session_id: str) -> list[ChatMessage]:
    """Load persisted messages for an explicitly selected chat session."""
    messages: list[ChatMessageRecord] = st.session_state.chat_store.load(user_id, session_id)
    return [message.model_dump(mode="json") for message in messages]


def persist_chat_messages(
    user_id: str,
    session_id: str,
    messages: Sequence[ChatMessage],
) -> None:
    """Persist messages for an explicitly selected chat session."""
    validated_messages = [
        ChatMessageRecord.model_validate(message)
        for message in messages
    ]
    st.session_state.chat_store.save(user_id, session_id, validated_messages)


def create_chat_session(user_id: str) -> str:
    """Create and select a new empty chat session for a user."""
    session_id = uuid4().hex
    st.session_state.chat_store.create_session(user_id, session_id)
    select_chat_session(user_id, session_id)
    return session_id


def list_chat_sessions(user_id: str) -> list[str]:
    """Return stored chat sessions for a user."""
    return st.session_state.chat_store.list_sessions(user_id)


def get_chat_session_label(user_id: str, session_id: str) -> str:
    """Return a short sidebar label derived from the first user message."""
    for message in load_session_messages(user_id, session_id):
        if message["role"] == "user" and message["content"]:
            return message["content"][:20]
    return "Untitled chat"


def select_chat_session(user_id: str, session_id: str) -> None:
    """Load and make a persisted chat session active in the current UI session."""
    messages = load_session_messages(user_id, session_id)
    st.session_state.user_id = user_id
    st.session_state.session_id = session_id
    st.session_state.messages = messages
    st.session_state.agent = get_log_analyzer_agent(user_id, session_id)
    refresh_agent_context(user_id)


def refresh_agent_context(user_id: str) -> None:
    """Refresh the agent prompt with manually prioritized incident memory."""
    if st.session_state.agent is None:
        return

    incidents = st.session_state.incident_store.get_incidents_for_prompt(user_id)
    incident_context = st.session_state.incident_store.format_for_prompt(incidents)
    st.session_state.agent.set_incident_context(incident_context)
