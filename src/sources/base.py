from abc import ABC, abstractmethod

from src.sources.types import LogFetchRequest, LogFetchResult, LogSourceName


class LogSource(ABC):
    """Abstract read-only adapter for a normalized log source."""

    name: LogSourceName

    @abstractmethod
    def is_configured(self) -> bool:
        """Return whether the source has valid local configuration."""

    def fetch(self, request: LogFetchRequest) -> LogFetchResult:
        """Fetch logs or return a typed unavailable result without raising to callers."""
        if not self.is_configured():
            return LogFetchResult(
                source=self.name,
                configured=False,
                message=self._configuration_message(),
            )

        try:
            return self._fetch_logs(request)
        except Exception as exc:
            return LogFetchResult(
                source=self.name,
                configured=True,
                message=f"{self.name} fetch failed: {type(exc).__name__}: {exc}",
            )

    @abstractmethod
    def _fetch_logs(self, request: LogFetchRequest) -> LogFetchResult:
        """Fetch logs after the concrete source has been configured."""

    def _configuration_message(self) -> str:
        """Describe the configuration required before this source can fetch logs."""
        return f"{self.name} source requires valid configuration"
