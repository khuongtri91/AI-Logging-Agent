from types import SimpleNamespace

from src.sources import LogEntry, LogFetchResult, LogLevel
from src.tools import get_agent_tools, source_tools


def make_entry() -> LogEntry:
    """Create one normalized entry for source-tool formatting tests."""
    return LogEntry(
        timestamp="2026-08-11T08:00:00.000Z",
        source="kubernetes",
        service="checkout-api-abc",
        level=LogLevel.ERROR,
        message="checkout timed out",
        raw="checkout timed out",
        metadata={"namespace": "ecommerce"},
    )


def test_list_log_sources_reports_configuration(monkeypatch):
    kubernetes_source = SimpleNamespace(name="kubernetes", is_configured=lambda: True)
    elasticsearch_source = SimpleNamespace(name="elasticsearch", is_configured=lambda: False)
    monkeypatch.setattr(source_tools, "get_kubernetes_source", lambda: kubernetes_source)
    monkeypatch.setattr(
        source_tools,
        "get_elasticsearch_source",
        lambda: elasticsearch_source,
    )

    result = source_tools.list_log_sources.invoke({})

    assert "kubernetes: configured" in result
    assert "elasticsearch: requires valid configuration" in result


def test_fetch_kubernetes_pod_logs_formats_normalized_result(monkeypatch):
    requests = []
    kubernetes_source = SimpleNamespace(
        fetch=lambda request: requests.append(request)
        or LogFetchResult(
            source="kubernetes",
            configured=True,
            entries=[make_entry()],
        )
    )
    monkeypatch.setattr(source_tools, "get_kubernetes_source", lambda: kubernetes_source)

    result = source_tools.fetch_kubernetes_pod_logs.invoke(
        {
            "pod_name": "checkout-api-abc",
            "namespace": "ecommerce",
            "query": "timeout",
            "minutes": 10,
            "limit": 5,
        }
    )

    assert requests[0].target == "ecommerce/checkout-api-abc"
    assert requests[0].query == "timeout"
    assert "Kubernetes namespace and pod: ecommerce/checkout-api-abc" in result
    assert "namespace=ecommerce" in result


def test_fetch_kubernetes_pod_logs_uses_default_namespace_for_blank_namespace(monkeypatch):
    requests = []
    kubernetes_source = SimpleNamespace(
        fetch=lambda request: requests.append(request)
        or LogFetchResult(source="kubernetes", configured=True)
    )
    monkeypatch.setattr(source_tools, "get_kubernetes_source", lambda: kubernetes_source)

    source_tools.fetch_kubernetes_pod_logs.invoke({"pod_name": "checkout-api-abc"})

    assert requests[0].target == "checkout-api-abc"


def test_fetch_kubernetes_pod_logs_rejects_blank_pod_name():
    result = source_tools.fetch_kubernetes_pod_logs.invoke({"pod_name": "   "})

    assert result == "Invalid Kubernetes log request: pod_name must not be empty"


def test_search_elasticsearch_logs_hides_index_selection(monkeypatch):
    requests = []
    elasticsearch_source = SimpleNamespace(
        fetch=lambda request: requests.append(request)
        or LogFetchResult(
            source="elasticsearch",
            configured=True,
            entries=[make_entry().model_copy(update={"source": "elasticsearch"})],
        )
    )
    monkeypatch.setattr(
        source_tools,
        "get_elasticsearch_source",
        lambda: elasticsearch_source,
    )

    result = source_tools.search_elasticsearch_logs.invoke(
        {"query": "timeout", "minutes": 10, "limit": 5}
    )

    assert requests[0].target is None
    assert requests[0].query == "timeout"
    assert "Elasticsearch Kubernetes logs" in result


def test_source_tools_reject_invalid_request_limits():
    result = source_tools.search_elasticsearch_logs.invoke({"limit": 0})

    assert result.startswith("Invalid log request:")


def test_get_source_tools_returns_all_external_log_tools():
    tool_names = {tool.name for tool in source_tools.get_source_tools()}

    assert tool_names == {
        "list_log_sources",
        "fetch_kubernetes_pod_logs",
        "search_elasticsearch_logs",
    }


def test_get_agent_tools_includes_external_log_source_tools():
    tool_names = {tool.name for tool in get_agent_tools()}

    assert {
        "list_log_sources",
        "fetch_kubernetes_pod_logs",
        "search_elasticsearch_logs",
    }.issubset(tool_names)
