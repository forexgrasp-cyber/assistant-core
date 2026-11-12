"""Canonical shared-service adapters for the retention analytics platform.

PRODUCTION_STANDARDS.md L1 forbids re-implementing capabilities that the
canonical ``shared/`` library already provides. Every canonical service the
platform needs is consumed here through a thin adapter that:

* resolves the canonical implementation (never a local copy),
* applies the platform's storage paths and tenant scoping,
* exposes a single process-wide instance so services, workers and scripts
  share the same state.

The canonical implementations keep their own contracts:

``shared.production.secrets.SecretManager``
    env -> .env file -> OS keyring -> vault.
``shared.idempotency.idempotency_ledger.IdempotencyStore``
    append-only JSONL ledger with claim/complete semantics.
``shared.audit.immutable_audit_log.ImmutableAuditLog``
    SQLite hash-chained audit trail (per-tenant chain).
``shared.production.health.HealthChecker``
    liveness/readiness checks with per-dependency probes.
``shared.rate_limit.sliding_window.SlidingWindowCounter``
    Redis-backed sliding window with in-memory fallback.
``shared.production.metrics.MetricsCollector``
    Prometheus-compatible counters, gauges and histograms.
``shared.production.retry.RetryHandler`` / ``CircuitBreaker``
    retry with exponential backoff plus per-host circuit breaking.
``shared.http_client.resilient_http_client.ResilientHTTPClient``
    HTTP client with mandatory timeout, retry and circuit breaker.
``shared.payments.registry``
    provider-agnostic payment providers (the project never imports a
    payment SDK directly).
``shared.config_service.ConfigService``
    layered configuration (defaults -> file -> env -> runtime -> tenant).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from retention_analytics_shared_config import get_settings
from shared.audit.immutable_audit_log import ImmutableAuditLog
from shared.config_service import ConfigService
from shared.idempotency.idempotency_ledger import IdempotencyStore
from shared.production.health import HealthChecker, HealthStatus
from shared.production.metrics import MetricsCollector
from shared.production.retry import RetryConfig, RetryHandler, get_retry_handler
from shared.production.secrets import SecretManager, get_secret_manager
from shared.rate_limit.sliding_window import SlidingWindowCounter

__all__ = [
    "AuditTrail",
    "CanonicalAdapters",
    "ConfigProvider",
    "HttpClientProvider",
    "IdempotencyLedger",
    "MetricsProvider",
    "RateLimiter",
    "RetryProvider",
    "SecretProvider",
    "get_adapters",
]


def _data_dir() -> Path:
    """Return the platform data directory, creating it when needed."""
    settings = get_settings()
    path = Path(settings.data_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


class SecretProvider:
    """Adapter over ``shared.production.secrets.SecretManager``.

    The platform never hardcodes a credential. Secrets are resolved from the
    environment first, then a local ``.env`` file, then the OS keyring, then
    a configured vault backend.
    """

    def __init__(self, manager: SecretManager | None = None) -> None:
        self._manager = manager or get_secret_manager()

    def get(self, key: str, default: Any = None) -> Any:
        return self._manager.get(key, default)

    def require(self, key: str) -> str:
        return self._manager.require(key)

    def sources(self) -> dict[str, bool]:
        return self._manager.list_sources()


class IdempotencyLedger:
    """Adapter over the canonical append-only idempotency ledger.

    ``claim`` reserves a key for the current caller, ``complete`` records the
    result so replays return the original outcome instead of re-executing
    money or data side effects.
    """

    def __init__(self, store: IdempotencyStore) -> None:
        self._store = store

    @staticmethod
    def build_key(*parts: str) -> str:
        return IdempotencyStore.build_key(*parts)

    def claim(self, key: str, tenant_id: str = "") -> tuple[bool, dict[str, Any] | None]:
        """Reserve ``key``; returns ``(claimed, prior_result)``.

        A prior record that is still ``pending`` means another caller holds
        the claim, so it is reported as a duplicate with no result yet.

        ``check_and_set`` already unwraps the stored entry's ``result`` field,
        so ``record`` here is the result dict directly (or ``None``).
        """
        claimed, record = self._store.check_and_set(key, tenant_id=tenant_id)
        if claimed:
            return True, None
        if not isinstance(record, dict):
            return False, None
        if record.get("status") == "pending":
            return False, None
        return False, record

    def complete(self, key: str, result: dict[str, Any]) -> None:
        self._store.complete(key, result)

    def lookup(self, key: str) -> dict[str, Any] | None:
        return self._store.lookup(key)

    def release(self, key: str) -> None:
        """Drop a claim so a failed operation can be retried."""
        self._store.record(key, {"status": "released"})


class AuditTrail:
    """Adapter over the canonical hash-chained audit log."""

    def __init__(self, log: ImmutableAuditLog) -> None:
        self._log = log

    def record(
        self,
        *,
        event_type: str,
        actor_id: str,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._log.log_event(
            event_type=event_type,
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
        )

    def verify(self, tenant_id: str) -> dict[str, Any]:
        return self._log.verify_chain_integrity(tenant_id)

    def query(self, tenant_id: str, **filters: Any) -> list[dict[str, Any]]:
        return self._log.query_audit_log(tenant_id, **filters)


class ConfigProvider:
    """Adapter over the canonical layered configuration service.

    Precedence is defaults < file < environment < runtime overrides, with a
    per-tenant override layer on top.
    """

    def __init__(self, service: ConfigService) -> None:
        self._service = service

    def get(self, key: str, default: Any = None) -> Any:
        return self._service.get(key, default)

    def for_tenant(self, tenant_id: str, key: str, default: Any = None) -> Any:
        return self._service.get_for_tenant(tenant_id, key, default)

    def set_override(self, key: str, value: Any) -> None:
        self._service.set_override(key, value)

    def set_tenant_override(self, tenant_id: str, key: str, value: Any) -> None:
        self._service.set_tenant_override(tenant_id, key, value)


class RateLimiter:
    """Adapter over the canonical sliding-window limiter.

    Uses Redis when ``RATE_LIMIT_STORAGE_URL`` points at a Redis instance and
    falls back to an in-process counter otherwise, so the platform never
    silently allows unlimited traffic.
    """

    def __init__(self, counter: SlidingWindowCounter) -> None:
        self._counter = counter

    def check(self, key: str, limit: int, window: int = 60) -> tuple[bool, int | None]:
        """Return ``(allowed, retry_after_seconds)``."""
        allowed, retry_after = self._counter.hit(key, limit, window)
        return allowed, retry_after

    def reset(self, key: str) -> None:
        self._counter.reset(key)

    @property
    def distributed(self) -> bool:
        return self._counter.redis_available


class MetricsProvider:
    """Adapter over the canonical Prometheus-compatible metrics collector."""

    def __init__(self, collector: MetricsCollector) -> None:
        self._collector = collector

    def counter(self, name: str, help_text: str = "", labels: Any = None) -> Any:
        return self._collector.counter(name, help_text, labels)

    def gauge(self, name: str, help_text: str = "", labels: Any = None) -> Any:
        return self._collector.gauge(name, help_text, labels)

    def histogram(self, name: str, help_text: str = "", labels: Any = None) -> Any:
        return self._collector.histogram(name, help_text, labels)

    def prometheus(self) -> str:
        return self._collector.generate_prometheus()


class RetryProvider:
    """Adapter over the canonical retry handler and circuit breaker."""

    def __init__(self, handler: RetryHandler) -> None:
        self._handler = handler

    async def execute(
        self,
        func: Any,
        *args: Any,
        config: RetryConfig | None = None,
        circuit_breaker_name: str | None = None,
        **kwargs: Any,
    ) -> Any:
        return await self._handler.execute(
            func, *args, config=config, circuit_breaker_name=circuit_breaker_name, **kwargs
        )

    def circuit_state(self, name: str) -> str | None:
        return self._handler.get_circuit_breaker_state(name)

    def reset_circuit(self, name: str) -> bool:
        return self._handler.reset_circuit_breaker(name)


class HttpClientProvider:
    """Adapter over the canonical resilient HTTP client.

    Every outbound call gets a mandatory timeout, bounded retries on
    transient failures and a per-host circuit breaker.
    """

    def __init__(self) -> None:
        from shared.http_client.resilient_http_client import ResilientHTTPClient

        self._client = ResilientHTTPClient()

    @property
    def client(self) -> Any:
        return self._client

    async def request(self, method: str, url: str, **kwargs: Any) -> Any:
        return await self._client.request(method, url, **kwargs)

    async def aclose(self) -> None:
        await self._client.aclose()


class CanonicalAdapters:
    """Container for every canonical shared-service adapter."""

    def __init__(self) -> None:
        settings = get_settings()
        data_dir = _data_dir()

        self.secrets = SecretProvider()
        self.idempotency = IdempotencyLedger(
            IdempotencyStore(str(data_dir / "idempotency_ledger.jsonl"))
        )
        self.audit = AuditTrail(ImmutableAuditLog(str(data_dir / "audit_log.db")))
        self.config = ConfigProvider(
            ConfigService(
                defaults={
                    "rate_limit_per_minute": settings.rate_limit_per_minute,
                    "environment": settings.environment,
                    "jwt_algorithm": settings.jwt_algorithm,
                },
                file_config={},
                env=dict(os.environ),
            )
        )
        self.rate_limiter = RateLimiter(
            SlidingWindowCounter(storage_url=settings.rate_limit_storage_url)
        )
        self.metrics = MetricsProvider(MetricsCollector())
        self.retry = RetryProvider(get_retry_handler())
        self.health = HealthChecker(service_name="retention-analytics-platform")

    def require_health_ready(self) -> bool:
        """True when every registered dependency probe is healthy."""
        return all(
            check.status == HealthStatus.HEALTHY for check in self.health._checks
        )


_adapters: CanonicalAdapters | None = None


def get_adapters() -> CanonicalAdapters:
    """Return the process-wide canonical adapter container."""
    global _adapters
    if _adapters is None:
        _adapters = CanonicalAdapters()
    return _adapters


def reset_adapters() -> None:
    """Reset the adapter container (test isolation)."""
    global _adapters
    _adapters = None
