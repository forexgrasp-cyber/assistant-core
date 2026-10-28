"""
Middleware for the FastAPI application.
"""

import time
import json
import logging
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog

from .config import get_settings
from .security import apply_security_headers
from .redis import get_redis

logger = structlog.get_logger()
settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        return apply_security_headers(response)


class TenantMiddleware(BaseHTTPMiddleware):
    """Extract and validate tenant context from request."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract tenant from header or subdomain
        tenant_slug = request.headers.get("X-Tenant-Slug")
        
        if not tenant_slug:
            # Try to extract from subdomain
            host = request.headers.get("host", "")
            if "." in host:
                subdomain = host.split(".")[0]
                if subdomain not in ("www", "api", "app", "admin"):
                    tenant_slug = subdomain
        
        if not tenant_slug:
            tenant_slug = "default"
        
        # Store in request state
        request.state.tenant_slug = tenant_slug
        request.state.tenant_id = None  # Will be resolved by auth dependency
        
        # Continue
        response = await call_next(request)
        response.headers["X-Tenant-Slug"] = tenant_slug
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis."""
    
    def __init__(self, app):
        super().__init__(app)
        self.redis = None
        self._redis_available = True
    
    async def _get_redis(self):
        if self.redis is None and self._redis_available:
            try:
                from .redis import get_redis
                self.redis = await get_redis()
                # Test connection
                await self.redis.ping()
            except Exception:
                self._redis_available = False
                self.redis = None
        return self.redis
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ("/health", "/health/ready", "/health/live"):
            return await call_next(request)
        
        redis = await self._get_redis()
        
        # Skip rate limiting if Redis is not available
        if redis is None:
            return await call_next(request)
        
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None)
        
        # Use user ID if authenticated, otherwise IP
        identifier = f"user:{user_id}" if user_id else f"ip:{client_ip}"
        
        # Rate limit key
        key = f"ratelimit:{identifier}:{request.url.path}"
        
        try:
            # Check rate limit
            current = await redis.incr(key)
            if current == 1:
                # Set expiry on first request
                await self._redis_expire(key, settings.rate_limit.window)
            
            if current > settings.rate_limit.requests:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Limit: {settings.rate_limit.requests} per {settings.rate_limit.window}s"
                    },
                    headers={
                        "X-RateLimit-Limit": str(settings.rate_limit.requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time()) + settings.rate_limit.window),
                        "Retry-After": str(settings.rate_limit.window),
                    }
                )
        except Exception:
            # If Redis fails, skip rate limiting
            pass
        
        response = await call_next(request)
        
        # Add rate limit headers
        try:
            response.headers["X-RateLimit-Limit"] = str(settings.rate_limit.requests)
            response.headers["X-RateLimit-Remaining"] = str(
                max(0, settings.rate_limit.requests - int(await redis.get(f"ratelimit:{identifier}:{request.url.path}") or 0))
            )
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + settings.rate_limit.window)
        except Exception:
            pass
        
        return response
    
    async def _redis_expire(self, key: str, window: int):
        redis = await self._get_redis()
        if redis:
            try:
                await redis.expire(key, window)
            except Exception:
                pass


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
        )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
            )
            raise
        
        # Log response
        duration = time.time() - start_time
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )
        
        # Add timing header
        response.headers["X-Process-Time"] = str(round(duration * 1000, 2))
        
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Add request ID to all requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or secrets.token_urlsafe(16)
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class CompressionMiddleware(BaseHTTPMiddleware):
    """Compress responses using gzip."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Only compress if client accepts gzip
        if "gzip" in request.headers.get("accept-encoding", ""):
            # FastAPI handles compression automatically if configured
            pass
        
        return response


def setup_middleware(app):
    """Set up all middleware for the application."""
    # Order matters - first added is outermost
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CompressionMiddleware)
    
    return app