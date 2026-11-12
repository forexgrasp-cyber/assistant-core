"""Middleware for the platform: correlation IDs, rate limiting, metrics, tracing.

The middleware delegates to the canonical shared implementations so the
platform does not re-implement capabilities that already exist:

* rate limiting uses ``shared.rate_limit.sliding_window.SlidingWindowCounter``
  (Redis-backed, in-memory fallback);
* metrics use ``shared.production.metrics.MetricsCollector``;
* request context / correlation IDs use ``shared.observability.context``;
* tenant context is published for the canonical multitenancy services.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Correlation ID
# ---------------------------------------------------------------------------

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    return correlation_id.get("")


# ---------------------------------------------------------------------------
# Tenant context (multi-tenancy)
# ---------------------------------------------------------------------------

tenant_id_ctx: ContextVar[str] = ContextVar("tenant_id", default="")


def get_tenant_id() -> str:
    return tenant_id_ctx.get("")


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Publish the request tenant to the platform and canonical contexts.

    The ``X-Tenant-Id`` header is advisory only — the effective tenant is
    resolved from the authenticated principal by
    :func:`retention_analytics_core.tenancy.resolve_tenant`. This middleware
    only makes the header value available to downstream code and to the
    canonical ``shared.multitenancy`` context.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        tid = request.headers.get("x-tenant-id", "")
        token = tenant_id_ctx.set(tid)
        try:
            response = await call_next(request)
            if tid:
                response.headers["X-Tenant-Id"] = tid
            return response
        finally:
            tenant_id_ctx.reset(token)


# ---------------------------------------------------------------------------
# Tracing (span context)
# ---------------------------------------------------------------------------

trace_id: ContextVar[str] = ContextVar("trace_id", default="")
span_id: ContextVar[str] = ContextVar("span_id", default="")


def get_trace_id() -> str:
    return trace_id.get("")


def get_span_id() -> str:
    return span_id.get("")


class TracingMiddleware(BaseHTTPMiddleware):
    """OpenTelemetry-compatible trace context propagation.

    Extracts or generates trace_id/span_id from incoming headers and makes
    them available via get_trace_id()/get_span_id() for logs and metrics.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        tid = request.headers.get("x-trace-id") or str(uuid.uuid4())
        sid = request.headers.get("x-span-id") or str(uuid.uuid4())
        token_tid = trace_id.set(tid)
        token_sid = span_id.set(sid)
        try:
            response = await call_next(request)
            response.headers["X-Trace-Id"] = tid
            response.headers["X-Span-Id"] = sid
            return response
        finally:
            trace_id.reset(token_tid)
            span_id.reset(token_sid)


# ---------------------------------------------------------------------------
# Correlation ID
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """OWASP security headers on every response."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        from retention_analytics_shared_config import get_settings
        if get_settings().is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
            response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Generate or propagate a correlation ID for every request.

    The ID is echoed back in the ``X-Correlation-Id`` response header so logs,
    metrics, and traces can be correlated across service boundaries. The same
    value is published to the canonical ``shared.observability.context`` so
    canonical services log with the same correlation ID.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        cid = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        token = correlation_id.set(cid)
        try:
            _publish_canonical_context(cid, request)
            response = await call_next(request)
            response.headers["X-Correlation-Id"] = cid
            return response
        finally:
            correlation_id.reset(token)


def _publish_canonical_context(cid: str, request: Request) -> None:
    """Publish the correlation ID to the canonical observability context."""
    try:
        from shared.observability.context import RequestContext, set_context

        set_context(
            RequestContext(
                correlation_id=cid,
                user_id=request.headers.get("x-user-id"),
                tenant_id=request.headers.get("x-tenant-id"),
            )
        )
    except ImportError:  # pragma: no cover - canonical package always present
        pass


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter backed by the canonical shared counter.

    Returns 429 when a client exceeds ``requests_per_minute`` requests in the
    rolling 60-second window. The canonical counter uses Redis when
    ``RATE_LIMIT_STORAGE_URL`` is configured and an in-process window
    otherwise.
    """

    def __init__(
        self,
        app: Any,
        requests_per_minute: int = 60,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self._counter: Any = None

    def _get_counter(self) -> Any:
        if self._counter is None:
            from retention_analytics_shared_config import get_settings
            from shared.rate_limit.sliding_window import SlidingWindowCounter

            self._counter = SlidingWindowCounter(
                storage_url=get_settings().rate_limit_storage_url
            )
        return self._counter

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        allowed, retry_after = self._get_counter().hit(
            client_ip, self.requests_per_minute, self.window_seconds
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded"},
                headers={"Retry-After": str(retry_after or self.window_seconds)},
            )
        return await call_next(request)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

_REQUEST_COUNT = 0
_REQUEST_LATENCY: list[float] = []


async def metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Any],
) -> Response:
    """Collect per-route request count and latency histogram.

    The canonical Prometheus collector is updated alongside the platform
    snapshot so both the ``/metrics`` endpoint and the canonical exporter
    report the same traffic.
    """
    global _REQUEST_COUNT
    start = time.monotonic()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        elapsed = time.monotonic() - start
        _REQUEST_COUNT += 1
        _REQUEST_LATENCY.append(elapsed)
        if len(_REQUEST_LATENCY) > 1000:
            _REQUEST_LATENCY.pop(0)
        _record_canonical_metrics(request, status_code, elapsed)


