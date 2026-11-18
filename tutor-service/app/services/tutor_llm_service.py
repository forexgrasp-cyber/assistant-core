"""
Tutor LLM Service - Unified LLM interface for Language Tutor
Integrates with shared.llm.UnifiedLLMService (free providers built-in), adds:
- User-provided API keys (BYOK) for paid models
- Admin model tier management (free/paid)
- Intelligent model selection by task type
- Cost tracking per user

Free providers from shared (no keys needed):
- OpenCode Zen: mimo-v2.6-flash-free, nemotron-3-ultra-free, big-pickle, nemotron-3.5-lightning-free, space-bunny-free
- OpenRouter free: meta-llama/llama-3.3-70b:free, mistralai/mistral-7b-instruct:free, google/gemma-3-12b-it:free, etc.
- NVIDIA NIM: meta/llama-3.1-70b-instruct, mistralai/mistral-7b-instruct-v0.3, etc.
- Groq: openai/gpt-oss-120b, qwen/qwen3.8-27b, etc.
- Cohere: command-r, command-r-plus
- Cloudflare: @cf/meta/llama-3-8b-instruct, @cf/mistral/mistral-7b-instruct-v0.1
- Local Ollama: llama3.1, mistral, etc. (if running locally)
"""
from __future__ import annotations

import json
import os
import structlog
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, List

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.tutor_memory import TutorMemory
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

log = structlog.get_logger(__name__)

# Import shared LLM infrastructure
try:
    from shared.llm.canonical_ai_service import CanonicalAIService
    from shared.llm.unified_llm_service import (
        _OPENCODE_FREE_MODELS,
        _OPENROUTER_FREE_FALLBACK_MODELS,
        _NVIDIA_FALLBACK_MODELS,
        _GROQ_FALLBACK_MODELS,
        _COHERE_FALLBACK_MODELS,
        _CLOUDFLARE_FALLBACK_MODELS,
    )
    from shared.llm.llm_model_registry import (
        LLMModel, ModelCapability, ModelTier, ProviderType, ModelPricing, ModelLimits
    )
    from shared.llm.provider_registry import PROVIDERS, list_providers
    from shared.llm.facade import call_llm, call_llm_json, get_llm_backend, available_backends
    SHARED_LLM_AVAILABLE = True
    log.info("shared_llm_available", free_providers=[
        "opencode_zen", "openrouter_free", "nvidia_nim", "groq", "cohere", "cloudflare", "ollama_local"
    ])
except ImportError as e:
    SHARED_LLM_AVAILABLE = False
    CanonicalAIService = None
    # Fallback free models from shared
    _OPENCODE_FREE_MODELS = [
        "mimo-v2.6-flash-free", "nemotron-3-ultra-free", "big-pickle",
        "nemotron-3.5-lightning-free", "space-bunny-free"
    ]
    _OPENROUTER_FREE_FALLBACK_MODELS = [
        "meta-llama/llama-3.3-70b:free", "meta-llama/llama-3.1-8b-instruct:free",
        "mistralai/mistral-7b-instruct:free", "google/gemma-3-12b-it:free",
        "microsoft/phi-3-mini-128k-instruct:free", "qwen/qwen-2-7b-instruct:free",
        "deepseek/deepseek-r1:free", "nousresearch/hermes-3-llama-3.1-405b:free"
    ]
    _NVIDIA_FALLBACK_MODELS = [
        "meta/llama-3.1-70b-instruct", "meta/llama-3.2-3b-instruct",
        "mistralai/mistral-7b-instruct-v0.3", "microsoft/phi-3-medium-128k-instruct",
        "qwen/qwen2-7b-instruct", "nvidia/nemotron-3-super-120b-a12b",
        "nvidia/nemotron-3-nano-30b-a3b"
    ]
    _GROQ_FALLBACK_MODELS = [
        "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b", "allam-2-7b"
    ]
    _COHERE_FALLBACK_MODELS = ["command-r", "command-r-plus", "command"]
    _CLOUDFLARE_FALLBACK_MODELS = [
        "@cf/meta/llama-3-8b-instruct", "@cf/meta/llama-3.1-8b-instruct",
        "@cf/mistral/mistral-7b-instruct-v0.1"
    ]
    # Provide fallback PROVIDERS for direct completion
    PROVIDERS = {
        "openai": {"api_style": "openai", "base_url": "https://api.openai.com/v1", "input_per_1m": 2.5, "output_per_1m": 10.0},
        "anthropic": {"api_style": "anthropic", "base_url": "https://api.anthropic.com", "input_per_1m": 3.0, "output_per_1m": 15.0},
        "google": {"api_style": "openai", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "input_per_1m": 1.25, "output_per_1m": 10.0},
        "openrouter": {"api_style": "openai", "base_url": "https://openrouter.ai/api/v1", "input_per_1m": 3.15, "output_per_1m": 15.75},
        "xai": {"api_style": "openai", "base_url": "https://api.x.ai/v1", "input_per_1m": 3.0, "output_per_1m": 15.0},
    }
    def list_providers():
        return [{"id": k, "label": v.get("label", k), "api_style": v["api_style"], "base_url": v["base_url"]} for k, v in PROVIDERS.items()]
    log.warning("shared_llm_not_available", reason=str(e))


