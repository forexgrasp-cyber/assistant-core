"""Shared configuration integration for the Retention Analytics Platform.

Centralizes environment-driven settings so every service, worker, and frontend
reads from a single source of truth instead of duplicating config logic (no
siloed configuration).

Secrets are never stored here. Credential *names* are declared so the
canonical secret manager (``shared.production.secrets``) knows what to
resolve, and ``jwt_secret`` is populated from the secret manager rather than
hardcoded (PRODUCTION_STANDARDS.md L6).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Environment variable names for the secrets the platform requires.
# Values are resolved through the canonical secret manager (env -> .env ->
# keyring -> vault), never hardcoded.
REQUIRED_SECRET_KEYS: tuple[str, ...] = ("JWT_SECRET",)


class PlatformSettings(BaseSettings):
    """Platform-wide configuration loaded once and shared across services."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Environment
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    data_dir: str = Field(default="data")

    # Service ports (non-standard, centralized)
    api_port: int = Field(default=47319)
    mcp_port: int = Field(default=47322)
    web_customer_port: int = Field(default=47320)
    web_dev_port: int = Field(default=47321)
    postgres_port: int = Field(default=47323)
    redis_port: int = Field(default=47324)
    clickhouse_port_http: int = Field(default=47325)

    @property
    def api_base_url(self) -> str:
        return f"http://127.0.0.1:{self.api_port}"

    # Database
    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:47323/retention_analytics")
    clickhouse_host: str = Field(default="localhost")
    clickhouse_port: int = Field(default=47325)

    # Cache / queue
    redis_url: str = Field(default="redis://localhost:47324/0")
    celery_broker_url: str = Field(default="redis://localhost:47324/1")
    celery_result_backend: str = Field(default="redis://localhost:47324/2")

    # Auth / tenancy
    workos_api_key: str | None = Field(default=None)
    workos_client_id: str | None = Field(default=None)
    jwt_secret: str | None = Field(default=None)
    jwt_algorithm: str = Field(default="HS256")
    webhook_secret: str | None = Field(default=None)

    # Billing
    stripe_secret_key: str | None = Field(default=None)
    stripe_webhook_secret: str | None = Field(default=None)
    payment_provider: str = Field(default="stripe")

    # AI / LLM
    openai_api_key: str | None = Field(default=None)
    anthropic_api_key: str | None = Field(default=None)

    # Optional integrations
    klaviyo_client_id: str | None = Field(default=None)
    shopify_api_key: str | None = Field(default=None)

    # Feature flags — consumed by feature_flags service and API gateway
    enable_workflows: bool = Field(default=True)
    enable_pipelines: bool = Field(default=True)
    enable_mcp: bool = Field(default=True)

    @property
    def workflows_enabled(self) -> bool:
        return self.enable_workflows

    @property
    def mcp_enabled(self) -> bool:
        return self.enable_mcp

    # Rate limiting
    rate_limit_per_minute: int = Field(default=60)
    rate_limit_storage_url: str | None = Field(default=None)

    # CORS / trusted hosts
    cors_origins: str = Field(default="")
    allowed_hosts: str = Field(default="")

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        if not value:
            raise ValueError("DATABASE_URL must be set")
        return value

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]


_settings: PlatformSettings | None = None


def get_settings() -> PlatformSettings:
    """Return a cached PlatformSettings instance (singleton)."""
    global _settings
    if _settings is None:
        _settings = PlatformSettings()
        _settings.jwt_secret = _resolve_secret("JWT_SECRET", _settings.jwt_secret)
        _settings.webhook_secret = _resolve_secret(
            "WEBHOOK_SECRET", _settings.webhook_secret
        )
    return _settings


def reset_settings() -> None:
    """Reset cached settings (primarily for tests)."""
    global _settings
    _settings = None


@lru_cache(maxsize=1)
def _secret_manager() -> Any:
    """Return the canonical secret manager (env -> .env -> keyring -> vault)."""
    try:
        from shared.production.secrets import get_secret_manager

        return get_secret_manager()
    except ImportError:  # pragma: no cover - canonical package always present
        return None


def _resolve_secret(key: str, fallback: str | None = None) -> str | None:
    """Resolve a secret through the canonical manager, falling back to env."""
    import os

    manager = _secret_manager()
    if manager is not None:
        value = manager.get(key)
        if value:
            return str(value)
    env_value = os.environ.get(key)
    if env_value:
        return env_value
    return fallback


def require_secret(key: str) -> str:
    """Resolve a secret or raise when it is missing.

    Production must never start with a missing credential.
    """
    value = _resolve_secret(key)
    if not value:
        raise RuntimeError(f"Required secret '{key}' is not configured")
    return value


__all__ = [
    "PlatformSettings",
    "REQUIRED_SECRET_KEYS",
    "get_settings",
    "require_secret",
    "reset_settings",
]
