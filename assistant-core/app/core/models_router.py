"""Models API Router - UI endpoints for model management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.models import ModelManager, create_model_manager

router = APIRouter(prefix="/models", tags=["models"])

_model_manager: ModelManager | None = None


def set_model_manager(manager: ModelManager):
    global _model_manager
    _model_manager = manager


def get_model_manager() -> ModelManager:
    if _model_manager is None:
        raise HTTPException(503, "Model manager not initialized")
    return _model_manager


class PullRequest(BaseModel):
    name: str


class PullHFRequest(BaseModel):
    repo_id: str
    quantization: str = "Q4_K_M"


class CustomModelRequest(BaseModel):
    name: str
    base_model: str
    system_prompt: str
    temperature: float = 0.7


class SetCurrentRequest(BaseModel):
    name: str


@router.get("/installed")
async def list_installed():
    """List locally installed models."""
    mgr = get_model_manager()
    models = await mgr.list_installed()
    return {"models": [vars(m) for m in models]}


@router.get("/available")
async def list_available():
    """List popular available models from Ollama library."""
    mgr = get_model_manager()
    models = await mgr.list_available()
    return {"models": [vars(m) for m in models]}


@router.get("/current")
async def get_current_model():
    """Get currently selected model."""
    mgr = get_model_manager()
    return {"current": mgr.get_current()}


@router.post("/select")
async def select_model(request: dict):
    """Select current model for new conversations."""
    mgr = get_model_manager()
    name = request.get("name")
    if not name:
        raise HTTPException(400, "Model name required")
    return await mgr.set_current(name)


@router.post("/pull")
async def pull_model(request: PullRequest):
    """Pull a model from Ollama library."""
    mgr = get_model_manager()
    return await mgr.pull_model(request.name)


@router.post("/pull/huggingface")
async def pull_huggingface(request: PullHFRequest):
    """Pull a GGUF model from Hugging Face Hub."""
    mgr = get_model_manager()
    return await mgr.pull_from_huggingface(request.repo_id, request.quantization)


@router.post("/custom")
async def create_custom_model(request: CustomModelRequest):
    """Create a custom model with custom system prompt."""
    mgr = get_model_manager()
    return await mgr.create_custom_model(
        request.name,
        request.base_model,
        request.system_prompt,
        request.temperature,
    )


@router.delete("/{name}")
async def remove_model(name: str):
    """Remove a local model."""
    mgr = get_model_manager()
    return await mgr.remove_model(name)


@router.get("/search")
async def search_models(q: str = Query("", description="Search query")):
    """Search available models."""
    mgr = get_model_manager()
    all_models = await mgr.list_available()
    if not q:
        return {"models": [vars(m) for m in all_models]}
    q_lower = q.lower()
    filtered = [m for m in all_models if q_lower in m.name.lower() or q_lower in m.description.lower()]
    return {"models": [vars(m) for m in filtered]}