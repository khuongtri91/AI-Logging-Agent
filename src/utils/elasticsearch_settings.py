from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ElasticsearchSettings(BaseSettings):
    """Configuration for read-only Kubernetes log searches in Elasticsearch."""

    url: str
    username: str
    password: SecretStr
    data_stream: str
    request_timeout_seconds: int = Field(default=10, ge=1, le=60)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        """Require an explicit HTTP(S) Elasticsearch endpoint."""
        parsed_url = urlparse(value)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("ELASTICSEARCH_URL must be an absolute HTTP(S) URL")
        return value.rstrip("/")

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        """Require a non-empty dedicated source username."""
        if not value.strip():
            raise ValueError("ELASTICSEARCH_USERNAME must not be empty")
        return value.strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        """Require a non-empty source password without exposing it in repr output."""
        if not value.get_secret_value():
            raise ValueError("ELASTICSEARCH_PASSWORD must not be empty")
        return value

    @field_validator("data_stream")
    @classmethod
    def validate_data_stream(cls, value: str) -> str:
        """Restrict searches to the approved Kubernetes data-stream family."""
        if value != "logs-kubernetes-*":
            raise ValueError("ELASTICSEARCH_DATA_STREAM must be logs-kubernetes-*")
        return value

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        env_prefix="ELASTICSEARCH_",
        extra="ignore",
    )


@lru_cache
def get_elasticsearch_settings() -> ElasticsearchSettings:
    """Return cached Elasticsearch source settings."""
    return ElasticsearchSettings()
