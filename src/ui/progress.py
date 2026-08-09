from collections.abc import Mapping

from src.ui.helper import build_tool_labels, format_tool_label
from src.ui.types import ProgressStep, StreamlitStatus


class StreamlitProgress:
    """Capture and display agent progress inside a Streamlit status container."""

    def __init__(
        self,
        container: StreamlitStatus,
        tool_labels: Mapping[str, str] | None = None,
    ):
        self.status = container
        self.tool_labels = dict(tool_labels or build_tool_labels())
        self.tool_count = 0
        self._has_error = False
        self.steps: list[ProgressStep] = []

    def on_thinking(self) -> None:
        """Show that the agent is preparing the next model step."""
        self.status.update(label="Thinking...", state="running")

    def on_reasoning(self, text: str) -> None:
        """Record model reasoning or other plain-text progress details."""
        if not text:
            return

        self.status.write(f"{text}...")
        self.steps.append({"label": "Reasoning", "detail": text})

    def on_tool_start(self, tool_name: str, tool_args: Mapping[str, object]) -> None:
        """Show that a tool call has started."""
        self.tool_count += 1
        label = self._get_tool_label(tool_name)
        self.status.update(label=f"{label}...", state="running")

    def on_tool_end(self, tool_name: str, result: object, success: bool = True) -> None:
        """Record a completed tool call and a compact result preview."""
        label = self._get_tool_label(tool_name)
        marker = "OK" if success else "FAIL"
        preview = summarize_result(tool_name, result)
        detail = f"[{marker}] {preview}"

        self.status.write(f"[{marker}] **{label}** - {preview}")
        self.steps.append({"label": label, "detail": detail})

    def on_approval_skipped(self, tool_name: str, tool_args: Mapping[str, object]) -> None:
        """Record that an action tool was blocked because approval is missing."""
        label = self._get_tool_label(tool_name)
        detail = "[BLOCKED] requires approval"

        self.status.write(f"[BLOCKED] **{label}** - requires your approval")
        self.steps.append({"label": label, "detail": detail})

    def on_error(self, error: str) -> None:
        """Record an unexpected progress-layer error."""
        self._has_error = True
        self.status.update(label="Error", state="error")
        self.steps.append({"label": "Error", "detail": error})

    def complete(self) -> None:
        """Mark the Streamlit status container complete."""
        if self._has_error:
            return

        if self.tool_count:
            suffix = "" if self.tool_count == 1 else "s"
            self.status.update(
                label=f"Done - {self.tool_count} tool{suffix} used",
                state="complete",
                expanded=False,
            )
            return

        self.status.update(label="Done", state="complete", expanded=False)

    def _get_tool_label(self, tool_name: str) -> str:
        """Return a readable label for a registered or model-provided tool name."""
        return self.tool_labels.get(tool_name, format_tool_label(tool_name))


def summarize_result(tool_name: str, result: object) -> str:
    """Create a compact, user-facing summary for one tool result."""
    normalized_result = _normalize_preview(result)

    if tool_name == "list_log_files":
        count = normalized_result.count(".log")
        suffix = "" if count == 1 else "s"
        return f"found {count} log file{suffix}"

    if tool_name == "read_log_file":
        return "log file read"

    if tool_name == "search_logs":
        first_line = normalized_result.split("\n", 1)[0]
        if first_line.lower().startswith("found"):
            return first_line.lower()
        return "search complete"

    if tool_name == "restart_kubernetes_pod":
        return "action initiated"

    return normalized_result[:80]


def _normalize_preview(result: object) -> str:
    """Convert arbitrary tool output to a compact preview string."""
    return str(result).strip()
