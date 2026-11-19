"""
AI Assistant — one deployment, every agent product.

This is the *wrapper project*: it assembles the reusable services from
``shared-canonical-services`` into a single capability-based platform.

- Agent core        : shared.agent_runtime (UniversalAgent + AgentDefinition)
- Agent config      : shared.agent_runtime.spec (VerticalSpec)
- App assembly      : shared.agent_apps (routers, per-vertical services)
- Multi-product app : shared.platform (UnifiedPlatformService + app factory)
- Entitlements      : shared.agent_runtime.entitlements

Everything reusable lives in ``shared/``; everything product-specific
(landing page, dashboard, deployment wiring) lives in this project.

Run locally:
    uvicorn app.main:app --port 8000
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from shared.agent_apps.dependencies import (
    get_tenant_entitlements,
    resolve_tenant_id,
)
from shared.agent_runtime.capabilities import (
    Capability,
    PRODUCT_BUNDLES,
    ProductBundle,
    resolve_capabilities,
)
from shared.agent_runtime.entitlements import EntitlementService, get_entitlement_service
from shared.platform.app_factory import create_unified_platform_app
from shared.platform.unified_platform import UnifiedPlatformService

VERSION = "2026.11.4"
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
DEFAULT_TENANT = "tenant-combo"


# ============================================================
# Lifespan & Initialization
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[START] Starting AI Assistant platform...")
    app.state.platform = UnifiedPlatformService()
    # The process-wide singleton — the shared entitlement dependencies
    # resolve it the same way, so grants made through one route are
    # visible through all of them.
    app.state.entitlement_service = get_entitlement_service()
    await load_tenant_entitlements(app.state.entitlement_service)
    print("[OK] AI Assistant platform ready!")
    yield
    print("[STOP] Shutting down AI Assistant platform...")


async def load_tenant_entitlements(entitlement_service: EntitlementService) -> None:
    """Load tenant entitlements (demo tenants in dev, DB in production)."""
    demo_tenants = {
        "tenant-callagent": ProductBundle.CALLAGENT_STARTER,
        "tenant-tutor": ProductBundle.TUTOR_FREE,
        "tenant-jarvis": ProductBundle.JARVIS_PERSONAL,
        "tenant-hvac": ProductBundle.HVAC_STARTER,
    }

    for tenant_id, bundle in demo_tenants.items():
        entitlement_service.assign_bundle(tenant_id, bundle)

    # Combo gets everything - grant all capabilities
    for cap in Capability:
        entitlement_service.grant_capability("tenant-combo", cap)

    print(f"Loaded entitlements for {len(demo_tenants) + 1} demo tenants")


# ============================================================
# App Creation
# ============================================================
app = create_unified_platform_app(
    title="AI Assistant",
    service_name="ai-assistant",
    version=VERSION,
    lifespan=lifespan,
)
app.state.default_tenant_id = DEFAULT_TENANT

os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ============================================================
# Dependency: Get Current Tenant
# ============================================================
async def get_current_tenant(request: Request) -> str:
    """Resolve the tenant for this request.

    Delegates to the canonical resolver in ``shared.agent_apps.dependencies``
    so this app and the shared platform routes always agree on the tenant:
    ``X-Tenant-ID`` header > subdomain > ``?tenant=`` > ``?tenant_id=`` >
    ``request.state`` > the app default (``tenant-combo``).
    """
    return resolve_tenant_id(request, default=DEFAULT_TENANT)


# ============================================================
# Entitlement Check Dependency
# ============================================================
def require_capability(capability: Capability):
    """Dependency that checks if tenant has a capability."""

    async def check(request: Request, tenant_id: str = Depends(get_current_tenant)):
        entitlement_service: EntitlementService = request.app.state.entitlement_service
        if not entitlement_service.check_capability(tenant_id, capability):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Capability not enabled",
                    "capability": capability.value,
                    "tenant": tenant_id,
                    "message": f"This feature requires '{capability.value}' capability. Contact admin to enable.",
                },
            )
        return tenant_id

    return check


# ============================================================
# API Routes
# ============================================================

# Bundle display info (matches landing page / product_dashboard)
BUNDLE_DISPLAY_INFO = {
    "callagent_starter": {"name": "CallAgent", "tagline": "AI Voice Receptionist", "color": "blue", "icon": "phone"},
    "callagent_pro": {"name": "CallAgent Pro", "tagline": "Advanced Voice Receptionist", "color": "blue", "icon": "phone"},
    "callagent_enterprise": {"name": "CallAgent Enterprise", "tagline": "Enterprise Voice Platform", "color": "blue", "icon": "phone"},
    "jarvis_personal": {"name": "Jarvis", "tagline": "AI Chief of Staff", "color": "amber", "icon": "brain"},
    "jarvis_professional": {"name": "Jarvis Pro", "tagline": "Professional AI Assistant", "color": "amber", "icon": "brain"},
    "jarvis_enterprise": {"name": "Jarvis Enterprise", "tagline": "Enterprise AI Chief of Staff", "color": "amber", "icon": "brain"},
    "tutor_free": {"name": "Language Tutor", "tagline": "AI Language Coach", "color": "purple", "icon": "book"},
    "tutor_pro": {"name": "Language Tutor Pro", "tagline": "Advanced Language Coach", "color": "purple", "icon": "book"},
    "tutor_family": {"name": "Language Tutor Family", "tagline": "Family Language Learning", "color": "purple", "icon": "book"},
    "hvac_starter": {"name": "HVAC Specialist", "tagline": "Vertical Receptionist", "color": "green", "icon": "wrench"},
    "hvac_pro": {"name": "HVAC Specialist Pro", "tagline": "Advanced HVAC Receptionist", "color": "green", "icon": "wrench"},
    "receptionist_starter": {"name": "Receptionist", "tagline": "Generic Voice Receptionist", "color": "gray", "icon": "phone"},
    "receptionist_pro": {"name": "Receptionist Pro", "tagline": "Advanced Generic Receptionist", "color": "gray", "icon": "phone"},
}


@app.get("/api/v1/entitlements/me")
async def get_my_entitlements(
    request: Request,
    tenant_id: str = Depends(get_current_tenant),
):
    """Get current tenant's capabilities and products."""
    entitlement_service: EntitlementService = request.app.state.entitlement_service

    entitlements = entitlement_service.get_entitlements(tenant_id)
    active_caps = entitlements.get_active_capabilities()
    capabilities = [c.value for c in active_caps]

    products = []
    for bundle_enum, bundle_caps in PRODUCT_BUNDLES.items():
        resolved_caps = resolve_capabilities(set(bundle_caps))
        if resolved_caps.issubset(set(active_caps)):
            display = BUNDLE_DISPLAY_INFO.get(
                bundle_enum.value,
                {
                    "name": bundle_enum.value.replace("_", " ").title(),
                    "tagline": "Product",
                    "color": "gray",
                    "icon": "box",
                },
            )
            products.append(
                {
                    "id": bundle_enum.value,
                    "name": display["name"],
                    "tagline": display["tagline"],
                    "color": display["color"],
                    "icon": display["icon"],
                }
            )

    return {
        "tenant_id": tenant_id,
        "capabilities": capabilities,
        "products": products,
        "capability_count": len(capabilities),
    }