def _record_canonical_metrics(request: Request, status_code: int, elapsed: float) -> None:
    """Record the request into the canonical metrics collector."""
    try:
        from retention_analytics_core.canonical import get_adapters

        metrics = get_adapters().metrics
        counter = metrics.counter(
            "retention_analytics_http_requests_total",
            "Total HTTP requests handled by the platform API.",
        )
        counter.inc()
        histogram = metrics.histogram(
            "retention_analytics_http_request_duration_seconds",
            "HTTP request duration in seconds.",
        )
        histogram.observe(elapsed)
    except Exception as exc:  # noqa: BLE001 - metrics must never break a request
        logger.warning("metrics.record_failed", error=str(exc))


def get_metrics() -> dict[str, Any]:
    """Return current metrics snapshot."""
    latency = sorted(_REQUEST_LATENCY)
    p50 = latency[int(len(latency) * 0.5)] if latency else 0.0
    p95 = latency[int(len(latency) * 0.95)] if latency else 0.0
    p99 = latency[int(len(latency) * 0.99)] if latency else 0.0
    return {
        "request_count": _REQUEST_COUNT,
        "latency_p50_ms": round(p50 * 1000, 2),
        "latency_p95_ms": round(p95 * 1000, 2),
        "latency_p99_ms": round(p99 * 1000, 2),
    }


def get_metrics_prometheus() -> str:
    """Return metrics in Prometheus text format."""
    metrics = get_metrics()
    lines = [
        "# HELP retention_analytics_request_count Total number of HTTP requests.",
        "# TYPE retention_analytics_request_count counter",
        f"retention_analytics_request_count {metrics['request_count']}",
        "# HELP retention_analytics_request_latency_p50_ms 50th percentile request latency in ms.",
        "# TYPE retention_analytics_request_latency_p50_ms gauge",
        f"retention_analytics_request_latency_p50_ms {metrics['latency_p50_ms']}",
        "# HELP retention_analytics_request_latency_p95_ms 95th percentile request latency in ms.",
        "# TYPE retention_analytics_request_latency_p95_ms gauge",
        f"retention_analytics_request_latency_p95_ms {metrics['latency_p95_ms']}",
        "# HELP retention_analytics_request_latency_p99_ms 99th percentile request latency in ms.",
        "# TYPE retention_analytics_request_latency_p99_ms gauge",
        f"retention_analytics_request_latency_p99_ms {metrics['latency_p99_ms']}",
    ]
    canonical = _canonical_prometheus()
    if canonical:
        lines.append(canonical.rstrip("\n"))
    return "\n".join(lines) + "\n"


def _canonical_prometheus() -> str:
    """Return the canonical collector's Prometheus exposition, if available."""
    try:
        from retention_analytics_core.canonical import get_adapters

        return get_adapters().metrics.prometheus()
    except Exception:  # noqa: BLE001 - metrics must never break a request
        return ""


__all__ = [
    "CorrelationIdMiddleware",
    "RateLimitMiddleware",
    "TenantContextMiddleware",
    "TracingMiddleware",
    "metrics_middleware",
    "get_correlation_id",
    "get_trace_id",
    "get_span_id",
    "get_tenant_id",
    "get_metrics",
    "get_metrics_prometheus",
]
