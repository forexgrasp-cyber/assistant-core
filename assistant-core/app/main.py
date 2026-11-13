"""Assistant Core - Main Application Entry Point."""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings

# Shared packages
from shared.llm.ollama_adapter import OllamaAdapter
from shared.rag import RAGService
from shared.agent_runtime import ToolRegistry

# Core components
from app.core.agent import create_assistant_agent
from app.core.voice import create_voice_manager
from app.core.rag import create_rag_manager
from app.core.persona import create_persona_manager
from app.core.memory import create_memory_store
from app.core.tools import create_tool_registry
from app.assistants import AssistantRegistry, get_registry, create_assistant, AssistantConfig
from app.multi_tenant import TenantManager, TenantIsolation
from app.billing import StripeBilling, BillingConfig
from app.config import load_config, get_config
from app.core.model_router import initialize_registry

# Routers
from app.modes.personal import router as personal_router
from app.modes.business import router as business_router
from app.voice import setup_voice_webhooks
from app.connectors import get_connector, list_connectors
from app.core.models_router import router as models_router, set_model_manager
from app.core.model_router_api import router as model_router_api

# Settings
class Settings(BaseSettings):
    ollama_host: str = "http://localhost:11437"
    ollama_model: str = "llama3.2:3b"
    embedding_model: str = "all-MiniLM-L6-v2"
    chromadb_path: str = "./data/chromadb"
    embedding_model: str = "all-MiniLM-L6-v2"
    data_dir: str = "./data"
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    elevenlabs_api_key: str | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    app_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


settings = Settings()


# Global state
_ollama = None
_rag_service = None
_tool_registry = None
_voice_manager = None
_persona_manager = None
_tenant_manager = None
_tenant_isolation = None
_stripe_billing = None
_assistant_registry = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ollama, _rag_service, _tool_registry, _voice_manager
    global _persona_manager, _tenant_manager, _tenant_isolation, _stripe_billing, _assistant_registry, _model_manager

    # Load config
    load_config()

    # Create data directories
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.chromadb_path).mkdir(parents=True, exist_ok=True)

    # Initialize shared services
    _ollama = OllamaAdapter(host=settings.ollama_host, model=settings.ollama_model)
    _rag_service = RAGService(persist_dir=settings.chromadb_path, embedding_model=settings.embedding_model)
    _tool_registry = create_tool_registry(settings.data_dir)

    # Initialize core services
    _voice_manager = create_voice_manager(elevenlabs_api_key=settings.elevenlabs_api_key)
    _persona_manager = create_persona_manager(settings.data_dir)
    _tenant_manager = TenantManager()
    _tenant_isolation = TenantIsolation(settings.data_dir)

    # Initialize model manager
    _model_manager = create_model_manager(_ollama, settings.data_dir)
    set_model_manager(_model_manager)

    # Initialize model registry with all providers
    await initialize_registry()

    # Initialize billing
    if settings.stripe_secret_key and settings.stripe_webhook_secret:
        _stripe_billing = StripeBilling(BillingConfig(
            stripe_secret_key=settings.stripe_secret_key,
            stripe_webhook_secret=settings.stripe_webhook_secret,
            success_url=f"{settings.app_url}/billing/success",
            cancel_url=f"{settings.app_url}/billing/cancel",
        ))

    _assistant_registry = get_registry()

    # Initialize assistants from config
    config = get_config()
    for tenant_config in config.get("tenants", []):
        tenant = _tenant_manager.create(type("Tenant", (), tenant_config)())
        for assistant_config in tenant_config.get("assistants", []):
            if assistant_config.get("enabled", True):
                assistant_cfg = AssistantConfig(
                    assistant_id=assistant_config["id"],
                    tenant_id=tenant.id,
                    type=assistant_config["type"],
                    name=assistant_config["name"],
                    vertical=assistant_config.get("vertical"),
                    connectors=assistant_config.get("config", {}).get("connectors", []),
                    persona_name=assistant_config.get("config", {}).get("persona", {}).get("name", "JARVIS"),
                    persona_style=assistant_config.get("config", {}).get("persona", {}).get("style", "professional, concise, proactive"),
                    voice_enabled=assistant_config.get("config", {}).get("voice", {}).get("enabled", True),
                )
                # Would create assistant here in production
                # assistant = await create_assistant(assistant_cfg, _ollama, _rag_service, settings.data_dir)
                # _assistant_registry.register(assistant)

    yield

    # Cleanup


