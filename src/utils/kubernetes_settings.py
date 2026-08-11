from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class KubernetesSettings(BaseSettings):
    """Configuration for read-only Kubernetes workload-log access."""

    kubeconfig: Path
    context: str | None = None
    allowed_namespaces: tuple[str, ...]
    request_timeout_seconds: int = Field(default=10, ge=1, le=60)

    @field_validator("context", mode="before")
    @classmethod
    def normalize_context(cls, value: str | None) -> str | None:
        """Treat an empty context as the kubeconfig current context."""
        if value is None or not value.strip():
            return None
        return value.strip()

    @field_validator("allowed_namespaces", mode="before")
    @classmethod
    def parse_allowed_namespaces(cls, value: str | tuple[str, ...]) -> tuple[str, ...]:
        """Parse a comma-separated namespace allow-list."""
        if isinstance(value, str):
            namespaces = tuple(item.strip() for item in value.split(",") if item.strip())
        else:
            namespaces = tuple(item.strip() for item in value if item.strip())

        if not namespaces:
            raise ValueError("K8S_ALLOWED_NAMESPACES must include at least one namespace")
        return namespaces

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        env_prefix="K8S_",
        enable_decoding=False,
        extra="ignore",
    )


@lru_cache
def get_kubernetes_settings() -> KubernetesSettings:
    """Return cached Kubernetes source settings."""
    return KubernetesSettings()
