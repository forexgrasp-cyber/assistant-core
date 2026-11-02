"""
Monitoring utilities for the VA Matching Platform.

Provides readiness probes, Prometheus metrics, and structured logging with correlation IDs.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable, Optional

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from prometheus_client.core import CollectorRegistry
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from marketplace.database import async_session_maker

# Structured logging with correlation IDs
_correlation_id_var: Optional[str] = None


def get_correlation_id() -> str:
    """Get the current correlation ID, generating one if not set."""
    global _correlation_id_var
    if _correlation_id_var is None:
        _correlation_id_var = str(uuid.uuid4())
    return _correlation_id_var


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set the correlation ID for the current context."""
    global _correlation_id_var
    _correlation_id_var = correlation_id or str(uuid.uuid4())
    return _correlation_id_var


def clear_correlation_id() -> None:
    """Clear the correlation ID."""
    global _correlation_id_var
    _correlation_id_var = None


class CorrelationIdFilter(logging.Filter):
    """Logging filter to add correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


def setup_structured_logging() -> None:
    """Configure structured logging with correlation IDs."""
    # Add correlation ID filter to root logger
    root_logger = logging.getLogger()
    root_logger.addFilter(CorrelationIdFilter())
    
    # Configure formatter with correlation ID
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-5s [%(name)s] [correlation_id=%(correlation_id)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Apply to all handlers
    for handler in logging.root.handlers:
        handler.setFormatter(formatter)
    
    # Also apply to structlog if available
    try:
        import structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    except ImportError:
        pass


# Prometheus metrics
REGISTRY = CollectorRegistry()

# HTTP metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=REGISTRY
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY
)

# Database metrics
DB_CONNECTIONS_ACTIVE = Gauge(
    "db_connections_active",
    "Number of active database connections",
    registry=REGISTRY
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=REGISTRY
)

# Business metrics
ACTIVE_MATCHES = Gauge(
    "active_matches_total",
    "Number of active matches",
    registry=REGISTRY
)

TOTAL_CLIENTS = Gauge(
    "total_clients_total",
    "Total number of clients",
    registry=REGISTRY
)

PLACEMENT_FEES_CHARGED = Counter(
    "placement_fees_charged_total",
    "Total placement fees charged",
    ["status"],
    registry=REGISTRY
)

MONTHLY_FEES_CHARGED = Counter(
    "monthly_fees_charged_total",
    "Total monthly fees charged",
    ["status"],
    registry=REGISTRY
)


@dataclass
class MetricsMiddleware:
    """Middleware to collect Prometheus metrics for HTTP requests."""
    
    app: FastAPI
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics for health/readiness endpoints
        if request.url.path in ("/health", "/ready", "/metrics"):
            return await self.app(request, call_next)
        
        method = request.method
        endpoint = request.url.path
        start_time = time.time()
        
        # Process request
        response = await self.app(request, call_next)
        
        # Record metrics
        duration = time.time() - start_time
        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()
        HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        
        return response


async def readiness_check(request: Request) -> dict[str, Any]:
    """
    Comprehensive readiness check.
    
    Checks:
    - Database connectivity
    - Database schema integrity
    - Critical service availability
    
    Returns:
        Dict with status and details
    """
    checks = {
        "database": {"status": "unknown", "details": {}},
        "schema": {"status": "unknown", "details": {}},
    }
    overall_status = "ready"
    
    # Create a new session for the check
    session = async_session_maker()
    close_session = True
    
    try:
        # Check database connectivity
        try:
            start = time.time()
            await session.execute(text("SELECT 1"))
            latency = (time.time() - start) * 1000
            checks["database"]["status"] = "healthy"
            checks["database"]["details"]["latency_ms"] = round(latency, 2)
        except Exception as e:
            checks["database"]["status"] = "unhealthy"
            checks["database"]["details"]["error"] = str(e)
            overall_status = "not_ready"
        
        # Check schema integrity (verify critical tables exist)
        try:
            # Check a few critical tables
            for table in ["users", "va_profiles", "client_profiles", "matches"]:
                result = await session.execute(
                    text(f"SELECT 1 FROM {table} LIMIT 1")
                )
            checks["schema"]["status"] = "healthy"
        except Exception as e:
            checks["schema"]["status"] = "unhealthy"
            checks["schema"]["details"]["error"] = str(e)
            overall_status = "not_ready"
        
    except Exception as e:
        overall_status = "not_ready"
        checks["database"]["status"] = "error"
        checks["database"]["details"]["error"] = str(e)
    finally:
        if close_session:
            await session.close()
    
    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": time.time(),
    }


async def liveness_check() -> dict[str, Any]:
    """Simple liveness check - always returns healthy if process is running."""
    return {
        "status": "healthy",
        "service": "va-matching-platform",
        "timestamp": time.time(),
    }


async def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


def add_monitoring(app: FastAPI) -> None:
    """Add monitoring endpoints and middleware to FastAPI app."""
    
    # Setup structured logging
    setup_structured_logging()
    
    # Add metrics middleware
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        # Skip metrics for internal endpoints
        if request.url.path in ("/health", "/ready", "/metrics"):
            return await call_next(request)
        
        # Set correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        set_correlation_id(correlation_id)
        
        method = request.method
        endpoint = request.url.path
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()
        HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = get_correlation_id()
        
        return response
    
    # Add monitoring endpoints
    app.add_api_route("/health", liveness_check, methods=["GET"], tags=["monitoring"])
    app.add_api_route("/ready", readiness_check, methods=["GET"], tags=["monitoring"])
    app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], tags=["monitoring"])
    
    # Add shutdown handler to clear correlation ID
    @app.middleware("http")
    async def correlation_cleanup(request: Request, call_next):
        response = await call_next(request)
        clear_correlation_id()
        return response