class LLMTaskType(str, Enum):
    """Types of LLM tasks for model selection"""
    LESSON_GENERATION = "lesson_generation"
    CONTENT_CREATION = "content_creation"
    GRAMMAR_EXPLANATION = "grammar_explanation"
    CONVERSATION_PRACTICE = "conversation_practice"
    PRONUNCIATION_GUIDANCE = "pronunciation_guidance"
    WRITING_CORRECTION = "writing_correction"
    VOCABULARY_EXPANSION = "vocabulary_expansion"
    CULTURAL_CONTEXT = "cultural_context"
    ASSESSMENT = "assessment"
    CHAT = "chat"


class ModelAccessTier(str, Enum):
    """User access tier for models"""
    FREE = "free"           # Free tier models only
    STANDARD = "standard"   # Balanced tier models
    PREMIUM = "premium"     # Flagship models
    ADMIN = "admin"         # All models including custom


@dataclass
class UserLLMConfig:
    """User's LLM configuration including BYOK keys"""
    user_id: int
    # BYOK keys (encrypted in production)
    openai_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    google_key: Optional[str] = None
    openrouter_key: Optional[str] = None
    xai_key: Optional[str] = None
    custom_endpoints: dict = field(default_factory=dict)  # provider_id -> {base_url, key}
    
    # Access tier
    access_tier: ModelAccessTier = ModelAccessTier.FREE
    
    # Preferences
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None
    cost_limit_usd_per_month: Decimal = Decimal("10.00")
    
    # Usage tracking
    total_tokens_used: int = 0
    total_cost_usd: Decimal = Decimal("0")
    last_reset: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class AdminModelConfig:
    """Admin configuration for model tiers"""
    
    # ─── Free tier models (from shared.llm.UnifiedLLMService - no API keys needed) ───
    # OpenCode Zen (built-in, uses opencode CLI with zen keys)
    SHARED_FREE_MODELS_OPENCODE: list[str] = field(default_factory=lambda: [
        "mimo-v2.6-flash-free", "nemotron-3-ultra-free", "big-pickle",
        "nemotron-3.5-lightning-free", "space-bunny-free"
    ])
    
    # OpenRouter free models (requires OPENROUTER_API_KEY for discovery, fallback works without)
    SHARED_FREE_MODELS_OPENROUTER: list[str] = field(default_factory=lambda: [
        "meta-llama/llama-3.3-70b:free", "meta-llama/llama-3.1-8b-instruct:free",
        "mistralai/mistral-7b-instruct:free", "google/gemma-3-12b-it:free",
        "microsoft/phi-3-mini-128k-instruct:free", "qwen/qwen-2-7b-instruct:free",
        "deepseek/deepseek-r1:free", "nousresearch/hermes-3-llama-3.1-405b:free"
    ])
    
    # NVIDIA NIM (requires NVIDIA_API_KEY for discovery, fallback works without)
    SHARED_FREE_MODELS_NVIDIA: list[str] = field(default_factory=lambda: [
        "meta/llama-3.1-70b-instruct", "meta/llama-3.2-3b-instruct",
        "mistralai/mistral-7b-instruct-v0.3", "microsoft/phi-3-medium-128k-instruct",
        "qwen/qwen2-7b-instruct", "nvidia/nemotron-3-super-120b-a12b",
        "nvidia/nemotron-3-nano-30b-a3b"
    ])
    
    # Groq (requires GROQ_API_KEY)
    SHARED_FREE_MODELS_GROQ: list[str] = field(default_factory=lambda: [
        "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b", "allam-2-7b"
    ])
    
    # Cohere (requires COHERE_API_KEY)
    SHARED_FREE_MODELS_COHERE: list[str] = field(default_factory=lambda: [
        "command-r", "command-r-plus", "command"
    ])
    
    # Cloudflare (requires CLOUDFLARE_API_KEY)
    SHARED_FREE_MODELS_CLOUDFLARE: list[str] = field(default_factory=lambda: [
        "@cf/meta/llama-3-8b-instruct", "@cf/meta/llama-3.1-8b-instruct",
        "@cf/mistral/mistral-7b-instruct-v0.1"
    ])
    
    # Local Ollama (requires local Ollama server)
    SHARED_FREE_MODELS_OLLAMA: list[str] = field(default_factory=lambda: [
        "llama3.1:latest", "mistral:latest", "gemma2:latest", "phi3:latest"
    ])
    
    # Combined free models (used when no paid keys configured)
    free_models: list[str] = field(default_factory=lambda: [
        # Primary: OpenCode Zen (works out of box with opencode CLI)
        "mimo-v2.6-flash-free", "nemotron-3-ultra-free", "big-pickle",
        # OpenRouter free fallbacks
        "meta-llama/llama-3.3-70b:free", "mistralai/mistral-7b-instruct:free",
        "google/gemma-3-12b-it:free", "deepseek/deepseek-r1:free",
        # NVIDIA fallbacks
        "meta/llama-3.1-70b-instruct", "mistralai/mistral-7b-instruct-v0.3",
    ])
    
    # Standard tier models (paid keys required)
    standard_models: list[str] = field(default_factory=lambda: [
        "anthropic/claude-3-5-sonnet-20241022",
        "openai/gpt-4o",
        "google/gemini-1.5-pro",
    ])
    
    # Premium tier models (paid keys required)
    premium_models: list[str] = field(default_factory=lambda: [
        "anthropic/claude-3-5-opus-20241022",
        "openai/gpt-4-turbo",
        "google/gemini-2.5-pro",
    ])
    
    # Task-specific model recommendations (FREE tier uses shared free providers)
    task_models: dict[LLMTaskType, dict[ModelAccessTier, str]] = field(default_factory=lambda: {
        LLMTaskType.LESSON_GENERATION: {
            ModelAccessTier.FREE: "meta-llama/llama-3.3-70b:free",  # Best free for complex generation
            ModelAccessTier.STANDARD: "anthropic/claude-3-5-sonnet-20241022",
            ModelAccessTier.PREMIUM: "anthropic/claude-3-5-opus-20241022",
        },
        LLMTaskType.CONTENT_CREATION: {
            ModelAccessTier.FREE: "mimo-v2.6-flash-free",  # OpenCode Zen - good for content
            ModelAccessTier.STANDARD: "anthropic/claude-3-5-sonnet-20241022",
            ModelAccessTier.PREMIUM: "google/gemini-2.5-pro",
        },
        LLMTaskType.GRAMMAR_EXPLANATION: {
            ModelAccessTier.FREE: "mistralai/mistral-7b-instruct:free",  # Good at structured output
            ModelAccessTier.STANDARD: "anthropic/claude-3-5-sonnet-20241022",
            ModelAccessTier.PREMIUM: "anthropic/claude-3-5-opus-20241022",
        },
        LLMTaskType.CONVERSATION_PRACTICE: {
            ModelAccessTier.FREE: "mimo-v2.6-flash-free",  # Fast, conversational
            ModelAccessTier.STANDARD: "openai/gpt-4o",
            ModelAccessTier.PREMIUM: "anthropic/claude-3-5-sonnet-20241022",
        },
        LLMTaskType.PRONUNCIATION_GUIDANCE: {
            ModelAccessTier.FREE: "google/gemma-3-12b-it:free",  # Good at phonetics
            ModelAccessTier.STANDARD: "anthropic/claude-3-5-sonnet-20241022",
            ModelAccessTier.PREMIUM: "anthropic/claude-3-5-opus-20241022",
        },
        LLMTaskType.WRITING_CORRECTION: {
            ModelAccessTier.FREE: "mistralai/mistral-7b-instruct:free",  # Structured corrections
            ModelAccessTier.STANDARD: "anthropic/claude-3-5-sonnet-20241022",
            ModelAccessTier.PREMIUM: "anthropic/claude-3-5-opus-20241022",
        },
        LLMTaskType.VOCABULARY_EXPANSION: {
            ModelAccessTier.FREE: "meta-llama/llama-3.3-70b:free",  # Broad knowledge
            ModelAccessTier.STANDARD: "openai/gpt-4o",
            ModelAccessTier.PREMIUM: "google/gemini-2.5-pro",
        },
        LLMTaskType.CULTURAL_CONTEXT: {
            ModelAccessTier.FREE: "meta-llama/llama-3.3-70b:free",  # Cultural knowledge
            ModelAccessTier.STANDARD: "anthropic/claude-3-5-sonnet-20241022",
            ModelAccessTier.PREMIUM: "anthropic/claude-3-5-opus-20241022",
        },
        LLMTaskType.ASSESSMENT: {
            ModelAccessTier.FREE: "mimo-v2.6-flash-free",  # Fast evaluation
            ModelAccessTier.STANDARD: "anthropic/claude-3-5-sonnet-20241022",
            ModelAccessTier.PREMIUM: "anthropic/claude-3-5-opus-20241022",
        },
        LLMTaskType.CHAT: {
            ModelAccessTier.FREE: "mimo-v2.6-flash-free",  # Default free chat
            ModelAccessTier.STANDARD: "openai/gpt-4o",
            ModelAccessTier.PREMIUM: "anthropic/claude-3-5-sonnet-20241022",
        },
    })
    
    # Cost limits per tier (monthly USD) - FREE tier uses shared free providers ($0)
    tier_cost_limits: dict[ModelAccessTier, Decimal] = field(default_factory=lambda: {
        ModelAccessTier.FREE: Decimal("0.00"),      # Free providers from shared
        ModelAccessTier.STANDARD: Decimal("25.00"),  # Paid models
        ModelAccessTier.PREMIUM: Decimal("100.00"),  # Flagship models
    })
    
    def get_all_free_models(self) -> list[str]:
        """Get all free models from all shared providers"""
        all_models = []
        all_models.extend(self.SHARED_FREE_MODELS_OPENCODE)
        all_models.extend(self.SHARED_FREE_MODELS_OPENROUTER)
        all_models.extend(self.SHARED_FREE_MODELS_NVIDIA)
        all_models.extend(self.SHARED_FREE_MODELS_GROQ)
        all_models.extend(self.SHARED_FREE_MODELS_COHERE)
        all_models.extend(self.SHARED_FREE_MODELS_CLOUDFLARE)
        all_models.extend(self.SHARED_FREE_MODELS_OLLAMA)
        return list(set(all_models))  # Deduplicate
    
    def get_free_models_for_task(self, task_type: LLMTaskType) -> list[str]:
        """Get recommended free models for a specific task"""
        free_model = self.task_models.get(task_type, {}).get(ModelAccessTier.FREE)
        if free_model:
            return [free_model]
        return self.free_models[:3]  # Top 3 general free models


