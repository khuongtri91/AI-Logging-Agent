from types import SimpleNamespace

from langchain_core.messages import AIMessage

from src.agents.tools_call import AgentToolsAction


class FakeTool:
    name = "fake_tool"

    def invoke(self, args):
        return f"called with {args['value']}"


class FailingTool:
    name = "failing_tool"

    def invoke(self, args):
        raise RuntimeError("tool broke")


def test_handle_tool_calls_uses_tool_map_lookup():
    action = AgentToolsAction([FakeTool()], verbose=False)

    conversation = action.handle_tool_calls(
        [],
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "fake_tool",
                    "args": {"value": "input"},
                    "id": "call_1",
                }
            ],
        ),
    )

    assert action.tools_map["fake_tool"].name == "fake_tool"
    assert conversation[0].tool_calls[0]["name"] == "fake_tool"
    assert conversation[1].name == "fake_tool"
    assert conversation[1].content == "called with input"
    assert conversation[1].tool_call_id == "call_1"


def test_handle_tool_calls_returns_error_for_unknown_tool():
    action = AgentToolsAction([], verbose=False)

    conversation = action.handle_tool_calls(
        [],
        SimpleNamespace(
            content="",
            tool_calls=[
                {
                    "name": "missing_tool",
                    "args": {},
                    "id": "call_1",
                }
            ],
        ),
    )

    assert "unknown tool" in conversation[1].content


def test_handle_tool_calls_blocks_action_tools_without_approval():
    action = AgentToolsAction(
        [FakeTool()],
        verbose=False,
        action_tool_names={"fake_tool"},
    )

    conversation = action.handle_tool_calls(
        [],
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "fake_tool",
                    "args": {"value": "input"},
                    "id": "call_1",
                }
            ],
        ),
    )

    assert "requires explicit user approval" in conversation[1].content


def test_handle_tool_calls_returns_error_for_tool_exception():
    action = AgentToolsAction([FailingTool()], verbose=False)

    conversation = action.handle_tool_calls(
        [],
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "failing_tool",
                    "args": {},
                    "id": "call_1",
                }
            ],
        ),
    )

    assert "Error executing tool 'failing_tool': tool broke" == conversation[1].content


def test_handle_tool_calls_uses_normalized_tool_call_id():
    action = AgentToolsAction([FakeTool()], verbose=False)

    conversation = action.handle_tool_calls(
        [],
        SimpleNamespace(
            content="",
            tool_calls=[
                {
                    "name": "fake_tool",
                    "args": {"value": "input"},
                }
            ],
        ),
    )

    assert conversation[1].tool_call_id == "fake_tool_missing_id"
