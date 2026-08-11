import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.sources import (
    ElasticsearchSource,
    KubernetesSource,
    LogEntry,
    LogFetchRequest,
    LogFetchResult,
    LogLevel,
    format_entries,
)
from src.utils import ElasticsearchSettings, KubernetesSettings


def make_kubernetes_settings(tmp_path) -> KubernetesSettings:
    """Create valid Kubernetes settings backed by a temporary kubeconfig file."""
    kubeconfig_path = tmp_path / "config"
    kubeconfig_path.write_text("apiVersion: v1", encoding="utf-8")
    return KubernetesSettings(
        kubeconfig=kubeconfig_path,
        allowed_namespaces="ecommerce,logging",
        request_timeout_seconds=10,
    )


def make_elasticsearch_settings() -> ElasticsearchSettings:
    """Create valid Elasticsearch settings without exposing a real secret."""
    return ElasticsearchSettings(
        url="http://127.0.0.1:9200",
        username="ai-agent",
        password="test-secret",
        data_stream="logs-kubernetes-*",
        request_timeout_seconds=10,
    )


def test_kubernetes_settings_parses_allowed_namespaces(tmp_path):
    settings = make_kubernetes_settings(tmp_path)

    assert settings.context is None
    assert settings.allowed_namespaces == ("ecommerce", "logging")


def test_log_entry_short_includes_sorted_metadata():
    entry = LogEntry(
        timestamp="2026-08-11T08:00:00.000Z",
        source="kubernetes",
        service="checkout-api-abc",
        level=LogLevel.INFO,
        message="checkout is healthy",
        raw="checkout is healthy",
        metadata={"namespace": "ecommerce", "container": "api"},
    )

    assert entry.short().endswith("[container=api, namespace=ecommerce]")


def test_elasticsearch_settings_rejects_unrestricted_data_stream():
    with pytest.raises(ValidationError, match="ELASTICSEARCH_DATA_STREAM"):
        ElasticsearchSettings(
            url="http://127.0.0.1:9200",
            username="ai-agent",
            password="test-secret",
            data_stream="*",
        )


def test_kubernetes_source_returns_unconfigured_result_for_missing_kubeconfig(tmp_path):
    settings = KubernetesSettings(
        kubeconfig=tmp_path / "missing-config",
        allowed_namespaces="ecommerce",
    )

    result = KubernetesSource(settings).fetch(LogFetchRequest(target="api-pod"))

    assert result.configured is False
    assert result.entries == []
    assert result.message == "kubernetes source requires valid configuration"


def test_kubernetes_source_fetches_and_normalizes_pod_logs(monkeypatch, tmp_path):
    calls = []
    api = SimpleNamespace(
        read_namespaced_pod_log=lambda **kwargs: calls.append(kwargs)
        or "2026-08-11T08:00:00.000Z INFO checkout is healthy\n"
        "2026-08-11T08:01:00.000Z ERROR checkout timed out",
        api_client=SimpleNamespace(close=lambda: calls.append("closed")),
    )
    source = KubernetesSource(make_kubernetes_settings(tmp_path))

    monkeypatch.setattr(source, "_create_api", lambda: api)

    result = source.fetch(
        LogFetchRequest(
            target="ecommerce/checkout-api-abc",
            query="checkout",
            minutes=5,
            limit=2,
        )
    )

    assert calls[0]["name"] == "checkout-api-abc"
    assert calls[0]["namespace"] == "ecommerce"
    assert calls[0]["tail_lines"] == 8
    assert calls[-1] == "closed"
    assert [entry.level for entry in result.entries] == [LogLevel.INFO, LogLevel.ERROR]
    assert result.entries[0].metadata["namespace"] == "ecommerce"


def test_kubernetes_source_defaults_bare_pod_target_to_first_allowed_namespace(
    monkeypatch,
    tmp_path,
):
    calls = []
    api = SimpleNamespace(
        read_namespaced_pod_log=lambda **kwargs: calls.append(kwargs)
        or "2026-08-11T08:00:00.000Z INFO checkout is healthy"
    )
    settings = make_kubernetes_settings(tmp_path).model_copy(
        update={"allowed_namespaces": ("default", "ecommerce")}
    )
    source = KubernetesSource(settings)
    monkeypatch.setattr(source, "_create_api", lambda: api)

    source.fetch(LogFetchRequest(target="checkout-api-abc", minutes=5, limit=1))

    assert calls[0]["namespace"] == "default"


