# Project Overview

The project is an AI-powered log analysis assistant with a Streamlit web interface.

## Current Capabilities

- List available `.log` files from the configured log directory.
- Read a selected log file.
- Search logs case-insensitively for a term.
- Ask natural-language questions about the logs.
- Preserve conversation context during the current Streamlit browser session.

## Current Boundaries

The implemented app is still level 1:

- It only uses local log files.
- It does not route between multiple data sources.
- It does not perform automated remediation.
- It does not persist chat history outside the current process/browser session.

## Configuration

Configuration is defined in `src/utils/config.py` through `Settings`.

Expected environment values include:

- `GEMINI_API_MODEL`
- `GEMINI_API_KEY`
- `TEMPERATURE`
- `LOG_DIRECTORY`

The system prompt is loaded from the root-level `system_prompt.txt` file by `Settings.get_system_prompt()`. The configured prompt path must point to a file directly under the project root.

## Logs

Sample logs currently exist in `logs/`:

- `app.log`
- `error.log`
- `system.log`
