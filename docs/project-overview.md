# Project Overview

The project is an AI-powered log analysis assistant with a Streamlit web interface.

## Current Capabilities

- List available `.log` files from the configured log directory.
- Read a selected log file.
- Search logs case-insensitively for a term.
- Check availability of live Kubernetes and Elasticsearch log sources.
- Fetch recent logs from a Kubernetes pod in an allow-listed namespace.
- Search retained Kubernetes workload logs in the configured Elasticsearch data stream.
- Ask natural-language questions about the logs.
- Preserve conversation context during the current Streamlit browser session.
- Persist chat sessions and incident memory through file-backed memory stores.
- Create, switch between, and clear user-scoped persisted chat sessions from the sidebar.
- Inject manually prioritized incident memory into the system prompt.

## Current Boundaries

The implemented app is still level 1:

- The model chooses between local, Kubernetes, and Elasticsearch read-only tools;
  there is no deterministic source-routing layer yet.
- It does not perform automated remediation.
- Incident memory is limited to all `P1` incidents and four recent `P2` incidents; `P3` and `info` entries are retained but not injected into prompts.

## Configuration

Configuration is defined in `src/utils/config.py` through `Settings`.

Expected environment values include:

- `GEMINI_API_MODEL`
- `GEMINI_API_KEY`
- `TEMPERATURE`
- `LOG_DIRECTORY`
- `DEFAULT_USER_ID`
- `K8S_KUBECONFIG`
- `K8S_CONTEXT`
- `K8S_ALLOWED_NAMESPACES`
- `ELASTICSEARCH_URL`
- `ELASTICSEARCH_USERNAME`
- `ELASTICSEARCH_PASSWORD`
- `ELASTICSEARCH_DATA_STREAM`

The system prompt is loaded from the root-level `system_prompt.txt` file by `Settings.get_system_prompt()`. The configured prompt path must point to a file directly under the project root.

## Logs

Sample logs currently exist in `logs/`:

- `app.log`
- `error.log`
- `system.log`

Runtime memory files are stored under `logs/users/` and ignored by Git.
