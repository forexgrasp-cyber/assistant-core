"""
LLM Model Management API endpoints.

Provides:
- Model listing with filters
- Per-tenant overrides (enable/disable, custom pricing, API keys)
- Global defaults management
- Cost estimation
- Provider configuration
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from decimal import Decimal

from ...core.config import get_settings
from ...core.security import get_current_active_user
from ...services.llm_model_service import (
    LLMModelRegistry,
    get_llm_model_registry,
    ProviderType,
    ModelCapability,
    ModelTier,
    ModelPricing,
    ModelLimits,
    LLMModelOverride,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/llm", tags=["LLM Models"])

settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────────────


class ModelPricingRequest(BaseModel):
    input_per_1m: Decimal = Field(..., ge=0)
    output_per_1m: Decimal = Field(..., ge=0)
    cached_input_per_1m: Optional[Decimal] = Field(None, ge=0)
    currency: str = "USD"


class ModelLimitsRequest(BaseModel):
    max_context_tokens: int = Field(..., gt=0)
    max_output_tokens: int = Field(..., gt=0)
    max_input_tokens: Optional[int] = Field(None, gt=0)


class ModelOverrideRequest(BaseModel):
    enabled: bool = True
    custom_pricing: Optional[ModelPricingRequest] = None
    custom_limits: Optional[ModelLimitsRequest] = None
    custom_tier: Optional[ModelTier] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    extra_headers: dict[str, str] = Field(default_factory=dict)
    max_monthly_cost_usd: Optional[float] = Field(None, ge=0)


class GlobalDefaultRequest(BaseModel):
    model_id: str


class CostEstimateRequest(BaseModel):
    model_id: str
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)
    cached_tokens: int = Field(0, ge=0)


class ProviderConfigRequest(BaseModel):
    name: str
    api_base: str
    auth_type: str = "bearer"
    auth_header: str = "Authorization"
    api_key_env: str = ""
    supports_streaming: bool = True
    supports_function_calling: bool = True
    rate_limit_rpm: int = 60
    rate_limit_tpm: int = 100000
    webhook_secret_env: str = ""
    extra_headers: dict[str, str] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Dependency
# ─────────────────────────────────────────────────────────────────────────────


async def get_registry(current_user=Depends(get_current_active_user)) -> LLMModelRegistry:
    return get_llm_model_registry(tenant_id=current_user.client_id)


# ─────────────────────────────────────────────────────────────────────────────
# Model Listing
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/models")
async def list_models(
    provider: Optional[ProviderType] = None,
    tier: Optional[ModelTier] = None,
    capability: Optional[ModelCapability] = None,
    include_deprecated: bool = False,
    task_type: Optional[str] = None,
    budget_tier: Optional[ModelTier] = None,
    registry: LLMModelRegistry = Depends(get_registry),
):
    """List available models with filters."""
    if task_type:
        models = registry.get_models_for_task(task_type, tenant_id=registry.tenant_id, budget_tier=budget_tier)
    else:
        models = registry.list_models(
            provider=provider,
            tier=tier,
            capability=capability,
            include_deprecated=include_deprecated,
            tenant_id=registry.tenant_id,
        )

    return [
        {
            "id": m.id,
            "provider": m.provider.value,
            "name": m.name,
            "version": m.version,
            "tier": m.tier.value,
            "capabilities": [c.value for c in m.capabilities],
            "pricing": {
                "input_per_1m": str(m.pricing.input_per_1m),
                "output_per_1m": str(m.pricing.output_per_1m),
                "cached_input_per_1m": str(m.pricing.cached_input_per_1m) if m.pricing.cached_input_per_1m else None,
                "currency": m.pricing.currency,
            },
            "limits": {
                "max_context_tokens": m.limits.max_context_tokens,
                "max_output_tokens": m.limits.max_output_tokens,
                "max_input_tokens": m.limits.max_input_tokens,
            },
            "description": m.description,
            "release_date": m.release_date,
            "deprecated": m.deprecated,
            "deprecated_at": m.deprecated_at,
            "replacement_model_id": m.replacement_model_id,
        }
        for m in models
    ]


@router.get("/models/{model_id}")
async def get_model(
    model_id: str,
    registry: LLMModelRegistry = Depends(get_registry),
):
    """Get model details with tenant-specific overrides."""
    model = registry.get_effective_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Get override info if exists
    override_info = None
    if registry.tenant_id in registry._models.get(model_id, LLMModel(id="")).tenant_overrides:
        override = registry._models[model_id].tenant_overrides[registry.tenant_id]
        override_info = {
            "enabled": override.enabled,
            "has_custom_pricing": override.custom_pricing is not None,
            "has_custom_limits": override.custom_limits is not None,
            "has_custom_tier": override.custom_tier is not None,
            "has_api_key": override.api_key is not None,
            "has_api_base": override.api_base is not None,
            "max_monthly_cost_usd": override.max_monthly_cost_usd,
            "created_at": override.created_at,
            "updated_at": override.updated_at,
        }

    return {
        "id": model.id,
        "provider": model.provider.value,
        "name": model.name,
        "version": model.version,
        "tier": model.tier.value,
        "capabilities": [c.value for c in model.capabilities],
        "pricing": {
            "input_per_1m": str(model.pricing.input_per_1m),
            "output_per_1m": str(model.pricing.output_per_1m),
            "cached_input_per_1m": str(model.pricing.cached_input_per_1m) if model.pricing.cached_input_per_1m else None,
            "currency": model.pricing.currency,
        },
        "limits": {
            "max_context_tokens": model.limits.max_context_tokens,
            "max_output_tokens": model.limits.max_output_tokens,
            "max_input_tokens": model.limits.max_input_tokens,
        },
        "description": model.description,
        "release_date": model.release_date,
        "deprecated": model.deprecated,
        "deprecated_at": model.deprecated_at,
        "replacement_model_id": model.replacement_model_id,
        "override": override_info,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tenant Overrides
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/overrides")
async def get_overrides(
    registry: LLMModelRegistry = Depends(get_registry),
):
    """Get all model overrides for current tenant."""
    overrides = registry.get_tenant_overrides(registry.tenant_id)
    return {
        model_id: {
            "model_id": model_id,
            "enabled": o.enabled,
            "custom_pricing": {
                "input_per_1m": str(o.custom_pricing.input_per_1m),
                "output_per_1m": str(o.custom_pricing.output_per_1m),
            } if o.custom_pricing else None,
            "custom_limits": {
                "max_context_tokens": o.custom_limits.max_context_tokens,
                "max_output_tokens": o.custom_limits.max_output_tokens,
            } if o.custom_limits else None,
            "custom_tier": o.custom_tier.value if o.custom_tier else None,
            "has_api_key": o.api_key is not None,
            "api_base": o.api_base,
            "extra_headers": o.extra_headers,
            "max_monthly_cost_usd": o.max_monthly_cost_usd,
            "created_at": o.created_at,
            "updated_at": o.updated_at,
        }
        for model_id, o in overrides.items()
    }


@router.post("/models/{model_id}/override")
async def set_model_override(
    model_id: str,
    override: ModelOverrideRequest,
    registry: LLMModelRegistry = Depends(get_registry),
):
    """Set or update model override for current tenant."""
    if not registry.get_model(model_id):
        raise HTTPException(status_code=404, detail="Model not found")

    custom_pricing = None
    if override.custom_pricing:
        custom_pricing = ModelPricing(
            input_per_1m=override.custom_pricing.input_per_1m,
            output_per_1m=override.custom_pricing.output_per_1m,
            cached_input_per_1m=override.custom_pricing.cached_input_per_1m,
            currency=override.custom_pricing.currency,
        )

    custom_limits = None
    if override.custom_limits:
        custom_limits = ModelLimits(
            max_context_tokens=override.custom_limits.max_context_tokens,
            max_output_tokens=override.custom_limits.max_output_tokens,
            max_input_tokens=override.custom_limits.max_input_tokens,
        )

    success = registry.set_tenant_override(
        tenant_id=registry.tenant_id,
        model_id=model_id,
        enabled=override.enabled,
        custom_pricing=custom_pricing,
        custom_limits=custom_limits,
        custom_tier=override.custom_tier,
        api_key=override.api_key,
        api_base=override.api_base,
        extra_headers=override.extra_headers,
        max_monthly_cost_usd=override.max_monthly_cost_usd,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to set override")

    return {"message": "Override set successfully"}


@router.delete("/models/{model_id}/override")
async def remove_model_override(
    model_id: str,
    registry: LLMModelRegistry = Depends(get_registry),
):
    """Remove model override (revert to global)."""
    success = registry.remove_tenant_override(registry.tenant_id, model_id)
    if not success:
        raise HTTPException(status_code=404, detail="Override not found")
    return {"message": "Override removed"}


# ─────────────────────────────────────────────────────────────────────────────
# Global Defaults
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/defaults")
async def get_defaults(
    registry: LLMModelRegistry = Depends(get_registry),
):
    """Get global default models per tier."""
    defaults = {}
    for tier, model_id in registry._global_defaults.items():
        model = registry.get_model(model_id)
        if model:
            defaults[tier.value] = {
                "model_id": model_id,
                "name": model.name,
                "provider": model.provider.value,
            }
    return {"defaults": defaults}


@router.post("/defaults/{tier}")
async def set_default_model(
    tier: ModelTier,
    request: GlobalDefaultRequest,
    registry: LLMModelRegistry = Depends(get_registry),
):
    """Set global default model for a tier."""
    success = registry.set_default_model(tier, request.model_id)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": f"Default model for {tier.value} set to {request.model_id}"}


# ─────────────────────────────────────────────────────────────────────────────
# Cost Estimation
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/estimate-cost")
async def estimate_cost(
    request: CostEstimateRequest,
    registry: LLMModelRegistry = Depends(get_registry),
):
    """Estimate cost for a model call."""
    try:
        cost = registry.estimate_cost(
            model_id=request.model_id,
            estimated_input_tokens=request.input_tokens,
            estimated_output_tokens=request.output_tokens,
            tenant_id=registry.tenant_id,
        )
        return {
            "model_id": request.model_id,
            "input_tokens": request.input_tokens,
            "output_tokens": request.output_tokens,
            "cached_tokens": request.cached_tokens,
            "estimated_cost_usd": str(cost),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/estimate-workflow")
async def estimate_workflow_cost(
    model_id: str,
    steps: list[dict],  # [{input_tokens, output_tokens, count}]
    registry: LLMModelRegistry = Depends(get_registry),
):
    """Estimate total cost for a multi-step workflow."""
    total_cost = Decimal("0")
    breakdown = []

    for step in steps:
        count = step.get("count", 1)
        input_tokens = step.get("input_tokens", 0)
        output_tokens = step.get("output_tokens", 0)

        step_cost = registry.estimate_cost(
            model_id=model_id,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            tenant_id=registry.tenant_id,
        )
        total_step_cost = step_cost * count
        total_cost += total_step_cost
        breakdown.append({
            "step": step.get("name", "step"),
            "count": count,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_per_run_usd": str(step_cost),
            "total_cost_usd": str(total_step_cost),
        })

    return {
        "model_id": model_id,
        "total_estimated_cost_usd": str(total_cost),
        "breakdown": breakdown,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Provider Config
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/providers")
async def list_providers(
    registry: LLMModelRegistry = Depends(get_registry),
):
    """List all provider configurations."""
    return {
        provider.value: {
            "name": config.name,
            "api_base": config.api_base,
            "auth_type": config.auth_type,
            "api_key_env": config.api_key_env,
            "supports_streaming": config.supports_streaming,
            "supports_function_calling": config.supports_function_calling,
            "rate_limit_rpm": config.rate_limit_rpm,
            "rate_limit_tpm": config.rate_limit_tpm,
        }
        for provider, config in registry._provider_configs.items()
    }


@router.get("/providers/{provider}")
async def get_provider(
    provider: ProviderType,
    registry: LLMModelRegistry = Depends(get_registry),
):
    """Get provider configuration."""
    config = registry.get_provider_config(provider)
    return {
        "provider": config.provider.value,
        "name": config.name,
        "api_base": config.api_base,
        "auth_type": config.auth_type,
        "auth_header": config.auth_header,
        "api_key_env": config.api_key_env,
        "supports_streaming": config.supports_streaming,
        "supports_function_calling": config.supports_function_calling,
        "rate_limit_rpm": config.rate_limit_rpm,
        "rate_limit_tpm": config.rate_limit_tpm,
        "webhook_secret_env": config.webhook_secret_env,
        "extra_headers": config.extra_headers,
    }


@router.patch("/providers/{provider}")
async def update_provider(
    provider: ProviderType,
    config: ProviderConfigRequest,
    registry: LLMModelRegistry = Depends(get_registry),
):
    """Update provider configuration."""
    from shared.llm.llm_model_registry import ProviderConfig
    provider_config = ProviderConfig(
        provider=provider,
        name=config.name,
        api_base=config.api_base,
        auth_type=config.auth_type,
        auth_header=config.auth_header,
        api_key_env=config.api_key_env,
        supports_streaming=config.supports_streaming,
        supports_function_calling=config.supports_function_calling,
        rate_limit_rpm=config.rate_limit_rpm,
        rate_limit_tpm=config.rate_limit_tpm,
        webhook_secret_env=config.webhook_secret_env,
        extra_headers=config.extra_headers,
    )
    registry.update_provider_config(provider_config)
    return {"message": f"Provider {provider.value} updated"}


# ─────────────────────────────────────────────────────────────────────────────
# Recommendations
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/recommendations/{task_type}")
async def get_recommendations(
    task_type: str,
    budget_tier: Optional[ModelTier] = None,
    registry: LLMModelRegistry = Depends(get_registry),
):
    """Get model recommendations for a task type."""
    models = registry.get_models_for_task(task_type, tenant_id=registry.tenant_id, budget_tier=budget_tier)
    return [
        {
            "id": m.id,
            "name": m.name,
            "provider": m.provider.value,
            "tier": m.tier.value,
            "pricing": {
                "input_per_1m": str(m.pricing.input_per_1m),
                "output_per_1m": str(m.pricing.output_per_1m),
            },
            "description": m.description,
        }
        for m in models[:5]  # Top 5
    ]


import structlog
from decimal import Decimal