class TutorLLMService:
    """
    Unified LLM service for Language Tutor.
    Wraps shared.llm.UnifiedLLMService with:
    - User BYOK support
    - Admin model tier management
    - Intelligent model selection
    - Cost tracking
    """
    
    def __init__(self):
        self.admin_config = AdminModelConfig()
        self._user_configs: dict[int, UserLLMConfig] = {}
        self._shared_service: Optional[CanonicalAIService] = None
        self._initialize_shared_service()
    
    def _initialize_shared_service(self):
        """Initialize the shared unified LLM service with service-level keys"""
        if not SHARED_LLM_AVAILABLE:
            log.warning("shared_llm_not_available", reason="Import failed")
            return
        
        # Set up environment variables for shared service from config
        # Paid provider keys (optional - for standard/premium tiers)
        if settings.OPENAI_API_KEY:
            os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        if settings.ANTHROPIC_API_KEY:
            os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY
        
        # Free provider keys (optional - enhances free tier)
        # All free providers need API keys to be available in shared.llm
        free_provider_keys = {
            "OPENROUTER_API_KEY": getattr(settings, 'OPENROUTER_API_KEY', ''),
            "GROQ_API_KEY": getattr(settings, 'GROQ_API_KEY', ''),
            "GEMINI_API_KEY": getattr(settings, 'GEMINI_API_KEY', ''),
            "GOOGLE_AI_API_KEY": getattr(settings, 'GOOGLE_AI_API_KEY', ''),
            "NVIDIA_API_KEY": getattr(settings, 'NVIDIA_API_KEY', ''),
            "NVIDIA_NIM_API_KEY": getattr(settings, 'NVIDIA_NIM_API_KEY', ''),
            "COHERE_API_KEY": getattr(settings, 'COHERE_API_KEY', ''),
            "TOGETHER_API_KEY": getattr(settings, 'TOGETHER_API_KEY', ''),
            "MISTRAL_API_KEY": getattr(settings, 'MISTRAL_API_KEY', ''),
            "CLOUDFLARE_AI_TOKEN": getattr(settings, 'CLOUDFLARE_AI_TOKEN', ''),
            "CLOUDFLARE_ACCOUNT_ID": getattr(settings, 'CLOUDFLARE_ACCOUNT_ID', ''),
            "CEREBRAS_API_KEY": getattr(settings, 'CEREBRAS_API_KEY', ''),
        }
        for env_var, value in free_provider_keys.items():
            if value:
                os.environ[env_var] = value
        
        # OpenCode Zen: uses opencode CLI with zen keys
        # Configure to use correct model prefix (opencode-zen instead of zen-key1)
        os.environ["OPENCODE_ZEN_KEYS"] = "opencode-zen"
        
        # Disable opencode_zen provider since it doesn't work with model specification
        # The HTTP-based free providers (openrouter_free, groq_llama, etc.) work better
        os.environ["LLM_DISABLED_PROVIDERS"] = "opencode_zen"
        
        try:
            self._shared_service = CanonicalAIService.get_instance(dry_run=False)
            log.info("tutor_llm_service_initialized", shared_service=True, 
                     free_providers=["openrouter_free", "nvidia_nim", "groq_llama", "cohere_free", "cloudflare_workers_ai", "gemini_flash", "together_free", "mistral_free"])
        except Exception as e:
            log.warning("shared_llm_init_failed", error=str(e))
            self._shared_service = None
    
    # =========================================================================
    # USER CONFIG MANAGEMENT
    # =========================================================================
    
    async def get_user_config(self, user_id: int) -> UserLLMConfig:
        """Get user's LLM configuration (with BYOK keys)"""
        if user_id in self._user_configs:
            return self._user_configs[user_id]
        
        # Load from database
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if user and hasattr(user, 'llm_config') and user.llm_config:
                config_data = user.llm_config
                config = UserLLMConfig(
                    user_id=user_id,
                    openai_key=config_data.get("openai_key"),
                    anthropic_key=config_data.get("anthropic_key"),
                    google_key=config_data.get("google_key"),
                    openrouter_key=config_data.get("openrouter_key"),
                    xai_key=config_data.get("xai_key"),
                    custom_endpoints=config_data.get("custom_endpoints", {}),
                    access_tier=ModelAccessTier(config_data.get("access_tier", "free")),
                    preferred_provider=config_data.get("preferred_provider"),
                    preferred_model=config_data.get("preferred_model"),
                    cost_limit_usd_per_month=Decimal(str(config_data.get("cost_limit_usd_per_month", "10.00"))),
                    total_tokens_used=config_data.get("total_tokens_used", 0),
                    total_cost_usd=Decimal(str(config_data.get("total_cost_usd", "0"))),
                    last_reset=config_data.get("last_reset", datetime.now(UTC).isoformat()),
                )
            else:
                config = UserLLMConfig(user_id=user_id)
            
            self._user_configs[user_id] = config
            return config
    
    async def update_user_config(self, user_id: int, config: UserLLMConfig):
        """Save user's LLM configuration"""
        self._user_configs[user_id] = config
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if user:
                config_dict = {
                    "openai_key": config.openai_key,
                    "anthropic_key": config.anthropic_key,
                    "google_key": config.google_key,
                    "openrouter_key": config.openrouter_key,
                    "xai_key": config.xai_key,
                    "custom_endpoints": config.custom_endpoints,
                    "access_tier": config.access_tier.value,
                    "preferred_provider": config.preferred_provider,
                    "preferred_model": config.preferred_model,
                    "cost_limit_usd_per_month": str(config.cost_limit_usd_per_month),
                    "total_tokens_used": config.total_tokens_used,
                    "total_cost_usd": str(config.total_cost_usd),
                    "last_reset": config.last_reset,
                }
                user.llm_config = config_dict
                await db.commit()
    
    async def set_user_api_key(self, user_id: int, provider: str, api_key: str):
        """Set a user's BYOK API key for a provider"""
        config = await self.get_user_config(user_id)
        
        if provider == "openai":
            config.openai_key = api_key
        elif provider == "anthropic":
            config.anthropic_key = api_key
        elif provider == "google":
            config.google_key = api_key
        elif provider == "openrouter":
            config.openrouter_key = api_key
        elif provider == "xai":
            config.xai_key = api_key
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        await self.update_user_config(user_id, config)
        log.info("user_api_key_set", user_id=user_id, provider=provider)
    
    async def set_user_custom_endpoint(self, user_id: int, provider_id: str, base_url: str, api_key: str):
        """Set a user's custom endpoint (for self-hosted/local models)"""
        config = await self.get_user_config(user_id)
        config.custom_endpoints[provider_id] = {"base_url": base_url, "api_key": api_key}
        await self.update_user_config(user_id, config)
    
    async def set_user_access_tier(self, user_id: int, tier: ModelAccessTier):
        """Set user's access tier (admin only)"""
        config = await self.get_user_config(user_id)
        config.access_tier = tier
        # Update cost limit based on tier
        config.cost_limit_usd_per_month = self.admin_config.tier_cost_limits.get(tier, Decimal("10.00"))
        await self.update_user_config(user_id, config)
    
    # =========================================================================
    # MODEL SELECTION
    # =========================================================================
    
    def get_available_models(self, user_id: int) -> list[str]:
        """Get list of model IDs available to user based on tier"""
        config = self._user_configs.get(user_id)
        if not config:
            # Default to free tier
            return self.admin_config.free_models
        
        available = []
        if config.access_tier in [ModelAccessTier.FREE, ModelAccessTier.STANDARD, ModelAccessTier.PREMIUM, ModelAccessTier.ADMIN]:
            available.extend(self.admin_config.free_models)
        if config.access_tier in [ModelAccessTier.STANDARD, ModelAccessTier.PREMIUM, ModelAccessTier.ADMIN]:
            available.extend(self.admin_config.standard_models)
        if config.access_tier in [ModelAccessTier.PREMIUM, ModelAccessTier.ADMIN]:
            available.extend(self.admin_config.premium_models)
        if config.access_tier == ModelAccessTier.ADMIN:
            # Admin can also use any custom models
            pass
        
        # Add user's custom models
        for provider_id, endpoint in config.custom_endpoints.items():
            available.append(f"custom/{provider_id}")
        
        return list(set(available))  # Deduplicate
    
    def select_model_for_task(
        self,
        task_type: LLMTaskType,
        user_id: int,
        user_preference: Optional[str] = None,
    ) -> str:
        """Select the best model for a task based on user's tier and preferences"""
        config = self._user_configs.get(user_id)
        if not config:
            # Default to free tier
            return self.admin_config.task_models.get(task_type, {}).get(ModelAccessTier.FREE, "google/gemini-1.5-flash")
        
        # Check user's explicit preference first
        if user_preference and user_preference in self.get_available_models(user_id):
            return user_preference
        if config.preferred_model and config.preferred_model in self.get_available_models(user_id):
            return config.preferred_model
        
        # Select based on tier
        tier_models = self.admin_config.task_models.get(task_type, {})
        model = tier_models.get(config.access_tier)
        
        if model and model in self.get_available_models(user_id):
            return model
        
        # Fallback to highest available tier
        for tier in [ModelAccessTier.PREMIUM, ModelAccessTier.STANDARD, ModelAccessTier.FREE]:
            model = tier_models.get(tier)
            if model and model in self.get_available_models(user_id):
                return model
        
        # Ultimate fallback
        return "google/gemini-1.5-flash"
    
    # =========================================================================
    # LLM CALLS
    # =========================================================================
    
    def _is_free_model(self, model: str) -> bool:
        """Check if a model is from shared free providers"""
        free_models = self.admin_config.get_all_free_models()
        return model in free_models
    
    def _get_backend_for_model(self, model: str) -> str:
        """Determine which backend to use for a model"""
        if self._is_free_model(model):
            return "shared-free"  # Use shared free providers
        return "shared-paid"  # Use shared with paid keys
    
    async def complete(
        self,
        user_id: int,
        prompt: str,
        system: Optional[str] = None,
        task_type: LLMTaskType = LLMTaskType.CHAT,
        model: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """
        Complete a prompt using the best available model for the user/task.
        
        Uses shared free providers (OpenCode Zen, OpenRouter free, NVIDIA, Groq, etc.)
        for FREE tier users. Paid tiers use BYOK or service keys.
        
        Returns dict with: success, data, error, model_used, tokens_used, cost_usd
        """
        # Select model
        if model is None:
            model = self.select_model_for_task(task_type, user_id)
        
        # Check if model is free (from shared providers)
        is_free = self._is_free_model(model)
        user_config = await self.get_user_config(user_id)
        
        # For free models, use shared facade (no API key needed)
        # For paid models, check BYOK
        byok_key = None
        old_key = None
        if not is_free:
            provider = model.split("/")[0] if "/" in model else "unknown"
            byok_key = self._get_byok_key(user_config, provider)
            if byok_key:
                env_var = self._provider_to_env_var(provider)
                old_key = os.environ.get(env_var)
                os.environ[env_var] = byok_key
        
        try:
            # Use shared free providers via UnifiedLLMService with preferred HTTP providers (skip opencode_zen)
            if is_free and SHARED_LLM_AVAILABLE:
                try:
                    # Prefer HTTP-based free providers over CLI-based ones (opencode_zen)
                    prefer_providers = [
                        "openrouter_free", "groq_llama", "gemini_flash", "gemini_gai_flash",
                        "nvidia_nim", "cohere_free", "together_free", "cloudflare_workers_ai",
                        "mistral_free", "cerebras_qwen", "nvidia_nemotron_super", "nvidia_llama4_maverick"
                    ]
                    
                    # Use the shared service with preferred providers
                    # Note: prefer_providers is passed to complete() method
                    response = await self._shared_service.complete(
                        prompt=prompt,
                        system=system,
                        model=model,
                        json_mode=json_mode,
                        prefer_providers=prefer_providers,
                    )
                    
                    result = {
                        "success": response.success,
                        "data": response.data,
                        "error": response.error,
                        "model_used": model,
                        "tokens_used": getattr(response, 'prompt_tokens', 0) + getattr(response, 'completion_tokens', 0),
                        "cost_usd": getattr(response, 'cost_usd', 0.0),
                        "backend": "shared-free",
                        "provider": getattr(response, 'provider', None),
                    }
                    log.info("tutor_llm_complete_free", user_id=user_id, model=model, task=task_type.value,
                             provider=result.get("provider"))
                except Exception as e:
                    log.warning("shared_free_llm_failed", error=str(e), model=model)
                    # Fall back to shared service without preferred providers
                    if self._shared_service:
                        response = await self._shared_service.complete(
                            prompt=prompt, system=system, model=model, json_mode=json_mode
                        )
                        result = {
                            "success": response.success,
                            "data": response.data,
                            "error": response.error,
                            "model_used": model,
                            "tokens_used": getattr(response, 'prompt_tokens', 0) + getattr(response, 'completion_tokens', 0),
                            "cost_usd": getattr(response, 'cost_usd', 0.0),
                            "backend": "shared-fallback",
                        }
                    else:
                        raise
            elif self._shared_service:
                # Use shared unified LLM service (for paid models)
                response = await self._shared_service.complete(
                    prompt=prompt,
                    system=system,
                    model=model,
                    json_mode=json_mode,
                )
                
                result = {
                    "success": response.success,
                    "data": response.data,
                    "error": response.error,
                    "model_used": model,
                    "tokens_used": 0,
                    "cost_usd": 0.0 if is_free else 0.001,  # Estimate
                    "backend": "shared-paid",
                }
            else:
                # Fallback: direct provider call
                result = await self._direct_complete(
                    provider=model.split("/")[0] if "/" in model else "unknown",
                    model=model,
                    prompt=prompt,
                    system=system,
                    json_mode=json_mode,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    api_key=byok_key,
                )
            
            # Track usage
            if result["success"]:
                await self._track_usage(user_id, result)
            
            return result
            
        finally:
            # Restore original key
            if byok_key and old_key is not None:
                os.environ[env_var] = old_key
            elif byok_key and old_key is None:
                os.environ.pop(env_var, None)
    
    async def call_json(
        self,
        user_id: int,
        prompt: str,
        schema: Optional[dict] = None,
        task_type: LLMTaskType = LLMTaskType.CONTENT_CREATION,
        model: Optional[str] = None,
    ) -> dict:
        """Call LLM expecting JSON response"""
        if model is None:
            model = self.select_model_for_task(task_type, user_id)
        
        # Enhance prompt with JSON schema instructions
        if schema:
            prompt = self._add_json_schema_to_prompt(prompt, schema)
        
        return await self.complete(
            user_id=user_id,
            prompt=prompt,
            task_type=task_type,
            model=model,
            json_mode=True,
        )
    
    # =========================================================================
    # DIRECT PROVIDER CALLS (fallback when shared service unavailable)
    # =========================================================================
    
    async def _direct_complete(
        self,
        provider: str,
        model: str,
        prompt: str,
        system: Optional[str],
        json_mode: bool,
        temperature: float,
        max_tokens: Optional[int],
        api_key: Optional[str],
    ) -> dict:
        """Direct API call to provider (fallback)"""
        import httpx
        
        provider_config = PROVIDERS.get(provider, {})
        api_style = provider_config.get("api_style", "openai")
        base_url = provider_config.get("base_url", "")
        
        if not api_key:
            return {
                "success": False,
                "error": f"No API key for {provider}",
                "model_used": model,
                "tokens_used": 0,
                "cost_usd": 0.0,
            }
        
        short_model = model.split("/")[-1] if "/" in model else model
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if api_style == "anthropic":
                    # Anthropic Messages API
                    headers = {
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    }
                    messages = []
                    if system:
                        messages.append({"role": "system", "content": system})
                    messages.append({"role": "user", "content": prompt})
                    
                    payload = {
                        "model": short_model,
                        "messages": messages,
                        "max_tokens": max_tokens or 4096,
                        "temperature": temperature,
                    }
                    if json_mode:
                        payload["system"] = (system or "") + "\n\nRespond ONLY with valid JSON."
                    
                    response = await client.post(
                        f"{base_url}/v1/messages",
                        headers=headers,
                        json=payload,
                    )
                else:
                    # OpenAI-compatible API
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    }
                    messages = []
                    if system:
                        messages.append({"role": "system", "content": system})
                    messages.append({"role": "user", "content": prompt})
                    
                    payload = {
                        "model": short_model,
                        "messages": messages,
                        "max_tokens": max_tokens or 4096,
                        "temperature": temperature,
                    }
                    if json_mode:
                        payload["response_format"] = {"type": "json_object"}
                    
                    response = await client.post(
                        f"{base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                
                response.raise_for_status()
                data = response.json()
                
                # Parse response
                if api_style == "anthropic":
                    content = data["content"][0]["text"]
                    usage = data.get("usage", {})
                else:
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                
                # Calculate cost
                cost = self._calculate_cost(provider, short_model, usage)
                
                return {
                    "success": True,
                    "data": content,
                    "model_used": model,
                    "tokens_used": usage.get("total_tokens", 0),
                    "cost_usd": float(cost),
                    "usage": usage,
                }
                
        except Exception as e:
            log.error("direct_llm_call_failed", provider=provider, model=model, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "model_used": model,
                "tokens_used": 0,
                "cost_usd": 0.0,
            }
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_byok_key(self, config: UserLLMConfig, provider: str) -> Optional[str]:
        """Get user's BYOK key for a provider"""
        key_map = {
            "openai": config.openai_key,
            "anthropic": config.anthropic_key,
            "google": config.google_key,
            "openrouter": config.openrouter_key,
            "xai": config.xai_key,
        }
        return key_map.get(provider)
    
    def _provider_to_env_var(self, provider: str) -> str:
        """Map provider to environment variable name"""
        return {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "xai": "XAI_API_KEY",
        }.get(provider, f"{provider.upper()}_API_KEY")
    
    def _add_json_schema_to_prompt(self, prompt: str, schema: dict) -> str:
        """Add JSON schema instructions to prompt"""
        return f"""{prompt}

IMPORTANT: Respond ONLY with valid JSON matching this schema:
{json.dumps(schema, indent=2)}

Do not include any explanation, markdown, or text outside the JSON object."""
    
    def _calculate_cost(self, provider: str, model: str, usage: dict) -> Decimal:
        """Calculate cost from usage tokens"""
        provider_config = PROVIDERS.get(provider, {})
        input_per_1m = Decimal(str(provider_config.get("input_per_1m", 0)))
        output_per_1m = Decimal(str(provider_config.get("output_per_1m", 0)))
        
        input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
        output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))
        
        input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * input_per_1m
        output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * output_per_1m
        
        return input_cost + output_cost
    
    async def _track_usage(self, user_id: int, result: dict):
        """Track token usage and cost for user"""
        config = await self.get_user_config(user_id)
        tokens = result.get("tokens_used", 0)
        cost = Decimal(str(result.get("cost_usd", 0)))
        
        config.total_tokens_used += tokens
        config.total_cost_usd += cost
        
        # Check monthly reset
        last_reset = datetime.fromisoformat(config.last_reset.replace('Z', '+00:00'))
        if (datetime.now(UTC) - last_reset).days >= 30:
            config.total_tokens_used = tokens
            config.total_cost_usd = cost
            config.last_reset = datetime.now(UTC).isoformat()
        
        await self.update_user_config(user_id, config)
    
    # =========================================================================
    # ADMIN METHODS
    # =========================================================================
    
    def get_admin_model_config(self) -> AdminModelConfig:
        """Get current admin model configuration"""
        return self.admin_config
    
    def update_admin_model_config(self, config: AdminModelConfig):
        """Update admin model configuration"""
        self.admin_config = config
        log.info("admin_model_config_updated")
    
    def add_free_model(self, model_id: str):
        """Add a model to free tier"""
        if model_id not in self.admin_config.free_models:
            self.admin_config.free_models.append(model_id)
    
    def add_standard_model(self, model_id: str):
        """Add a model to standard tier"""
        if model_id not in self.admin_config.standard_models:
            self.admin_config.standard_models.append(model_id)
    
    def add_premium_model(self, model_id: str):
        """Add a model to premium tier"""
        if model_id not in self.admin_config.premium_models:
            self.admin_config.premium_models.append(model_id)
    
    def set_task_model(self, task_type: LLMTaskType, tier: ModelAccessTier, model_id: str):
        """Set recommended model for a task type and tier"""
        if task_type not in self.admin_config.task_models:
            self.admin_config.task_models[task_type] = {}
        self.admin_config.task_models[task_type][tier] = model_id
    
    # =========================================================================
    # DISCOVERY
    # =========================================================================
    
    def get_available_providers(self) -> list[dict]:
        """Get list of available providers with metadata"""
        return list_providers()
    
    def get_user_model_options(self, user_id: int) -> dict:
        """Get model options organized by tier for user"""
        config = self._user_configs.get(user_id)
        tier = config.access_tier if config else ModelAccessTier.FREE
        
        return {
            "current_tier": tier.value,
            "free_models": self.admin_config.free_models,
            "standard_models": self.admin_config.standard_models if tier in [ModelAccessTier.STANDARD, ModelAccessTier.PREMIUM, ModelAccessTier.ADMIN] else [],
            "premium_models": self.admin_config.premium_models if tier in [ModelAccessTier.PREMIUM, ModelAccessTier.ADMIN] else [],
            "custom_models": list(config.custom_endpoints.keys()) if config else [],
            "recommended_by_task": {
                task.value: {
                    t.value: m for t, m in models.items()
                    if t in [ModelAccessTier.FREE] or (t == ModelAccessTier.STANDARD and tier in [ModelAccessTier.STANDARD, ModelAccessTier.PREMIUM, ModelAccessTier.ADMIN]) or (t == ModelAccessTier.PREMIUM and tier in [ModelAccessTier.PREMIUM, ModelAccessTier.ADMIN])
                }
                for task, models in self.admin_config.task_models.items()
            },
            "cost_limit_usd": str(config.cost_limit_usd_per_month) if config else "10.00",
            "current_usage_usd": str(config.total_cost_usd) if config else "0.00",
        }


# Singleton instance
_tutor_llm_service: Optional[TutorLLMService] = None


def get_tutor_llm_service() -> TutorLLMService:
    """Get singleton TutorLLMService instance"""
    global _tutor_llm_service
    if _tutor_llm_service is None:
        _tutor_llm_service = TutorLLMService()
    return _tutor_llm_service