"""Model Router API - Universal model catalog and routing."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.model_router import (
    get_model_registry,
    Modality,
    Provider,
)

router = APIRouter(prefix="/model-router", tags=["model-router"])


class RouteRequest(BaseModel):
    task: str
    modality: str | None = None
    max_cost: float | None = None
    min_quality: int = 1
    prefer_free: bool = False
    provider: str | None = None


class SelectModelRequest(BaseModel):
    model_id: str


class CustomModelRequest(BaseModel):
    model_id: str
    display_name: str
    modality: str
    provider: str
    description: str
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_vision: bool = False
    context_window: int = 128000
    max_output_tokens: int = 4096
    tags: list[str] = []


@router.get("/catalog")
async def list_catalog(
    modality: str | None = Query(None, description="Filter by modality"),
    provider: str | None = Query(None, description="Filter by provider"),
    free_only: bool = Query(False, description="Free models only"),
):
    """List all available models in catalog."""
    reg = get_model_registry()

    modality_filter = Modality(modality) if modality else None
    provider_filter = Provider(provider) if provider else None

    models = reg.list_models(modality=modality_filter, provider=provider_filter)

    if free_only:
        models = [m for m in models if m.input_cost_per_1k == 0 and m.output_cost_per_1k == 0]

    return {
        "models": [
            {
                "model_id": m.model_id,
                "name": m.display_name,
                "modality": m.modality.value,
                "provider": m.provider.value,
                "description": m.description,
                "cost_per_1m_tokens": m.cost_per_1m_tokens_usd,
                "cost_per_generation": m.cost_per_generation_usd,
                "quality_rating": m.quality_rating,
                "speed_rating": m.speed_rating,
                "free_tier": m.free_tier,
                "tags": m.tags,
                "max_tokens": m.max_tokens,
                "context_window": m.context_window,
            }
            for m in models if not m.deprecated
        ]
    }


@router.get("/modalities")
async def list_modalities():
    """List available modalities."""
    return {"modalities": [m.value for m in Modality]}


@router.get("/providers")
async def list_providers():
    """List available providers."""
    return {"providers": [p.value for p in Provider]}


@router.get("/search")
async def search_models(q: str = Query("", description="Search query")):
    """Search models by name, description, or tags."""
    reg = get_model_registry()
    all_models = reg.list_models()
    q_lower = q.lower()
    results = [
        m for m in all_models
        if not m.deprecated and (
            q_lower in m.display_name.lower() or
            q_lower in m.description.lower() or
            any(q_lower in tag for tag in m.tags)
        )
    ]
    return {"models": [
        {
            "model_id": m.model_id,
            "name": m.display_name,
            "modality": m.modality.value,
            "provider": m.provider.value,
            "description": m.description,
            "cost_per_1m_tokens": m.cost_per_1m_tokens_usd,
            "cost_per_generation": m.cost_per_generation_usd,
            "quality_rating": m.quality_rating,
            "speed_rating": m.speed_rating,
            "free_tier": m.free_tier,
            "tags": m.tags,
            "max_tokens": m.max_tokens,
            "context_window": m.context_window,
        }
        for m in results
    ]}


@router.get("/by-modality/{modality}")
async def get_by_modality(modality: str):
    """Get models for a specific modality."""
    reg = get_model_registry()
    try:
        modality_enum = Modality(modality)
    except ValueError:
        raise HTTPException(400, f"Invalid modality: {modality}")

    models = reg.list_models(modality=modality_enum)
    return {"models": [
        {
            "model_id": m.model_id,
            "name": m.display_name,
            "modality": m.modality.value,
            "provider": m.provider.value,
            "description": m.description,
            "cost_per_1m_tokens": m.cost_per_1m_tokens_usd,
            "cost_per_generation": m.cost_per_generation_usd,
            "quality_rating": m.quality_rating,
            "speed_rating": m.speed_rating,
            "free_tier": m.free_tier,
            "tags": m.tags,
            "max_tokens": m.max_tokens,
            "context_window": m.context_window,
        }
        for m in models if not m.deprecated
    ]}


@router.post("/route")
async def route_task(request: RouteRequest):
    """Find best model for a task."""
    reg = get_model_registry()
    reg.ensure_initialized()

    modality = Modality(request.modality) if request.modality else None
    provider = Provider(request.provider) if request.provider else None

    # If no modality specified, infer from task
    modality_hint = request.modality
    if not modality_hint:
        task_lower = request.task.lower()
        if any(k in task_lower for k in ["video", "movie", "animate"]):
            modality_hint = "video"
        elif any(k in task_lower for k in ["music", "song", "compose"]):
            modality_hint = "music"
        elif any(k in task_lower for k in ["audio", "speech", "speak", "tts", "say"]):
            modality_hint = "audio"
        elif any(k in task_lower for k in ["code", "program", "function", "script"]):
            modality_hint = "code"
        elif any(k in task_lower for k in ["image", "picture", "photo", "draw", "screenshot", "see", "look"]):
            modality_hint = "vision"
        elif any(k in task_lower for k in ["generate", "draw", "create", "make"]):
            modality_hint = "image"
        else:
            modality_hint = "text"

    modality_enum = Modality(modality_hint) if modality_hint else None
    provider_enum = Provider(request.provider) if request.provider else None

    # Map max_cost (per-1M) to max_cost_per_1k (per-1k) for find_best
    max_cost_per_1k = request.max_cost / 1000 if request.max_cost else None

    best = reg.find_best(
        modality=modality_enum,
        provider=provider_enum,
        max_cost_per_1k=max_cost_per_1k,
        min_context=0,
        require_tools=False,
        require_vision=False,
    )

    if not best:
        raise HTTPException(404, "No suitable model found for this task")

    return {
        "model_id": best.model_id,
        "name": best.display_name,
        "modality": best.modality.value,
        "provider": best.provider.value,
        "description": best.description,
        "cost_per_1m_tokens": best.cost_per_1m_tokens_usd,
        "cost_per_generation": best.cost_per_generation_usd,
        "quality_rating": best.quality_rating,
        "speed_rating": best.speed_rating,
        "free_tier": best.free_tier,
        "reasoning": f"Selected for {request.task[:100]}...",
    }


@router.get("/by-provider/{provider}")
async def get_by_provider(provider: str):
    reg = get_model_registry()
    try:
        provider_enum = Provider(provider)
    except ValueError:
        raise HTTPException(400, f"Invalid provider: {provider}")

    models = reg.list_models(provider=provider_enum)
    return {"models": [
        {
            "model_id": m.model_id,
            "name": m.display_name,
            "modality": m.modality.value,
            "provider": m.provider.value,
            "description": m.description,
            "cost_per_1m_tokens": m.cost_per_1m_tokens_usd,
            "cost_per_generation": m.cost_per_generation_usd,
            "quality_rating": m.quality_rating,
            "speed_rating": m.speed_rating,
            "free_tier": m.free_tier,
            "tags": m.tags,
            "max_tokens": m.max_tokens,
            "context_window": m.context_window,
        }
        for m in models if not m.deprecated
    ]}


@router.post("/custom")
async def add_custom_model(request: dict):
    """Add a custom model to catalog (admin)."""
    from shared.model_catalog import ModelCapability
    reg = get_model_registry()

    try:
        cap = ModelCapability(
            model_id=request["model_id"],
            display_name=request["display_name"],
            provider=Provider(request["provider"]),
            modality=Modality(request["modality"]),
            context_window=request.get("context_window", 128000),
            max_output_tokens=request.get("max_output_tokens", 4096),
            supports_streaming=request.get("supports_streaming", True),
            supports_tools=request.get("supports_tools", False),
            supports_vision=request.get("supports_vision", False),
            input_cost_per_1k=request.get("input_cost_per_1k", 0.0),
            output_cost_per_1k=request.get("output_cost_per_1k", 0.0),
            description=request.get("description", ""),
            is_custom=True,
        )
        reg.add_custom_model(cap)
        return {"status": "added", "model_id": cap.model_id}
    except Exception as e:
        raise HTTPException(400, f"Invalid model: {e}")