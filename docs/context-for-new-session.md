# Context For A New Codex Session

We are building an AI Logging Agent. The current implemented scope is level 1:

- Read and analyze local log files.
- Answer natural-language questions about logs.
- Maintain chat history in the caller, not inside the agent.

Current level-1 limitations:

- No routing decisions.
- No automated actions.
- No multi-source integration.
- Kubernetes restart remediation is wired as a simulated action tool and is blocked unless the latest user turn explicitly approves action execution.

Important architectural decisions:

- The agent follows an iterative ReAct-style loop: prompt the model, execute requested tools, append AI/tool messages to the evolving `conversation`, and continue until the model returns a final answer or `max_iterations` is reached.
- Tool lookup uses `tools_map` for O(1) lookup instead of scanning the tools list for every tool call.
- Tool execution errors are returned as `ToolMessage` content so one failed tool call does not crash the whole agent loop.
- `ToolMessage.tool_call_id` uses the normalized ID returned by `_execute_tool_call()`.
- `LogAnalyzerAgent` is stateless with respect to chat history. `process_query(user_input, callbacks=None, chat_history=None)` accepts LangChain messages and optional progress callbacks from the caller.
- Streamlit owns chat history in `st.session_state.messages`.
- Streamlit progress steps are captured through `StreamlitProgress` and persisted on assistant messages.
- Persistent chat storage has intentionally not been implemented yet.

Current UI:

- Streamlit entrypoint: `src/main.py`
- Root launcher: `streamlit_app.py`
- UI components: `src/ui/state.py`, `src/ui/helper.py`, `src/ui/chat.py`, `src/ui/progress.py`, `src/ui/types.py`, `src/ui/sidebar.py`, `src/ui/styles.py`
- Run with `streamlit run` from the project root, or `.venv\Scripts\python.exe -m streamlit run streamlit_app.py`

Current test status:

- The test suite uses explicit test files in `Makefile`.
- Coverage gate is `--cov-fail-under=80`.
- Last verified result: 37 tests passed, 89.03% coverage.

Potential next work:

- Add stronger tests around multi-iteration tool calls and Kubernetes approval behavior.
- Decide how strict the action approval detector should become before real Kubernetes integration.
- If real Kubernetes execution is added, replace the simulated restart with kubeconfig/context checks.
