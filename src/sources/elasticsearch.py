import json
from collections.abc import Mapping
from functools import lru_cache

from pydantic import ValidationError

from src.sources.base import LogSource
from src.sources.helper import guess_log_level, parse_timestamp
from src.sources.types import LogEntry, LogFetchRequest, LogFetchResult, LogSourceName
from src.utils import ElasticsearchSettings, get_elasticsearch_settings


class ElasticsearchSource(LogSource):
    """Search the configured Kubernetes Elasticsearch data-stream family."""

    name = LogSourceName.ELASTICSEARCH

    def __init__(self, settings: ElasticsearchSettings | None = None) -> None:
        self._settings = settings

    def is_configured(self) -> bool:
        """Return whether dedicated Elasticsearch credentials are available."""
        try:
            self.settings
        except ValidationError:
            return False
        return True

    @property
    def settings(self) -> ElasticsearchSettings:
        """Return injected settings or cached Elasticsearch settings."""
        return self._settings or get_elasticsearch_settings()

    def _fetch_logs(self, request: LogFetchRequest) -> LogFetchResult:
        client = self._create_client()
        try:
            response = client.search(
                index=self.settings.data_stream,
                size=request.limit,
                sort=[{"@timestamp": {"order": "desc"}}],
                query=self._build_query(request),
                source_includes=[
                    "@timestamp",
                    "message",
                    "level",
                    "severity",
                    "kubernetes.namespace_name",
                    "kubernetes.pod_name",
                    "kubernetes.container_name",
                    "kubernetes.host",
                ],
            )
        finally:
            close = getattr(client, "close", None)
            if close is not None:
                close()

        hits = response.get("hits", {}).get("hits", [])
        entries = [self._to_log_entry(hit) for hit in reversed(hits)]
        return LogFetchResult(source=self.name, configured=True, entries=entries)

    def _create_client(self):
        """Create a basic-authenticated, bounded Elasticsearch client."""
        from elasticsearch import Elasticsearch

        return Elasticsearch(
            self.settings.url,
            basic_auth=(
                self.settings.username,
                self.settings.password.get_secret_value(),
            ),
            request_timeout=self.settings.request_timeout_seconds,
        )

    def _build_query(self, request: LogFetchRequest) -> dict[str, object]:
        """Build a bounded read-only time-range search over the fixed data stream."""
        filters: list[dict[str, object]] = [
            {
                "range": {
                    "@timestamp": {
                        "gte": f"now-{request.minutes}m",
                        "lte": "now",
                    }
                }
            }
        ]
        query_clauses: list[dict[str, object]] = []
        if request.query:
            query_clauses.append({"match": {"message": {"query": request.query}}})
        return {"bool": {"filter": filters, "must": query_clauses}}

    def _to_log_entry(self, hit: Mapping[str, object]) -> LogEntry:
        """Transform an Elasticsearch hit using the observed Fluent Bit schema."""
        source = hit.get("_source", {})
        if not isinstance(source, Mapping):
            source = {}

        kubernetes = source.get("kubernetes", {})
        if not isinstance(kubernetes, Mapping):
            kubernetes = {}
        timestamp, timestamp_inferred = parse_timestamp(str(source.get("@timestamp", "")))
        message = str(source.get("message", ""))
        level = source.get("level") or source.get("severity")

        metadata = {
            "namespace": str(kubernetes.get("namespace_name", "")),
            "container": str(kubernetes.get("container_name", "")),
            "host": str(kubernetes.get("host", "")),
            "document_id": str(hit.get("_id", "")),
        }
        if timestamp_inferred:
            metadata["timestamp_inferred"] = "true"

        return LogEntry(
            timestamp=timestamp,
            source=self.name,
            service=str(kubernetes.get("pod_name") or self.settings.data_stream),
            level=guess_log_level(str(level or message)),
            message=message,
            raw=json.dumps(source, default=str)[:1_000],
            metadata=metadata,
        )


@lru_cache
def get_elasticsearch_source() -> ElasticsearchSource:
    """Return the shared Elasticsearch source adapter."""
    return ElasticsearchSource()
