"""
Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog
from typing import Any

from .core.config import get_settings
from .core.database import init_db, close_db
from .core.security import get_password_hash, verify_password
from .api.v1.router import api_router
from .core.exceptions import setup_exception_handlers
from .core.middleware import TenantMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from .services.demo_service import init_demo_services, shutdown_demo_services

logger = structlog.get_logger()

settings = get_settings()

# Global workflow engine instances
_workflow_engines: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting application", env=settings.env)
    await init_db()
    
    # Initialize demo services
    await init_demo_services()
    logger.info("Demo services initialized")
    
    # Initialize workflow engines for each tenant
    # In production, would get tenants from database
    # For now, start engine for default tenant
    # default_tenant = "default"
    # _workflow_engines[default_tenant] = await startup_workflow_engine(default_tenant)
    # logger.info("Workflow engine started", tenant=default_tenant)

    yield

    # Shutdown
    logger.info("Shutting down application")
    # for tenant_id, engine in _workflow_engines.items():
    #     await shutdown_workflow_engine(tenant_id)
    # _workflow_engines.clear()
    
    # Shutdown demo services
    await shutdown_demo_services()
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.name,
        description="Multi-tenant retention analytics platform for marketing agencies",
        version="0.1.0",
        docs_url="/docs" if not settings.is_production() else None,
        redoc_url="/redoc" if not settings.is_production() else None,
        openapi_url="/openapi.json" if not settings.is_production() else None,
        lifespan=lifespan,
    )
    
    # Security middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins if hasattr(settings, 'cors_origins') else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Trusted host middleware (production only)
    if settings.is_production():
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts if hasattr(settings, 'allowed_hosts') else ["*"]
        )
    
    # Custom middleware
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    # Exception handlers
    setup_exception_handlers(app)
    
    # Include API router
    app.include_router(api_router, prefix="/api/v1")
    
    # Health check endpoints
    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "healthy", "version": "0.1.0", "env": settings.env}
    
    @app.get("/health/ready", tags=["health"])
    async def readiness_check():
        # TODO: Check database, Redis, ClickHouse connections
        return {"status": "ready", "checks": {"database": "ok", "redis": "ok"}}
    
    @app.get("/health/live", tags=["health"])
    async def liveness_check():
        return {"status": "alive"}
    
    # Root endpoint
    @app.get("/", tags=["root"])
    async def root():
        return {
            "name": settings.name,
            "version": "0.1.0",
            "docs": "/docs" if not settings.is_production() else None,
            "api": "/api/v1"
        }
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "apps.api.app.main:app",
        host="0.0.0.0",
        port=8765,
        reload=settings.debug,
        log_config=None,
    )