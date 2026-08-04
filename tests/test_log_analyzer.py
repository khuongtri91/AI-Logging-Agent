from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from src.agents import log_analyzer


class FakeSettings:
    verbose = False
    max_iterations = 5

    def get_system_prompt(self):
        return "You analyze logs."


class FakeTool:
    name = "fake_tool"

    def invoke(self, args):
        return f"tool result for {args['filename']}"


class FakeLlmWithTools:
    def __init__(self, responses):
        self.responses = list(responses)
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        if self.responses:
            return self.responses.pop(0)
        return AIMessage(content="final answer")


class FakeGeminiModel:
    tool_responses = [AIMessage(content="direct answer")]

    def __init__(self, settings):
        self.llm = object()
        self.llm_with_tools = None

    def get_llm(self):
        return self.llm

    def get_llm_with_tools(self, tools):
        self.llm_with_tools = FakeLlmWithTools(self.tool_responses)
        return self.llm_with_tools


def build_agent(monkeypatch, tool_responses):
    FakeGeminiModel.tool_responses = tool_responses
    monkeypatch.setattr(log_analyzer, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(log_analyzer, "GeminiModel", FakeGeminiModel)
    monkeypatch.setattr(log_analyzer, "get_agent_tools", lambda: [FakeTool()])
    monkeypatch.setattr(log_analyzer, "ACTION_TOOL_NAMES", set())
    return log_analyzer.LogAnalyzerAgent()


def test_process_query_uses_supplied_chat_history(monkeypatch):
    agent = build_agent(monkeypatch, [AIMessage(content="direct answer")])
    chat_history = [HumanMessage(content="Earlier question")]

    result = agent.process_query("What happened?", chat_history=chat_history)

    assert result == "direct answer"
    assert agent.llm_with_tools.last_messages[1].content == "Earlier question"


def test_process_query_executes_tool_calls_before_final_answer(monkeypatch):
    tool_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "fake_tool",
                "args": {"filename": "app.log"},
                "id": "call_1",
            }
        ],
    )
    agent = build_agent(monkeypatch, [tool_response, AIMessage(content="final answer")])

    result = agent.process_query("Read app.log")

    assert result == "final answer"
    assert agent.llm_with_tools.last_messages[-1].content == "tool result for app.log"


def test_process_query_returns_error_message_on_exception(monkeypatch):
    agent = build_agent(monkeypatch, [AIMessage(content="direct answer")])

    def raise_error(inputs):
        raise RuntimeError("boom")

    monkeypatch.setattr(agent, "_run_agent_step", raise_error)

    result = agent.process_query("break")

    assert result == "Error processing query: boom"
    assert isinstance(agent.tools_map, dict)
