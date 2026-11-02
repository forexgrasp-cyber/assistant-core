"""
Rate Limiting Middleware for FastAPI/Starlette.

Provides token-bucket rate limiting using the canonical shared infrastructure's RateLimiter.
"""

from __future__ import annotations

from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from shared.infrastructure.resilience_patterns import RateLimiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token-bucket rate limiting middleware for FastAPI/Starlette.
    
    Applies different rate limits based on route patterns.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        *,
        default_rate: int = 100,
        default_per: int = 60,
        auth_rate: int = 5,
        auth_per: int = 60,
        api_rate: int = 30,
        api_per: int = 60,
        exempt_paths: Optional[list[str]] = None,
        exempt_ips: Optional[list[str]] = None,
    ):
        super().__init__(app)
        self.default_limiter = RateLimiter(rate=default_rate, per=default_per)
        self.auth_limiter = RateLimiter(rate=auth_rate, per=auth_per)
        self.api_limiter = RateLimiter(rate=api_rate, per=api_per)
        self.exempt_paths = exempt_paths or ["/health", "/docs", "/openapi.json", "/redoc"]
        self.exempt_ips = exempt_ips or []
    
    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request."""
        # Check for X-Forwarded-For header (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting."""
        for exempt in self.exempt_paths:
            if path.startswith(exempt):
                return True
        return False
    
    def _get_limiter(self, path: str) -> RateLimiter:
        """Get the appropriate rate limiter for the path."""
        if path.startswith("/api/auth/"):
            return self.auth_limiter
        elif path.startswith("/api/"):
            return self.api_limiter
        return self.default_limiter
    
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        # Skip rate limiting for exempt paths
        if self._is_exempt(request.url.path):
            return await call_next(request)
        
        # Skip rate limiting for exempt IPs
        client_ip = self._get_client_id(request)
        if client_ip in self.exempt_ips:
            return await call_next(request)
        
        # Get appropriate limiter for this path
        limiter = self._get_limiter(request.url.path)
        
        # Try to acquire token
        if not await limiter.try_acquire(1):
            # Rate limit exceeded
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": 60
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(int(limiter.rate)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(limiter.per)),
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(int(limiter.rate))
        response.headers["X-RateLimit-Remaining"] = str(limiter.available_tokens)
        response.headers["X-RateLimit-Reset"] = str(int(limiter.per))
        
        return response