app = FastAPI(
    title="Assistant Core",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(personal_router)
app.include_router(business_router)
app.include_router(models_router)
app.include_router(model_router_api)
setup_voice_webhooks(app)


# Models
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    use_rag: bool = True
    use_tools: bool = True


class ChatResponse(BaseModel):
    response: str
    session_id: str


# Routes
@app.get("/health")
async def health():
    ollama_ok = False
    if _ollama:
        try:
            ollama_ok = await _ollama.health_check()
        except Exception:
            pass

    return {
        "status": "ok",
        "service": "assistant-core",
        "ollama": ollama_ok,
        "model": settings.ollama_model,
        "tenants": len(_tenant_manager._tenants) if _tenant_manager else 0,
    }


@app.get("/config")
async def get_app_config():
    """Get application configuration."""
    return get_config()


@app.get("/tenants")
async def list_tenants():
    """List all tenants."""
    return {"tenants": [vars(t) for t in _tenant_manager.list_all()]}


@app.post("/tenants")
async def create_tenant(request: Request):
    """Create a new tenant."""
    data = await request.json()
    tenant = type("Tenant", (), data)()
    _tenant_manager.create(tenant)
    return {"status": "created", "tenant_id": tenant.id}


@app.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str):
    """Get tenant by ID."""
    tenant = _tenant_manager.get(tenant_id)
    if not tenant:
        return {"error": "Tenant not found"}, 404
    return vars(tenant)


@app.get("/tenants/{tenant_id}/assistants")
async def list_assistants(tenant_id: str):
    """List assistants for a tenant."""
    return {"assistants": [a.get_config() for a in _assistant_registry.list_for_tenant(tenant_id)]}


@app.post("/tenants/{tenant_id}/assistants")
async def create_assistant_instance(tenant_id: str, request: Request):
    """Create a new assistant for a tenant."""
    data = await request.json()
    config = AssistantConfig(
        assistant_id=data.get("assistant_id", f"asst_{uuid.uuid4().hex[:8]}"),
        tenant_id=tenant_id,
        type=data.get("type", "personal"),
        name=data.get("name", "New Assistant"),
        **{k: v for k, v in data.items() if k not in ["assistant_id", "tenant_id", "type", "name"]},
    )
    # Would create actual assistant here
    return {"status": "created", "assistant_id": config.assistant_id}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with default assistant (for testing)."""
    # Would route to appropriate assistant based on context
    return ChatResponse(response="Hello! This is the unified assistant core.", session_id=request.session_id or "test")


@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket for chat."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            await websocket.send_json({"response": f"Echo: {message}"})
    except Exception:
        pass


# Connector routes
@app.get("/connectors")
async def list_connectors_endpoint():
    return {"connectors": list_connectors()}


@app.post("/connectors/{name}/sync")
async def sync_connector(name: str, request: Request):
    """Sync data from a connector."""
    data = await request.json()
    tenant_id = data.get("tenant_id")
    assistant_id = data.get("assistant_id")
    if not tenant_id or not assistant_id:
        return {"error": "tenant_id and assistant_id required"}, 400

    conn = get_connector(name)
    if not conn or not await conn.authenticate():
        return {"error": "Connector not available or not authenticated"}, 400

    items = await conn.fetch_recent(limit=50)
    return {"synced": len(items), "connector": name}


# Billing routes
@app.post("/billing/checkout")
async def create_checkout(request: Request):
    """Create Stripe checkout session."""
    if not _stripe_billing:
        return {"error": "Billing not configured"}, 503

    data = await request.json()
    customer_id = data.get("customer_id")
    tier = data.get("tier", "pro")

    result = _stripe_billing.create_checkout_session(customer_id, tier)
    return result


@app.post("/billing/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook."""
    if not _stripe_billing:
        return {"error": "Billing not configured"}, 503

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = _stripe_billing.handle_webhook(payload, sig_header)
        return {"received": True, "event": event["event"]}
    except ValueError as e:
        return {"error": str(e)}, 400


@app.get("/")
async def root():
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>Assistant Core</title>
    <style>
        body { font-family: system-ui; max-width: 800px; margin: 0 auto; padding: 20px; background: #0d1117; color: #c9d1d9; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin: 20px 0; }
        h1 { color: #6366f1; }
        code { background: #0d1117; padding: 2px 6px; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>🤖 Assistant Core</h1>
    <p>Unified AI Assistant - Personal (JARVIS) + Business (Receptionist)</p>

    <div class="card">
        <h3>Status</h3>
        <p id="status">Loading...</p>
    </div>

    <div class="card">
        <h3>Quick Links</h3>
        <ul>
            <li><a href="/health">Health Check</a></li>
            <li><a href="/config">Configuration</a></li>
            <li><a href="/tenants">Tenants</a></li>
            <li><a href="/connectors">Connectors</a></li>
            <li><a href="/docs">API Docs</a></li>
        </ul>
    </div>

    <script>
        fetch('/health').then(r=>r.json()).then(d=>{
            document.getElementById('status').innerHTML = 
                `Ollama: ${d.ollama ? '✓' : '✗'} | Model: ${d.model} | Tenants: ${d.tenants}`;
        });
    </script>
</body>
</html>
""")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)