@app.get("/api/v1/entitlements/check/{capability}")
async def check_capability(
    capability: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant),
):
    """Check if tenant has a specific capability."""
    entitlement_service: EntitlementService = request.app.state.entitlement_service
    try:
        cap = Capability(capability)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown capability: {capability}")
    has_cap = entitlement_service.check_capability(tenant_id, cap)
    return {"tenant_id": tenant_id, "capability": capability, "enabled": has_cap}


@app.post("/api/v1/admin/entitlements/grant")
async def grant_capability(
    request: Request,
    tenant_id: str,
    capability: str,
    current_tenant: str = Depends(get_current_tenant),
):
    """Grant capability to tenant (admin only)."""
    # In production, check admin role
    entitlement_service: EntitlementService = request.app.state.entitlement_service
    try:
        cap = Capability(capability)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    success = entitlement_service.grant_capability(tenant_id, cap)
    return {"success": success, "tenant_id": tenant_id, "capability": capability}


@app.post("/api/v1/admin/entitlements/revoke")
async def revoke_capability(
    request: Request,
    tenant_id: str,
    capability: str,
    current_tenant: str = Depends(get_current_tenant),
):
    """Revoke capability from tenant (admin only)."""
    entitlement_service: EntitlementService = request.app.state.entitlement_service
    try:
        cap = Capability(capability)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    success = entitlement_service.revoke_capability(tenant_id, cap)
    return {"success": success, "tenant_id": tenant_id, "capability": capability}


# ============================================================
# Product-Specific API Routes (Capability-Gated)
# ============================================================


