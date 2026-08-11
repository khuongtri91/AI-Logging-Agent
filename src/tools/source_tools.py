from langchain_core.tools import tool
from pydantic import ValidationError

from src.sources import (
    LogFetchRequest,
    LogSource,
    format_entries,
    get_elasticsearch_source,
    get_kubernetes_source,
)


@tool
def list_log_sources() -> str:
    """
    List the read-only log sources available to the agent. Call this first
    when you're unsure which sources are available.
    """
    sources: tuple[LogSource, ...] = (
        get_kubernetes_source(),
        get_elasticsearch_source(),
    )
    rows = []
    for source in sources:
        if source.is_configured():
            rows.append(f"- {source.name}: configured")
        else:
            rows.append(f"- {source.name}: requires valid configuration")

    return "Available log sources:\n" + "\n".join(rows)


@tool
def fetch_kubernetes_pod_logs(
    pod_name: str,
    namespace: str = "",
    query: str = "",
    minutes: int = 15,
    limit: int = 100,
) -> str:
    """Fetch recent logs from a Kubernetes pod.

    Args:
        pod_name: Kubernetes pod name.
        namespace: Optional namespace. A blank value uses the configured default.
        query: Optional case-insensitive text filter.
        minutes: Number of recent minutes to search, from 1 to 1,440.
        limit: Maximum entries to return, from 1 to 200.

    Returns:
        Formatted text block of the newest matching log entries, ordered oldest
        to newest.
    """
    target = _build_kubernetes_target(pod_name, namespace)
    if not target:
        return "Invalid Kubernetes log request: pod_name must not be empty"

    request_or_error = _build_request(
        target=target,
        query=query,
        minutes=minutes,
        limit=limit,
    )
    if isinstance(request_or_error, str):
        return request_or_error

    result = get_kubernetes_source().fetch(request_or_error)
    query_label = query.strip() or "none"
    return format_entries(
        result,
        header=(
            f"Kubernetes namespace and pod: {target} "
            f"(last {minutes}m, query={query_label})"
        ),
    )


@tool
def search_elasticsearch_logs(
    query: str = "",
    minutes: int = 15,
    limit: int = 50,
) -> str:
    """Search recent Kubernetes workload logs in the configured Elasticsearch stream.

    The agent cannot select the Elasticsearch index. Searches are restricted to the
    configured `logs-kubernetes-*` data-stream family.

    Args:
        query: Optional text filter applied to the log message field.
        minutes: Number of recent minutes to search, from 1 to 1,440.
        limit: Maximum entries to return, from 1 to 200.

    Returns:
        Formatted text block of the newest matching log entries, ordered oldest
        to newest.
    """
    request_or_error = _build_request(
        target=None,
        query=query,
        minutes=minutes,
        limit=limit,
    )
    if isinstance(request_or_error, str):
        return request_or_error

    result = get_elasticsearch_source().fetch(request_or_error)
    query_label = query.strip() or "none"
    return format_entries(
        result,
        header=f"Elasticsearch Kubernetes logs (last {minutes}m, query={query_label})",
    )


def _build_kubernetes_target(pod_name: str, namespace: str) -> str:
    """Build a pod target while allowing the source to apply its default namespace."""
    normalized_pod_name = pod_name.strip()
    normalized_namespace = namespace.strip()
    if not normalized_namespace:
        return normalized_pod_name
    return f"{normalized_namespace}/{normalized_pod_name}"


def _build_request(
    target: str | None,
    query: str,
    minutes: int,
    limit: int,
) -> LogFetchRequest | str:
    """Validate model-provided tool inputs before calling a source adapter."""
    try:
        return LogFetchRequest(
            target=target,
            query=query,
            minutes=minutes,
            limit=limit,
        )
    except ValidationError as exc:
        return f"Invalid log request: {exc.errors(include_url=False)}"


def get_source_tools() -> list:
    """Return all read-only external log-source tools."""
    return [
        list_log_sources,
        fetch_kubernetes_pod_logs,
        search_elasticsearch_logs,
    ]
