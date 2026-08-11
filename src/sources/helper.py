from collections import Counter
from datetime import datetime, timezone
import re

from src.sources.types import LogFetchResult, LogLevel


def guess_log_level(message: str) -> LogLevel:
    """Infer a normalized log level from common textual level tokens."""
    level_pattern = re.compile(
        r"\b(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL)\b",
        re.IGNORECASE,
    )
    match = level_pattern.search(message)
    if not match:
        return LogLevel.UNKNOWN

    value = match.group(1).upper()
    if value == "WARNING":
        return LogLevel.WARN
    if value in {"FATAL", "CRITICAL"}:
        return LogLevel.ERROR
    return LogLevel(value)


def parse_timestamp(value: str) -> tuple[datetime, bool]:
    """Parse an ISO timestamp and report whether the fallback current time was used."""
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc), True

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc), True
    return timestamp, False


def format_entries(result: LogFetchResult, header: str = "") -> str:
    """Format a source result for bounded injection into the agent prompt."""
    lines: list[str] = []
    if header:
        lines.extend([header, ""])

    if result.message:
        lines.append(result.message)

    if not result.entries:
        lines.append("(no matching log entries)")
        return "\n".join(lines)

    counts = Counter(entry.level.value for entry in result.entries)
    summary = ", ".join(f"{level}={count}" for level, count in sorted(counts.items()))
    lines.extend([f"{len(result.entries)} entries ({summary})", ""])
    lines.extend(entry.short() for entry in result.entries)
    return "\n".join(lines)
