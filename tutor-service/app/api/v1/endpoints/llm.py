"""
LLM Configuration API - User BYOK keys, model selection, admin tier management
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_active_user, get_current_admin_user
from app.models.user import User
from app.services.tutor_llm_service import (
    get_tutor_llm_service,
    TutorLLMService,
    UserLLMConfig,
    AdminModelConfig,
    ModelAccessTier,
    LLMTaskType,
)

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class APIKeyRequest(BaseModel):
    provider: str = Field(..., pattern="^(openai|anthropic|google|openrouter|xai)$")
    api_key: SecretStr


class CustomEndpointRequest(BaseModel):
    provider_id: str = Field(..., min_length=1, max_length=50)
    base_url: str = Field(..., pattern=r"^https?://")
    api_key: SecretStr


class AccessTierRequest(BaseModel):
    tier: ModelAccessTier


class ModelSelectionRequest(BaseModel):
    task_type: LLMTaskType
    preferred_model: Optional[str] = None


class ModelSelectionResponse(BaseModel):
    selected_model: str
    available_models: List[str]
    user_tier: str
    reason: str


class UserLLMConfigResponse(BaseModel):
    user_id: int
    access_tier: str
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None
    cost_limit_usd_per_month: str
    total_cost_usd: str
    total_tokens_used: int
    has_keys: dict[str, bool]
    custom_endpoints: List[str]


class AdminModelConfigResponse(BaseModel):
    free_models: List[str]
    standard_models: List[str]
    premium_models: List[str]
    task_models: dict
    tier_cost_limits: dict


class ProvidersResponse(BaseModel):
    providers: List[dict]
    user_options: dict


class UsageStatsResponse(BaseModel):
    total_tokens_used: int
    total_cost_usd: str
    cost_limit_usd: str
    percentage_used: float
    last_reset: str


# =============================================================================
# USER ENDPOINTS
# =============================================================================

@router.get("/config", response_model=UserLLMConfigResponse)
async def get_llm_config(
    current_user: User = Depends(get_current_active_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Get current user's LLM configuration"""
    config = await llm_service.get_user_config(current_user.id)
    
    return UserLLMConfigResponse(
        user_id=config.user_id,
        access_tier=config.access_tier.value,
        preferred_provider=config.preferred_provider,
        preferred_model=config.preferred_model,
        cost_limit_usd_per_month=str(config.cost_limit_usd_per_month),
        total_cost_usd=str(config.total_cost_usd),
        total_tokens_used=config.total_tokens_used,
        has_keys={
            "openai": bool(config.openai_key),
            "anthropic": bool(config.anthropic_key),
            "google": bool(config.google_key),
            "openrouter": bool(config.openrouter_key),
            "xai": bool(config.xai_key),
        },
        custom_endpoints=list(config.custom_endpoints.keys()),
    )


