from collections.abc import Sequence
from typing import Literal, NotRequired, Protocol, TypedDict

from langchain_core.messages import BaseMessage

from src.agents.types import ProgressCallback


ChatRole = Literal["user", "assistant"]
ProgressState = Literal["running", "complete", "error"]


class ProgressStep(TypedDict):
    """One persisted progress item shown under an assistant message."""

    label: str
    detail: str


class ChatMessage(TypedDict):
    """One Streamlit chat message stored in session state."""

    role: ChatRole
    content: str
    steps: NotRequired[list[ProgressStep]]


class StreamlitStatus(Protocol):
    """Minimal Streamlit status container interface used by progress rendering."""

    def update(
        self,
        *,
        label: str,
        state: ProgressState,
        expanded: bool | None = None,
    ) -> None:
        """Update the visible status container."""

    def write(self, text: str) -> None:
        """Write progress detail into the status container."""


class AgentProcessor(Protocol):
    """Agent interface required by the Streamlit chat view."""

    def process_query(
        self,
        user_input: str,
        callbacks: ProgressCallback | None = None,
        chat_history: Sequence[BaseMessage] | None = None,
    ) -> str:
        """Process a user query and return the assistant response."""
