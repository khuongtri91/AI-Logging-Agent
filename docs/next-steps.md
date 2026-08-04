# Next Steps

## Near-Term

- Refine the action approval detector before connecting to real Kubernetes APIs.
- Consider whether `SYSTEM_PROMPT_PATH` should remain configurable or always use root-level `system_prompt.txt`.
- Add tests for Streamlit helper functions in `src/ui/state.py` where practical.
- Add a lightweight README for external users once the app flow settles.

## Kubernetes / Action Tools

Current state:

- `src/tools/k8s_tools.py` contains a simulated Kubernetes pod restart tool.
- It is wired into the active tool list through `get_agent_tools()`.
- It is treated as an action tool through `ACTION_TOOL_NAMES`.
- User-facing strings have been normalized to ASCII.

Before enabling Kubernetes tools:

- Separate read-only tools from action tools.
- Keep action tools impossible to execute unless the latest user turn clearly approves.
- Expand tests that prove action tools are blocked without approval across Streamlit flows.
- Add configuration checks for kubeconfig/context.

Possible design:

- Keep level-1 log tools in `src/tools/log_reader.py`.
- Add `src/tools/k8s_tools.py` for Kubernetes actions.
- Add metadata to tools, such as `requires_approval = True`.
- In `AgentToolsAction`, block `requires_approval` tools unless an approval flag is passed by the caller.

## Persistence

Streamlit history currently lives only in `st.session_state.messages`.

Future persistence options:

- Local JSON file for development.
- SQLite for simple local durability.
- Postgres or another external database for multi-user deployments.

When persistence is added:

- Keep `LogAnalyzerAgent` stateless.
- Persist Streamlit message dictionaries or a normalized message table.
- Convert persisted messages to LangChain messages at the UI/application boundary.

## Testing

Current test coverage is above 80%.

Future test areas:

- UI state conversion edge cases.
- Prompt path validation edge cases.
- Approval gating for action tools at the app boundary.
- Multi-iteration tool-call behavior beyond the current focused unit tests.
- Clear-chat and history behavior across multiple Streamlit turns.
