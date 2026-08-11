from collections.abc import Sequence
from functools import lru_cache
from typing import TypedDict

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.agents.tools_call import AgentToolsAction
from src.agents.types import ProgressCallback
from src.model import GeminiModel
from src.tools import ACTION_TOOL_NAMES, get_agent_tools
from src.utils import extract_response_text, get_settings


class AgentStepInput(TypedDict):
    """Inputs needed to run one agent step."""

    input: str
    chat_history: Sequence[BaseMessage]


class LogAnalyzerAgent:
    """
    AI Logging Agent

    Capabilities:
    - Read and analyze log files
    - Inspect live Kubernetes pod logs
    - Search retained Kubernetes logs in Elasticsearch
    - Answer questions about logs
    - Maintain conversation history

    Limitations:
    - No routing decisions
    - No automated actions
    - No automatic source routing beyond model tool selection
    """

    def __init__(self, incident_context: str = ""):
        self.settings = get_settings()
        self.incident_context = incident_context

        self.model = GeminiModel(self.settings)
        self.llm = self.model.get_llm()

        self.tools = get_agent_tools()
        self.tools_action = AgentToolsAction(
            self.tools,
            verbose=self.settings.verbose,
            action_tool_names=ACTION_TOOL_NAMES,
        )
        self.tools_map = self.tools_action.tools_map
        self.llm_with_tools = self.model.get_llm_with_tools(self.tools)

        self.prompt = self._build_prompt()

    def set_incident_context(self, incident_context: str) -> None:
        """Refresh the system prompt with the latest incident memory."""
        self.incident_context = incident_context
        self.prompt = self._build_prompt()

    def _build_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", self.settings.get_system_prompt(self.incident_context)),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
        ])

    def _run_agent_step(
        self,
        inputs: AgentStepInput,
        callbacks: ProgressCallback | None = None,
    ) -> AIMessage:
        """Run one ReAct-style model step, execute requested tools, then finalize."""
        conversation = self.prompt.invoke(inputs).to_messages()
        allow_action_tools = self._has_action_approval(inputs["input"])
        response = self.llm_with_tools.invoke(conversation)

        for _ in range(self.settings.max_iterations):
            if callbacks:
                last_response = extract_response_text(response)
                callbacks.on_reasoning(last_response)

            if not response.tool_calls:
                return response

            conversation = self.tools_action.handle_tool_calls(
                conversation,
                response,
                callbacks=callbacks,
                allow_action_tools=allow_action_tools,
            )

            if callbacks:
                callbacks.on_thinking()

            response = self.llm_with_tools.invoke(conversation)

        return AIMessage(
            content=(
                "I reached the maximum number of tool iterations before producing "
                "a final answer. Please narrow the request and try again."
            )
        )

    def _has_action_approval(self, user_input: str) -> bool:
        """Detect explicit approval for action tools in the latest user turn."""
        approval_terms = (
            "yes",
            "approve",
            "approved",
            "confirm",
            "confirmed",
            "proceed",
            "do it",
            "go ahead",
            "restart it",
            "restart the pod",
        )
        normalized_input = user_input.lower()
        return any(term in normalized_input for term in approval_terms)

    def process_query(
        self,
        user_input: str,
        callbacks: ProgressCallback | None = None,
        chat_history: Sequence[BaseMessage] | None = None,
    ) -> str:
        """Process a user query and return the response."""
        try:
            response = self._run_agent_step(
                {
                    "input": user_input,
                    "chat_history": chat_history or [],
                },
                callbacks=callbacks,
            )
            return extract_response_text(response)
        except Exception as exc:
            return f"Error processing query: {exc}"


@lru_cache(maxsize=128)
def get_log_analyzer_agent(user_id: str, session_id: str) -> LogAnalyzerAgent:
    """Return the cached agent resource for one user chat session."""
    return LogAnalyzerAgent()
