from .auth import router as auth_router
from .tenants import router as tenants_router
from .clients import router as clients_router
from .engagement import router as engagement_router
from .ecommerce import router as ecommerce_router
from .analytics import router as analytics_router
from .reporting import router as reporting_router
from .workflows import router as workflows_router

# Optional imports - may fail if shared-canonical-services not fully available
optional_routers = {}
for module_name, router_name in [
    ("workflows_v2", "workflows_v2_router"),
    ("llm_models", "llm_models_router"),
]:
    try:
        module = __import__(f".{module_name}", fromlist=[router_name])
        optional_routers[router_name] = getattr(module, router_name)
    except ImportError:
        pass

from .vertical_packs import router as vertical_packs_router
from .webhooks import router as webhooks_router
from .admin import router as admin_router
from .demo import router as demo_router

from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenants_router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(clients_router, prefix="/clients", tags=["Clients"])
api_router.include_router(engagement_router, prefix="/engagement", tags=["Engagement"])
api_router.include_router(ecommerce_router, prefix="/ecommerce", tags=["Ecommerce"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(reporting_router, prefix="/reports", tags=["Reporting"])
api_router.include_router(workflows_router, prefix="/workflows", tags=["Workflows"])
for router in optional_routers.values():
    if router:
        api_router.include_router(router, prefix="/workflows" if "workflows" in str(router) else "/llm", tags=["Workflows v2" if "workflows" in str(router) else "LLM Models"])
api_router.include_router(vertical_packs_router, prefix="/vertical-packs", tags=["Vertical Packs"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
api_router.include_router(demo_router, prefix="/demo", tags=["Demo"])


@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api", "version": "v1"}


@api_router.get("/version")
async def version():
    return {"version": "v1", "api": "retention-analytics-platform"}