@router.post("/config/api-key")
async def set_user_api_key(
    request: APIKeyRequest,
    current_user: User = Depends(get_current_active_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Set user's BYOK API key for a provider"""
    await llm_service.set_user_api_key(current_user.id, request.provider, request.api_key.get_secret_value())
    return {"status": "success", "message": f"API key for {request.provider} set successfully"}


@router.delete("/config/api-key/{provider}")
async def delete_user_api_key(
    provider: str,
    current_user: User = Depends(get_current_active_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Remove user's BYOK API key for a provider"""
    config = await llm_service.get_user_config(current_user.id)
    
    if provider == "openai":
        config.openai_key = None
    elif provider == "anthropic":
        config.anthropic_key = None
    elif provider == "google":
        config.google_key = None
    elif provider == "openrouter":
        config.openrouter_key = None
    elif provider == "xai":
        config.xai_key = None
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    await llm_service.update_user_config(current_user.id, config)
    return {"status": "success", "message": f"API key for {provider} removed"}


@router.post("/config/custom-endpoint")
async def set_custom_endpoint(
    request: CustomEndpointRequest,
    current_user: User = Depends(get_current_active_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Set user's custom endpoint (for self-hosted/local models)"""
    await llm_service.set_user_custom_endpoint(
        current_user.id, 
        request.provider_id, 
        request.base_url, 
        request.api_key.get_secret_value()
    )
    return {"status": "success", "message": f"Custom endpoint {request.provider_id} set successfully"}


@router.delete("/config/custom-endpoint/{provider_id}")
async def delete_custom_endpoint(
    provider_id: str,
    current_user: User = Depends(get_current_active_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Remove user's custom endpoint"""
    config = await llm_service.get_user_config(current_user.id)
    if provider_id in config.custom_endpoints:
        del config.custom_endpoints[provider_id]
        await llm_service.update_user_config(current_user.id, config)
    return {"status": "success", "message": f"Custom endpoint {provider_id} removed"}


@router.get("/models/available", response_model=ModelSelectionResponse)
async def get_available_models(
    task_type: Optional[LLMTaskType] = Query(None),
    current_user: User = Depends(get_current_active_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Get available models for user, optionally filtered by task"""
    config = await llm_service.get_user_config(current_user.id)
    available = llm_service.get_available_models(current_user.id)
    
    selected = None
    reason = "Available models for your tier"
    
    if task_type:
        selected = llm_service.select_model_for_task(task_type, current_user.id)
        reason = f"Recommended for {task_type.value} based on your {config.access_tier.value} tier"
    
    return ModelSelectionResponse(
        selected_model=selected or available[0] if available else "none",
        available_models=available,
        user_tier=config.access_tier.value,
        reason=reason,
    )


@router.post("/models/select", response_model=ModelSelectionResponse)
async def select_model_for_task(
    request: ModelSelectionRequest,
    current_user: User = Depends(get_current_active_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Select best model for a task"""
    config = await llm_service.get_user_config(current_user.id)
    available = llm_service.get_available_models(current_user.id)
    selected = llm_service.select_model_for_task(
        request.task_type, 
        current_user.id, 
        request.preferred_model
    )
    
    return ModelSelectionResponse(
        selected_model=selected,
        available_models=available,
        user_tier=config.access_tier.value,
        reason=f"Selected for {request.task_type.value} with {config.access_tier.value} tier access",
    )


@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    current_user: User = Depends(get_current_active_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Get user's LLM usage statistics"""
    config = await llm_service.get_user_config(current_user.id)
    limit = float(config.cost_limit_usd_per_month)
    used = float(config.total_cost_usd)
    
    return UsageStatsResponse(
        total_tokens_used=config.total_tokens_used,
        total_cost_usd=str(config.total_cost_usd),
        cost_limit_usd=str(config.cost_limit_usd_per_month),
        percentage_used=(used / limit * 100) if limit > 0 else 0,
        last_reset=config.last_reset,
    )


@router.get("/providers", response_model=ProvidersResponse)
async def get_providers(
    current_user: User = Depends(get_current_active_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Get available providers and user's model options"""
    providers = llm_service.get_available_providers()
    user_options = llm_service.get_user_model_options(current_user.id)
    
    return ProvidersResponse(
        providers=providers,
        user_options=user_options,
    )


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.get("/admin/models", response_model=AdminModelConfigResponse)
async def get_admin_models(
    current_user: User = Depends(get_current_admin_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Get admin model configuration"""
    admin_config = llm_service.get_admin_model_config()
    
    return AdminModelConfigResponse(
        free_models=admin_config.free_models,
        standard_models=admin_config.standard_models,
        premium_models=admin_config.premium_models,
        task_models={
            task.value: {tier.value: model for tier, model in models.items()}
            for task, models in admin_config.task_models.items()
        },
        tier_cost_limits={tier.value: str(limit) for tier, limit in admin_config.tier_cost_limits.items()},
    )


@router.post("/admin/models/free")
async def add_free_model(
    model_id: str,
    current_user: User = Depends(get_current_admin_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Add model to free tier"""
    llm_service.add_free_model(model_id)
    return {"status": "success", "message": f"Added {model_id} to free tier"}


@router.post("/admin/models/standard")
async def add_standard_model(
    model_id: str,
    current_user: User = Depends(get_current_admin_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Add model to standard tier"""
    llm_service.add_standard_model(model_id)
    return {"status": "success", "message": f"Added {model_id} to standard tier"}


@router.post("/admin/models/premium")
async def add_premium_model(
    model_id: str,
    current_user: User = Depends(get_current_admin_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Add model to premium tier"""
    llm_service.add_premium_model(model_id)
    return {"status": "success", "message": f"Added {model_id} to premium tier"}


@router.post("/admin/models/task")
async def set_task_model(
    task_type: LLMTaskType,
    tier: ModelAccessTier,
    model_id: str,
    current_user: User = Depends(get_current_admin_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Set recommended model for task type and tier"""
    llm_service.set_task_model(task_type, tier, model_id)
    return {"status": "success", "message": f"Set {model_id} for {task_type.value} ({tier.value})"}


@router.post("/admin/users/{user_id}/tier")
async def set_user_tier(
    user_id: int,
    request: AccessTierRequest,
    current_user: User = Depends(get_current_admin_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Set user's access tier (admin only)"""
    await llm_service.set_user_access_tier(user_id, request.tier)
    return {"status": "success", "message": f"Set user {user_id} to {request.tier.value} tier"}


# =============================================================================
# COMPLETION ENDPOINTS (for testing)
# =============================================================================

class CompletionRequest(BaseModel):
    prompt: str
    system: Optional[str] = None
    task_type: LLMTaskType = LLMTaskType.CHAT
    model: Optional[str] = None
    json_mode: bool = False
    temperature: float = 0.7
    max_tokens: Optional[int] = None


class CompletionResponse(BaseModel):
    success: bool
    data: Optional[str] = None
    error: Optional[str] = None
    model_used: str
    tokens_used: int
    cost_usd: float


@router.post("/complete", response_model=CompletionResponse)
async def complete(
    request: CompletionRequest,
    current_user: User = Depends(get_current_active_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Complete a prompt (for testing)"""
    result = await llm_service.complete(
        user_id=current_user.id,
        prompt=request.prompt,
        system=request.system,
        task_type=request.task_type,
        model=request.model,
        json_mode=request.json_mode,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )
    return CompletionResponse(**result)


class JSONCompletionRequest(BaseModel):
    prompt: str
    schema: Optional[dict] = None
    task_type: LLMTaskType = LLMTaskType.CONTENT_CREATION
    model: Optional[str] = None


@router.post("/complete/json", response_model=CompletionResponse)
async def complete_json(
    request: JSONCompletionRequest,
    current_user: User = Depends(get_current_active_user),
    llm_service: TutorLLMService = Depends(get_tutor_llm_service),
):
    """Complete a prompt expecting JSON response"""
    result = await llm_service.call_json(
        user_id=current_user.id,
        prompt=request.prompt,
        schema=request.schema,
        task_type=request.task_type,
        model=request.model,
    )
    return CompletionResponse(**result)