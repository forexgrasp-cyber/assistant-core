"""
Custom exceptions and exception handlers.
"""

from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError
import structlog

logger = structlog.get_logger()


class AppException(Exception):
    """Base application exception."""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        code: str = "INTERNAL_ERROR",
        details: dict = None,
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    """Resource not found."""
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            status_code=404,
            code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier}
        )


class ValidationError(AppException):
    """Validation error."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            status_code=422,
            code="VALIDATION_ERROR",
            details=details or {}
        )


class AuthenticationError(Exception):
    """Authentication error."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=401,
            code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(Exception):
    """Authorization error."""
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            status_code=403,
            code="AUTHORIZATION_ERROR"
        )


class RateLimitError(Exception):
    """Rate limit exceeded."""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(
            message=message,
            status_code=429,
            code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after} if retry_after else {}
        )


class TenantNotFoundError(Exception):
    """Tenant not found."""
    def __init__(self, tenant_slug: str):
        super().__init__(
            message=f"Tenant not found: {tenant_slug}",
            status_code=404,
            code="TENANT_NOT_FOUND",
            details={"tenant_slug": tenant_slug}
        )


class ResourceConflictError(Exception):
    """Resource conflict."""
    def __init__(self, message: str, resource: str = None, identifier: str = None):
        super().__init__(
            message=message,
            status_code=409,
            code="CONFLICT",
            details={"resource": resource, "identifier": identifier} if resource else {}
        )


class ExternalServiceError(Exception):
    """External service error."""
    def __init__(self, service: str, message: str, status_code: int = 502):
        super().__init__(
            message=f"{service} error: {message}",
            status_code=status_code,
            code="EXTERNAL_SERVICE_ERROR",
            details={"service": service}
        )


def setup_exception_handlers(app):
    """Set up exception handlers for the FastAPI app."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        logger.warning(
            "http_exception",
            path=exc.request.url.path if hasattr(exc, 'request') else None,
            status_code=exc.status_code,
            detail=exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "code": f"HTTP_{exc.status_code}",
                "status_code": exc.status_code,
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc: RequestValidationError):
        logger.warning(
            "validation_error",
            path=request.url.path,
            errors=exc.errors(),
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation error",
                "code": "VALIDATION_ERROR",
                "status_code": 422,
                "details": exc.errors(),
            }
        )
    
    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(request, exc: ValidationError):
        logger.warning(
            "pydantic_validation_error",
            path=request.url.path,
            errors=exc.errors(),
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation error",
                "code": "VALIDATION_ERROR",
                "status_code": 422,
                "details": exc.errors(),
            }
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request, exc: Exception):
        logger.exception(
            "unhandled_exception",
            path=request.url.path,
            error=str(exc),
            exc_info=True,
        )
        
        # Don't expose internal errors in production
        from .config import get_settings
        settings = get_settings()
        
        if settings.is_production():
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "code": "INTERNAL_ERROR",
                    "status_code": 500,
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "code": "INTERNAL_ERROR",
                    "status_code": 500,
                    "detail": str(exc),
                }
            )
    
    # Custom exceptions
    @app.exception_handler(AppException)
    async def app_exception_handler(request, exc: AppException):
        logger.warning(
            "app_exception",
            path=request.url.path,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "code": exc.code,
                "status_code": exc.status_code,
                "details": exc.details,
            }
        )
    
    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request, exc: NotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "error": exc.message,
                "code": exc.code,
                "status_code": 404,
                "details": exc.details,
            }
        )
    
    @app.exception_handler(ValidationError)
    async def custom_validation_error_handler(request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": exc.message,
                "code": exc.code,
                "status_code": 422,
                "details": exc.details,
            }
        )
    
    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request, exc: AuthenticationError):
        return JSONResponse(
            status_code=401,
            content={
                "error": exc.message,
                "code": exc.code,
                "status_code": 401,
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    @app.exception_handler(AuthorizationError)
    async def authz_error_handler(request, exc: AuthorizationError):
        return JSONResponse(
            status_code=403,
            content={
                "error": exc.message,
                "code": exc.code,
                "status_code": 403,
            }
        )
    
    @app.exception_handler(RateLimitError)
    async def rate_limit_error_handler(request, exc: RateLimitError):
        return JSONResponse(
            status_code=429,
            content={
                "error": exc.message,
                "code": exc.code,
                "status_code": 429,
                "details": exc.details,
            },
            headers={
                "Retry-After": str(exc.details.get("retry_after", 60)),
            }
        )
    
    @app.exception_handler(TenantNotFoundError)
    async def tenant_not_found_handler(request, exc: TenantNotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "error": exc.message,
                "code": exc.code,
                "status_code": 404,
                "details": exc.details,
            }
        )
    
    @app.exception_handler(ResourceConflictError)
    async def conflict_error_handler(request, exc: ResourceConflictError):
        return JSONResponse(
            status_code=409,
            content={
                "error": exc.message,
                "code": exc.code,
                "status_code": 409,
                "details": exc.details,
            }
        )
    
    @app.exception_handler(ExternalServiceError)
    async def external_service_error_handler(request, exc: ExternalServiceError):
        logger.error(
            "external_service_error",
            service=exc.details.get("service"),
            error=exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "code": exc.code,
                "status_code": exc.status_code,
                "details": exc.details,
            }
        )
    
    # SQLAlchemy errors
    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request, exc: IntegrityError):
        logger.warning(
            "integrity_error",
            path=exc.request.url.path if hasattr(exc, 'request') else None,
            error=str(exc.orig),
        )
        return JSONResponse(
            status_code=409,
            content={
                "error": "Resource conflict",
                "code": "INTEGRITY_ERROR",
                "status_code": 409,
                "details": {"message": "A resource with this identifier already exists"},
            }
        )
    
    @app.exception_handler(OperationalError)
    async def operational_error_handler(request, exc: OperationalError):
        logger.error(
            "operational_error",
            path=request.url.path if hasattr(request, 'url') else None,
            error=str(exc),
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": "Database temporarily unavailable",
                "code": "DATABASE_UNAVAILABLE",
                "status_code": 503,
            }
        )