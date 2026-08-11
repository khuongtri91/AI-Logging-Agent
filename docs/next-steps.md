# Next Steps

## Near-Term

- Refine the action approval detector before enabling real Kubernetes remediation.
- Consider whether `SYSTEM_PROMPT_PATH` should remain configurable or always use root-level `system_prompt.txt`.
- Add tests for Streamlit helper functions in `src/ui/state.py` where practical.
- Add a lightweight README for external users once the app flow settles.

## Kubernetes / Action Tools

Current state:

- `src/tools/source_tools.py` provides active, read-only Kubernetes and
  Elasticsearch inspection tools.
- `src/tools/k8s_tools.py` contains a simulated Kubernetes pod restart tool.
- It is wired into the active tool list through `get_agent_tools()`.
- It is treated as an action tool through `ACTION_TOOL_NAMES`.
- User-facing strings have been normalized to ASCII.

Before enabling Kubernetes remediation:

- Keep action tools impossible to execute unless the latest user turn clearly approves.
- Expand tests that prove action tools are blocked without approval across Streamlit flows.

Possible design:

- Keep level-1 log tools in `src/tools/log_reader.py`.
- Keep read-only source tools in `src/tools/source_tools.py`.
- Keep `src/tools/k8s_tools.py` for Kubernetes actions.
- Add metadata to tools, such as `requires_approval = True`.
- In `AgentToolsAction`, block `requires_approval` tools unless an approval flag is passed by the caller.

## Persistence

Streamlit history currently lives in `st.session_state.messages`.
The UI now persists chat sessions and manually saved incidents through the memory package.

Implemented local persistence:

- `ChatStore` stores normalized chat sessions as JSON.
- `IncidentStore` stores per-user incident memory as JSON.
- `UserMemoryStorage` centralizes user/session file paths and creates directories.
- The sidebar can create and switch persisted sessions; Streamlit state only tracks the active selection.

Future persistence options:

- SQLite for simple local durability.
- Postgres or another external database for multi-user deployments.

Current wiring notes:

- Keep `LogAnalyzerAgent` stateless.
- Persist Streamlit message dictionaries after Pydantic validation.
- Convert persisted messages to LangChain messages at the UI/application boundary.

Future persistence options:

- Consider an opt-in model-assisted incident-saving workflow, with an explicit user confirmation before persisting the incident and its severity.
- Add editable session titles derived from the first user message instead of generated session IDs.

## Testing

Current test coverage is above 80%.

Future test areas:

- UI state conversion edge cases.
- Prompt path validation edge cases.
- Approval gating for action tools at the app boundary.
- Multi-iteration tool-call behavior beyond the current focused unit tests.
- Clear-chat and history behavior across multiple Streamlit turns.
