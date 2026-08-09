from collections.abc import Mapping
from typing import Protocol


class ProgressCallback(Protocol):
    """Agent progress callback interface."""

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