@app.get("/api/v1/callagent/calls")
async def list_calls(
    request: Request,
    tenant_id: str = Depends(require_capability(Capability.COMM_VOICE)),
):
    """List calls - requires communication.voice capability."""
    return {"tenant_id": tenant_id, "calls": [], "total": 0, "page": 1, "page_size": 20}


@app.post("/api/v1/callagent/calls/outbound")
async def make_call(
    request: Request,
    tenant_id: str = Depends(require_capability(Capability.COMM_VOICE)),
):
    """Make outbound call - requires communication.voice capability."""
    body = await request.json()
    to_number = body.get("to_number", "")
    return {"success": True, "call_sid": "CA_mock_123", "to_number": to_number, "status": "queued"}


@app.get("/api/v1/tutor/curriculum")
async def get_curriculum(
    request: Request,
    tenant_id: str = Depends(require_capability(Capability.VERT_TUTOR)),
):
    """Get curriculum - requires vertical.tutor capability."""
    return {
        "tenant_id": tenant_id,
        "languages": [
            {"code": "es", "name": "Spanish", "levels": ["A1", "A2", "B1", "B2", "C1", "C2"]},
            {"code": "fr", "name": "French", "levels": ["A1", "A2", "B1", "B2", "C1", "C2"]},
            {"code": "de", "name": "German", "levels": ["A1", "A2", "B1", "B2", "C1", "C2"]},
            {"code": "en", "name": "English", "levels": ["A1", "A2", "B1", "B2", "C1", "C2"]},
        ],
        "total_lessons": 30,
        "featured": ["Spanish A1", "English A1 (Child)", "French A1"],
    }


@app.get("/api/v1/tutor/progress")
async def get_progress(
    request: Request,
    tenant_id: str = Depends(require_capability(Capability.VERT_TUTOR)),
):
    """Get learner progress - requires vertical.tutor capability."""
    return {
        "tenant_id": tenant_id,
        "streak_days": 7,
        "total_xp": 1250,
        "lessons_completed": 12,
        "current_level": "A2",
        "weak_areas": ["past_tense", "pronunciation"],
        "recent_activity": [
            {"date": "2026-11-16", "lesson": "Spanish A1-5", "score": 85},
            {"date": "2026-11-15", "lesson": "Spanish A1-4", "score": 92},
        ],
    }


@app.get("/api/v1/jarvis/email")
async def get_emails(
    request: Request,
    tenant_id: str = Depends(require_capability(Capability.INT_EMAIL_PROVIDER)),
):
    """Get emails - requires integration.email_provider capability."""
    return {
        "tenant_id": tenant_id,
        "emails": [
            {"id": "1", "subject": "Meeting tomorrow", "from": "boss@company.com", "snippet": "Don't forget..."},
            {"id": "2", "subject": "Invoice #1234", "from": "billing@vendor.com", "snippet": "Please review..."},
        ],
        "unread_count": 5,
    }


@app.get("/api/v1/jarvis/calendar")
async def get_calendar(
    request: Request,
    tenant_id: str = Depends(require_capability(Capability.INT_CALENDAR)),
):
    """Get calendar - requires integration.calendar capability."""
    return {
        "tenant_id": tenant_id,
        "events": [
            {"id": "1", "title": "Team standup", "start": "2026-11-18T09:00:00", "end": "2026-11-18T09:30:00"},
            {"id": "2", "title": "Client call", "start": "2026-11-18T14:00:00", "end": "2026-11-18T15:00:00"},
        ],
        "today_count": 3,
    }


# ============================================================
# Frontend Routes
# ============================================================


@app.get("/landing", response_class=HTMLResponse)
async def landing_page():
    """Public landing page - no auth required."""
    landing_file = os.path.join(STATIC_DIR, "landing_page.html")
    if os.path.exists(landing_file):
        return FileResponse(landing_file)
    return HTMLResponse("<h1>Landing page not found</h1>", status_code=404)


@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/app", response_class=HTMLResponse)
async def dashboard(request: Request, tenant_id: str = Depends(get_current_tenant)):
    """Product dashboard - requires authentication."""
    dashboard_file = os.path.join(STATIC_DIR, "product_dashboard.html")
    if os.path.exists(dashboard_file):
        return FileResponse(dashboard_file)
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root redirects to landing page."""
    return await landing_page()


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "ai-assistant",
        "version": VERSION,
        "capabilities": len(Capability),
        "products": len(PRODUCT_BUNDLES),
    }


# ============================================================
# Run
# ============================================================
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
