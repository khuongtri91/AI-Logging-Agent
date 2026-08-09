from collections.abc import Mapping, Sequence
from typing import Protocol

from langchain_core.messages import BaseMessage, ToolMessage

from src.agents.types import ProgressCallback


class ToolLike(Protocol):
    """Minimal LangChain tool interface used by AgentToolsAction."""

    name: str

    def invoke(self, args: Mapping[str, object]) -> object:
        """Run the tool with model-provided arguments."""


class AgentToolsAction:
    """Execute model-requested tools and return LangChain ToolMessages."""

    def __init__(
        self,
        tools: Sequence[ToolLike],
        verbose: bool = True,
        action_tool_names: set[str] | None = None,
    ) -> None:
        self.tools = list(tools)
        self.tools_map: dict[str, ToolLike] = {tool.name: tool for tool in tools}
        self.verbose = verbose
        self.action_tool_names = action_tool_names or set()

    def handle_tool_calls(
        self,
        conversation: list[BaseMessage],
        ai_message,
        callbacks: ProgressCallback | None = None,
        allow_action_tools: bool = False,
    ) -> list[BaseMessage]:
        """
        Append an AI tool-call message and its ToolMessages to the conversation.

        Args:
            conversation: Running conversation messages.
            ai_message: AI message containing tool calls.
            callbacks: Optional progress callback receiver.
            allow_action_tools: Whether action tools may execute this turn.

        Returns:
            The updated running conversation messages.
        """
        conversation.append(ai_message)
        tool_messages: list[ToolMessage] = []

        for tool_call in ai_message.tool_calls:
            tool_name, tool_call_id, result = self._execute_tool_call(
                tool_call,
                callbacks=callbacks,
                allow_action_tools=allow_action_tools,
            )

            if self.verbose:
                print(f"\n[Tool: {tool_name}]")
                print(f"{result}\n")

            tool_messages.append(
                ToolMessage(
                    content=str(result),
                    name=tool_name,
                    tool_call_id=tool_call_id,
                )
            )

        conversation.extend(tool_messages)
        return conversation

    def _execute_tool_call(
        self,
        tool_call: Mapping[str, object],
        callbacks: ProgressCallback | None = None,
        allow_action_tools: bool = False,
    ) -> tuple[str, str, str]:
        """Execute one tool call and return a safe result tuple."""
        tool_name = str(tool_call.get("name") or "unknown_tool")
        tool_call_id = str(tool_call.get("id") or f"{tool_name}_missing_id")
        raw_tool_args = tool_call.get("args", {})
        tool_args = raw_tool_args if isinstance(raw_tool_args, Mapping) else {}

        try:
            tool = self.tools_map.get(tool_name)

            if tool is None:
                result = f"Error: unknown tool '{tool_name}'"
            elif self._requires_approval(tool_name) and not allow_action_tools:
                if callbacks:
                    callbacks.on_approval_skipped(tool_name, tool_args)
                result = (
                    f"Action tool '{tool_name}' was not executed because it requires "
                    "explicit user approval. Ask the user to confirm before trying again."
                )
            else:
                if callbacks:
                    callbacks.on_tool_start(tool_name, tool_args)
                result = tool.invoke(tool_args)
                if callbacks:
                    callbacks.on_tool_end(tool_name, result, success=True)
        except Exception as exc:
            result = f"Error executing tool '{tool_name}': {exc}"
            if callbacks:
                callbacks.on_tool_end(tool_name, result, success=False)

        return tool_name, tool_call_id, str(result)

    def _requires_approval(self, tool_name: str) -> bool:
        """Return whether a tool is an action that needs user approval."""
        return tool_name in self.action_tool_names
