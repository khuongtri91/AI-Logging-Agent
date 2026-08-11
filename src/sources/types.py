from datetime import datetime, timezone
from enum import StrEnum
from pydantic import BaseModel, Field, field_validator, model_validator


class LogSourceName(StrEnum):
    """Names of supported normalized log sources."""

    KUBERNETES = "kubernetes"
    ELASTICSEARCH = "elasticsearch"


class LogLevel(StrEnum):
    """Normalized levels supported by the agent prompt format."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class LogEntry(BaseModel):
    """A single normalized log line from any configured source."""

    timestamp: datetime
    source: LogSourceName
    service: str
    level: LogLevel = LogLevel.UNKNOWN
    message: str
    raw: str
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Require explicit time-zone information for comparable log ordering."""
        if value.tzinfo is None:
            raise ValueError("Log timestamp must include time-zone information")
        return value

    def short(self) -> str:
        """Return the compact representation used for agent prompt context."""
        timestamp = self.timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        metadata = ", ".join(
            f"{key}={value}" for key, value in sorted(self.metadata.items())
        )
        metadata_suffix = f" [{metadata}]" if metadata else ""
        return (
            f"[{timestamp}] [{self.source}/{self.service}] {self.level}: "
            f"{self.message}{metadata_suffix}"
        )


class LogFetchRequest(BaseModel):
    """Bounded query options shared by all source adapters."""

    target: str | None = None
    query: str | None = None
    minutes: int = Field(default=15, ge=1, le=1_440)
    limit: int = Field(default=100, ge=1, le=200)

    @field_validator("target", "query", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        """Normalize empty target and query values to None."""
        if value is None or not value.strip():
            return None
        return value.strip()


class LogFetchResult(BaseModel):
    """Typed source response that distinguishes logs from source availability."""

    source: LogSourceName
    configured: bool
    entries: list[LogEntry] = Field(default_factory=list)
    message: str = ""

    @model_validator(mode="after")
    def reject_entries_for_unconfigured_source(self) -> "LogFetchResult":
        """Prevent placeholder entries from being interpreted as log evidence."""
        if not self.configured and self.entries:
            raise ValueError("Unconfigured sources must not return log entries")
        return self