def test_kubernetes_source_decodes_serialized_log_response(monkeypatch, tmp_path):
    api = SimpleNamespace(
        read_namespaced_pod_log=lambda **kwargs: json.dumps(
            "2026-08-11T08:00:00.000Z INFO checkout is healthy\n"
            "2026-08-11T08:01:00.000Z WARN checkout is slow"
        )
    )
    source = KubernetesSource(make_kubernetes_settings(tmp_path))
    monkeypatch.setattr(source, "_create_api", lambda: api)

    result = source.fetch(
        LogFetchRequest(target="ecommerce/checkout-api-abc", minutes=5, limit=2)
    )

    assert [entry.level for entry in result.entries] == [LogLevel.INFO, LogLevel.WARN]


def test_kubernetes_source_decodes_bytes_literal_log_response(monkeypatch, tmp_path):
    payload = (
        "2026-08-11T08:00:00.000Z INFO checkout is healthy\n"
        "2026-08-11T08:01:00.000Z WARN checkout is slow"
    )
    api = SimpleNamespace(read_namespaced_pod_log=lambda **kwargs: repr(payload.encode()))
    source = KubernetesSource(make_kubernetes_settings(tmp_path))
    monkeypatch.setattr(source, "_create_api", lambda: api)

    result = source.fetch(
        LogFetchRequest(target="ecommerce/checkout-api-abc", minutes=5, limit=2)
    )

    assert [entry.level for entry in result.entries] == [LogLevel.INFO, LogLevel.WARN]


def test_kubernetes_source_rejects_namespaces_outside_allow_list(monkeypatch, tmp_path):
    source = KubernetesSource(make_kubernetes_settings(tmp_path))
    monkeypatch.setattr(
        source,
        "_create_api",
        lambda: pytest.fail("Kubernetes API should not be called"),
    )

    result = source.fetch(LogFetchRequest(target="kube-system/calico-node"))

    assert result.configured is True
    assert result.entries == []
    assert "not allow-listed" in result.message


def test_elasticsearch_source_uses_fixed_data_stream_and_normalizes_hits(monkeypatch):
    calls = []
    client = SimpleNamespace(
        search=lambda **kwargs: calls.append(kwargs)
        or {
            "hits": {
                "hits": [
                    {
                        "_id": "document-1",
                        "_source": {
                            "@timestamp": "2026-08-11T08:00:00.000Z",
                            "message": "ERROR database connection timed out",
                            "kubernetes": {
                                "namespace_name": "ecommerce",
                                "pod_name": "checkout-api-abc",
                                "container_name": "api",
                                "host": "k8s-master-2",
                            },
                        },
                    }
                ]
            }
        },
        close=lambda: calls.append("closed"),
    )
    source = ElasticsearchSource(make_elasticsearch_settings())
    monkeypatch.setattr(source, "_create_client", lambda: client)

    result = source.fetch(
        LogFetchRequest(target="untrusted-index", query="database", minutes=10, limit=5)
    )

    assert calls[0]["index"] == "logs-kubernetes-*"
    assert calls[0]["query"]["bool"]["must"] == [
        {"match": {"message": {"query": "database"}}}
    ]
    assert calls[-1] == "closed"
    assert result.entries[0].service == "checkout-api-abc"
    assert result.entries[0].level == LogLevel.ERROR
    assert result.entries[0].metadata == {
        "namespace": "ecommerce",
        "container": "api",
        "host": "k8s-master-2",
        "document_id": "document-1",
    }


def test_elasticsearch_source_returns_typed_failure_result(monkeypatch):
    source = ElasticsearchSource(make_elasticsearch_settings())
    monkeypatch.setattr(source, "_create_client", lambda: (_ for _ in ()).throw(RuntimeError("down")))

    result = source.fetch(LogFetchRequest(query="database"))

    assert result.configured is True
    assert result.entries == []
    assert "RuntimeError: down" in result.message


def test_elasticsearch_source_returns_configuration_requirement(monkeypatch):
    source = ElasticsearchSource(make_elasticsearch_settings())
    monkeypatch.setattr(source, "is_configured", lambda: False)

    result = source.fetch(LogFetchRequest(query="database"))

    assert result.configured is False
    assert result.message == "elasticsearch source requires valid configuration"


def test_format_entries_includes_result_message_and_level_summary():
    result = LogFetchResult(
        source="elasticsearch",
        configured=False,
        message="Elasticsearch source requires configuration",
    )

    assert "Elasticsearch source requires configuration" in format_entries(
        result,
        header="Elasticsearch",
    )
