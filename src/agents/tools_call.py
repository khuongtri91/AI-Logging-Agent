from langchain_core.messages import ToolMessage


class AgentToolsAction:
    """Execute model-requested tools and return LangChain ToolMessages."""

    def __init__(
        self,
        tools: list,
        verbose: bool = True,
        action_tool_names: set[str] | None = None,
    ):
        self.tools = tools
        self.tools_map = {tool.name: tool for tool in tools}
        self.verbose = verbose
        self.action_tool_names = action_tool_names or set()

    def handle_tool_calls(
        self,
        conversation: list,
        ai_message,
        allow_action_tools: bool = False,
    ) -> list:
        """
        Append an AI tool-call message and its ToolMessages to the conversation.

        Args:
            conversation: Running conversation messages.
            ai_message: AI message containing tool calls.
            allow_action_tools: Whether action tools may execute this turn.

        Returns:
            The updated running conversation messages.
        """
        conversation.append(ai_message)
        tool_messages = []

        for tool_call in ai_message.tool_calls:
            tool_name, tool_call_id, result = self._execute_tool_call(
                tool_call,
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
        tool_call: dict,
        allow_action_tools: bool = False,
    ) -> tuple[str, str, str]:
        """Execute one tool call and return a safe result tuple."""
        tool_name = tool_call.get("name", "unknown_tool")
        tool_call_id = tool_call.get("id", f"{tool_name}_missing_id")

        try:
            tool = self.tools_map.get(tool_name)

            if tool is None:
                result = f"Error: unknown tool '{tool_name}'"
            elif self._requires_approval(tool_name) and not allow_action_tools:
                result = (
                    f"Action tool '{tool_name}' was not executed because it requires "
                    "explicit user approval. Ask the user to confirm before trying again."
                )
            else:
                result = tool.invoke(tool_call.get("args", {}))
        except Exception as exc:
            result = f"Error executing tool '{tool_name}': {exc}"

        return tool_name, tool_call_id, str(result)

    def _requires_approval(self, tool_name: str) -> bool:
        """Return whether a tool is an action that needs user approval."""
        return tool_name in self.action_tool_names
