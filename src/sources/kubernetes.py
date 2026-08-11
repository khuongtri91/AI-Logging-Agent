import ast
import json
import re
from functools import lru_cache

from pydantic import ValidationError

from src.sources.base import LogSource
from src.sources.helper import guess_log_level, parse_timestamp
from src.sources.types import LogEntry, LogFetchRequest, LogFetchResult, LogSourceName
from src.utils import KubernetesSettings, get_kubernetes_settings


class KubernetesSource(LogSource):
    """Read recent container logs for an allow-listed Kubernetes pod."""

    name = LogSourceName.KUBERNETES

    def __init__(self, settings: KubernetesSettings | None = None) -> None:
        self._settings = settings

    def is_configured(self) -> bool:
        """Return whether the kubeconfig is available on the runtime host."""
        try:
            return self.settings.kubeconfig.is_file()
        except ValidationError:
            return False

    @property
    def settings(self) -> KubernetesSettings:
        """Return injected settings or the cached Kubernetes settings."""
        return self._settings or get_kubernetes_settings()

    def _fetch_logs(self, request: LogFetchRequest) -> LogFetchResult:
        if request.target is None:
            return LogFetchResult(
                source=self.name,
                configured=True,
                message="Kubernetes log fetch requires a pod target",
            )

        namespace, pod_name = self._resolve_target(request.target)
        if namespace not in self.settings.allowed_namespaces:
            return LogFetchResult(
                source=self.name,
                configured=True,
                message=f"Kubernetes namespace '{namespace}' is not allow-listed",
            )

        api = self._create_api()
        try:
            raw_logs = api.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                since_seconds=request.minutes * 60,
                tail_lines=min(request.limit * 4, 1_000),
                timestamps=True,
                _request_timeout=self.settings.request_timeout_seconds,
            )
        finally:
            api_client = getattr(api, "api_client", None)
            close = getattr(api_client, "close", None)
            if close is not None:
                close()

        log_lines = self._decode_log_response(raw_logs)
        entries = [
            self._to_log_entry(line, pod_name, namespace)
            for line in log_lines.splitlines()
            if not request.query or request.query.lower() in line.lower()
        ]
        return LogFetchResult(
            source=self.name,
            configured=True,
            entries=entries[-request.limit:],
        )

    def _create_api(self):
        """Create a CoreV1 client from the configured local kubeconfig."""
        from kubernetes import client, config

        api_client = config.new_client_from_config(
            config_file=str(self.settings.kubeconfig),
            context=self.settings.context,
        )
        return client.CoreV1Api(api_client)

    def _resolve_target(self, target: str) -> tuple[str, str]:
        """Resolve pod or namespace/pod targets without accepting nested paths."""
        if "/" not in target:
            return self.settings.allowed_namespaces[0], target

        namespace, pod_name = target.split("/", maxsplit=1)
        if not namespace or not pod_name or "/" in pod_name:
            raise ValueError("Kubernetes target must be pod or namespace/pod")
        return namespace, pod_name

    def _decode_log_response(self, raw_logs: str) -> str:
        """Decode serialized Kubernetes client response wrappers when present."""
        if raw_logs.startswith(("b'", 'b"')):
            try:
                decoded_bytes = ast.literal_eval(raw_logs)
            except (SyntaxError, ValueError):
                return raw_logs

            if isinstance(decoded_bytes, bytes):
                return decoded_bytes.decode("utf-8", errors="replace")

        if not raw_logs.startswith('"'):
            return raw_logs

        try:
            decoded_logs = json.loads(raw_logs)
        except json.JSONDecodeError:
            return raw_logs

        return decoded_logs if isinstance(decoded_logs, str) else raw_logs

    def _to_log_entry(self, line: str, pod_name: str, namespace: str) -> LogEntry:
        """Transform one Kubernetes API log line into the normalized record shape."""
        timestamp_prefix = re.compile(r"^(?P<timestamp>\S+)\s+(?P<message>.*)$")
        match = timestamp_prefix.match(line)
        if match:
            timestamp, timestamp_inferred = parse_timestamp(match.group("timestamp"))
            message = match.group("message")
        else:
            timestamp, timestamp_inferred = parse_timestamp("")
            message = line

        metadata = {"namespace": namespace}
        if timestamp_inferred:
            metadata["timestamp_inferred"] = "true"
        return LogEntry(
            timestamp=timestamp,
            source=self.name,
            service=pod_name,
            level=guess_log_level(message),
            message=message,
            raw=line[:1_000],
            metadata=metadata,
        )


@lru_cache
def get_kubernetes_source() -> KubernetesSource:
    """Return the shared Kubernetes source adapter."""
    return KubernetesSource()
