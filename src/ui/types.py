from collections.abc import Mapping, Sequence
from typing import Literal, NotRequired, Protocol, TypedDict

from langchain_core.messages import BaseMessage


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


class ProgressCallback(Protocol):
    """Agent progress callback interface."""

    steps: list[ProgressStep]

    def on_thinking(self) -> None:
        """Show that the agent is preparing the next model step."""

    def on_reasoning(self, text: str) -> None:
        """Record model reasoning or other plain-text progress details."""

    def on_tool_start(self, tool_name: str, tool_args: Mapping[str, object]) -> None:
        """Show that a tool call has started."""

    def on_tool_end(self, tool_name: str, result: object, success: bool = True) -> None:
        """Record a completed tool call."""

    def on_approval_skipped(self, tool_name: str, tool_args: Mapping[str, object]) -> None:
        """Record that an action tool was blocked because approval is missing."""

    def on_error(self, error: str) -> None:
        """Record an unexpected progress-layer error."""

    def complete(self) -> None:
        """Mark progress complete."""


class AgentProcessor(Protocol):
    """Agent interface required by the Streamlit chat view."""

    def process_query(
        self,
        user_input: str,
        callbacks: ProgressCallback | None = None,
        chat_history: Sequence[BaseMessage] | None = None,
    ) -> str:
        """Process a user query and return the assistant response."""
