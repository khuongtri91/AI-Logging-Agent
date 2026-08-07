# Architecture

## Main Runtime Flow

The active agent flow is:

1. Caller collects user input.
2. Caller converts prior chat messages to LangChain messages.
3. Caller invokes `LogAnalyzerAgent.process_query(user_input, callbacks=progress, chat_history=history)`.
4. Agent builds a prompt with system instructions, chat history, and user input.
5. Gemini returns either a direct answer or tool calls.
6. If tool calls exist, the assistant tool-call message is appended to the evolving `conversation`.
7. Tool calls are executed by `AgentToolsAction`.
8. Tool results are appended as LangChain `ToolMessage` objects.
9. The updated `conversation` is sent back to the model for another iteration.
10. Final assistant text is returned to the caller once `response.tool_calls` is empty.
11. Caller appends user and assistant messages to its own history.

## Agent Layer

`src/agents/log_analyzer.py`

- Owns model initialization.
- Owns tool binding.
- Owns prompt construction.
- Does not own chat history.
- Accepts external history through `process_query(user_input, chat_history=None)`.
- Accepts an optional progress callback for reasoning/tool execution updates.

`src/agents/tools_call.py`

- Executes model-requested tool calls.
- Builds `tools_map = {tool.name: tool}` once.
- Uses O(1) lookup per tool call.
- Receives and returns the evolving `conversation`.
- Appends both the AI tool-call message and generated `ToolMessage` objects.
- Catches per-tool exceptions and returns them as tool-result content.
- Uses a normalized `tool_call_id` returned by `_execute_tool_call()` when constructing `ToolMessage`.
- Emits optional progress callback events for tool start, tool end, and approval-blocked actions.

## Tool Layer

`src/tools/log_reader.py`

Active tools:

- `list_log_files`
- `read_log_file`
- `search_logs`

Design notes:

- Tools read configuration through `get_settings()`.
- Tool schemas do not expose `settings` to the model.
- Log path resolution protects against path traversal outside the configured log directory.

`src/tools/k8s_tools.py`

- Contains simulated Kubernetes pod restart behavior.
- Imported through `src/tools/__init__.py`.
- `restart_kubernetes_pod` is treated as an action tool.
- Action tools are blocked unless the latest user turn includes explicit approval.

## Model Layer

`src/model/gemini.py`

- Wraps `ChatGoogleGenerativeAI`.
- Exposes `get_llm()`.
- Exposes `get_llm_with_tools(tools)`.

## Utility Layer

`src/utils/config.py`

- Defines `Settings`.
- Loads environment values from `.env`.
- Provides the current system prompt.

`src/utils/response.py`

- Normalizes model responses into plain text.
- Handles string content, structured content blocks, and generic objects.

## Streamlit UI Layer

`src/main.py`

- Streamlit entrypoint.
- Calls UI components.

`streamlit_app.py`

- Root launcher for Streamlit CLI default discovery.
- Delegates to `src.main.main`.

`src/ui/state.py`

- Initializes `st.session_state.messages`.
- Initializes `st.session_state.agent` once per browser session.

`src/ui/helper.py`

- Appends Streamlit chat messages to session state.
- Converts Streamlit messages to LangChain messages.

`src/ui/chat.py`

- Displays existing messages.
- Accepts `st.chat_input`.
- Appends the user message to session state.
- Converts prior messages to LangChain history.
- Creates `StreamlitProgress` for the assistant turn.
- Calls `agent.process_query` with progress callbacks.
- Appends the assistant response and captured progress steps to session state.

`src/ui/progress.py`

- Defines `StreamlitProgress`.
- Updates the active Streamlit status container.
- Captures progress steps for later rendering under assistant messages.

`src/ui/types.py`

- Defines typed message, progress-step, callback, and Streamlit status protocols.

`src/ui/sidebar.py`

- Shows runtime settings.
- Shows available tools.
- Shows example prompts.
- Provides clear-chat behavior.

`src/ui/styles.py`

- Contains small Streamlit layout refinements.
