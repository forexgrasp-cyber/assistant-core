"""
AI Orchestrator Configuration
"""
from functools import lru_cache
from typing import Optional, List, Dict
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AIOrchestratorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Provider Configuration
    default_llm_provider: str = Field(
        default="openai",
        description="Default LLM provider (openai, anthropic, local)"
    )

    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    openai_organization: Optional[str] = Field(
        default=None,
        description="OpenAI organization ID"
    )
    openai_default_model: str = Field(
        default="gpt-4o-mini",
        description="Default OpenAI model"
    )
    openai_max_tokens: int = Field(
        default=4096,
        description="Max tokens for OpenAI responses"
    )
    openai_temperature: float = Field(
        default=0.1,
        description="Default temperature for OpenAI"
    )

    # Anthropic Configuration
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key"
    )
    anthropic_default_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Default Anthropic model"
    )
    anthropic_max_tokens: int = Field(
        default=4096,
        description="Max tokens for Anthropic responses"
    )
    anthropic_temperature: float = Field(
        default=0.1,
        description="Default temperature for Anthropic"
    )

    # Local/Embedded LLM Configuration
    local_llm_enabled: bool = Field(
        default=False,
        description="Enable local LLM (via Ollama, etc.)"
    )
    local_llm_base_url: str = Field(
        default="http://localhost:11434",
        description="Local LLM base URL"
    )
    local_llm_model: str = Field(
        default="llama3.1:8b",
        description="Local LLM model name"
    )

    # Token Management
    max_context_tokens: int = Field(
        default=128000,
        description="Max context window tokens"
    )
    default_max_tokens: int = Field(
        default=4096,
        description="Default max tokens per response"
    )
    token_budget_per_skill: int = Field(
        default=2000,
        description="Token budget per skill execution"
    )
    token_budget_per_tool: int = Field(
        default=1000,
        description="Token budget per tool call"
    )

    # Agent Configuration
    max_agent_iterations: int = Field(
        default=10,
        description="Max iterations per agent run"
    )
    max_tool_calls_per_iteration: int = Field(
        default=5,
        description="Max tool calls per agent iteration"
    )
    agent_timeout_seconds: int = Field(
        default=300,
        description="Agent execution timeout in seconds"
    )

    # Skill Configuration
    skill_registry_path: str = Field(
        default="./skills",
        description="Path to skill registry"
    )
    skill_hot_reload: bool = Field(
        default=True,
        description="Enable hot reloading of skills"
    )
    max_skills_per_agent: int = Field(
        default=20,
        description="Max skills an agent can have"
    )

    # Memory Configuration
    memory_type: str = Field(
        default="chromadb",
        description="Memory backend (chromadb, redis, postgres)"
    )
    short_term_memory_ttl_hours: int = Field(
        default=24,
        description="Short-term memory TTL in hours"
    )
    long_term_memory_ttl_days: int = Field(
        default=365,
        description="Long-term memory TTL in days"
    )
    max_memory_entries: int = Field(
        default=10000,
        description="Max memory entries per agent"
    )
    memory_embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model for memory search"
    )
    memory_max_results: int = Field(
        default=10,
        description="Max results from memory search"
    )
    memory_similarity_threshold: float = Field(
        default=0.7,
        description="Similarity threshold for memory retrieval"
    )

    # Tool Configuration
    tool_timeout_seconds: int = Field(
        default=30,
        description="Tool execution timeout in seconds"
    )
    max_tool_retries: int = Field(
        default=3,
        description="Max retries for tool execution"
    )
    tool_retry_backoff_seconds: float = Field(
        default=1.0,
        description="Backoff base for tool retries"
    )

    # Vector Database (ChromaDB)
    chromadb_host: str = Field(
        default="localhost",
        description="ChromaDB host"
    )
    chromadb_port: int = Field(
        default=8000,
        description="ChromaDB port"
    )
    chromadb_collection_prefix: str = Field(
        default="ai_orchestrator",
        description="ChromaDB collection prefix"
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/2",
        description="Redis URL for caching and pub/sub"
    )

    # MCP Server Configuration
    mcp_server_enabled: bool = Field(
        default=True,
        description="Enable MCP server for agent tools"
    )
    mcp_server_port: int = Field(
        default=8767,
        description="MCP server port"
    )

    # Skill Auto-training
    skill_auto_training_enabled: bool = Field(
        default=False,
        description="Enable automatic skill training from usage"
    )
    skill_training_min_samples: int = Field(
        default=100,
        description="Minimum samples before skill training"
    )
    skill_training_schedule_cron: str = Field(
        default="0 2 * * *",
        description="Cron schedule for skill training"
    )

    # Observability
    enable_tracing: bool = Field(
        default=True,
        description="Enable execution tracing"
    )
    trace_sample_rate: float = Field(
        default=0.1,
        description="Trace sample rate"
    )
    log_level: str = Field(
        default="INFO",
        description="Log level"
    )

    # API Configuration
    api_host: str = Field(
        default="0.0.0.0",
        description="API host"
    )
    api_port: int = Field(
        default=8002,
        description="API port"
    )
    api_workers: int = Field(
        default=4,
        description="API workers"
    )


@lru_cache
def get_ai_orchestrator_settings() -> AIOrchestratorSettings:
    return AIOrchestratorSettings()