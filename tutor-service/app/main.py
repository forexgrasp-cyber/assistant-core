"""
Tutor Service - Award-winning Language Learning Platform
Thin wrapper around shared-canonical-services vertical app factory.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import structlog

from shared.agent_apps.app_factory import create_app_from_bundle
from shared.agent_runtime.capabilities import ProductBundle
from shared.platform.unified_platform import UnifiedPlatformService
from shared.config import init_db


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
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting Tutor Service", version="2026.11.3")
    await init_db()
    logger.info("Database initialized")
    
    platform = UnifiedPlatformService(tenant_id="default")
    app.state.platform = platform
    
    logger.info("Tutor Service initialized")
    yield
    
    logger.info("Shutting down Tutor Service")


# Create app from ProductBundle - this is the ENTIRE service
app = create_app_from_bundle(
    ProductBundle.TUTOR_PRO,
    tenant_id="default",
    business_name="LinguaFlow",
    title="Tutor Service",
    version="2026.11.3",
    dry_run=False,
)

# Override lifespan
app.router.lifespan_context = lifespan

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for frontend
app.mount("/assets", StaticFiles(directory="app/static/assets"), name="assets")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def root():
    """Serve frontend index.html"""
    return FileResponse("app/static/index.html")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve frontend for all other routes (SPA)"""
    return FileResponse("app/static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8147,
        reload=True,
        log_config=None,
    )