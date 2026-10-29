"""
CDP Engine Configuration
"""
from functools import lru_cache
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CDPSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/cdp",
        description="PostgreSQL database URL"
    )
    database_pool_size: int = Field(
        default=20,
        description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=10,
        description="Database max overflow"
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/1",
        description="Redis URL for caching"
    )
    redis_pool_size: int = Field(
        default=10,
        description="Redis connection pool size"
    )

    # Identity Resolution Configuration
    identity_resolution_enabled: bool = Field(
        default=True,
        description="Enable identity resolution"
    )
    deterministic_matching_enabled: bool = Field(
        default=True,
        description="Enable deterministic matching"
    )
    probabilistic_matching_enabled: bool = Field(
        default=True,
        description="Enable probabilistic matching"
    )
    fuzzy_matching_threshold: float = Field(
        default=0.85,
        description="Fuzzy matching threshold (0-1)"
    )
    max_identity_candidates: int = Field(
        default=10,
        description="Maximum identity candidates to consider"
    )

    # Profile Configuration
    profile_cache_ttl_seconds: int = Field(
        default=3600,
        description="Profile cache TTL in seconds"
    )
    profile_max_events: int = Field(
        default=10000,
        description="Maximum events per profile"
    )
    profile_retention_days: int = Field(
        default=730,
        description="Profile retention in days"
    )

    # Segmentation Configuration
    segment_cache_ttl_seconds: int = Field(
        default=300,
        description="Segment cache TTL in seconds"
    )
    segment_max_members: int = Field(
        default=1000000,
        description="Maximum members per segment"
    )
    segment_refresh_interval_seconds: int = Field(
        default=3600,
        description="Segment refresh interval in seconds"
    )
    segment_max_complexity: int = Field(
        default=100,
        description="Maximum segment rule complexity"
    )

    # Vector Search Configuration
    vector_search_enabled: bool = Field(
        default=True,
        description="Enable vector search for probabilistic matching"
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model for vector search"
    )
    embedding_dimension: int = Field(
        default=384,
        description="Embedding dimension"
    )
    faiss_index_type: str = Field(
        default="IVF100,Flat",
        description="FAISS index type"
    )
    faiss_nprobe: int = Field(
        default=10,
        description="FAISS nprobe parameter"
    )

    # Enrichment Configuration
    enrichment_enabled: bool = Field(
        default=True,
        description="Enable profile enrichment"
    )
    enrichment_providers: List[str] = Field(
        default=["clearbit", "fullcontact", "apollo"],
        description="Enrichment providers"
    )
    enrichment_cache_ttl_seconds: int = Field(
        default=86400,
        description="Enrichment cache TTL in seconds"
    )
    enrichment_batch_size: int = Field(
        default=100,
        description="Enrichment batch size"
    )

    # API Configuration
    api_host: str = Field(
        default="0.0.0.0",
        description="API host"
    )
    api_port: int = Field(
        default=8001,
        description="API port"
    )
    api_workers: int = Field(
        default=4,
        description="API workers"
    )

    # Streaming Integration
    streaming_kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers for streaming"
    )
    streaming_events_topic: str = Field(
        default="retention.events.processed",
        description="Processed events topic"
    )
    streaming_consumer_group: str = Field(
        default="cdp-engine",
        description="Kafka consumer group for CDP"
    )


@lru_cache
def get_cdp_settings() -> CDPSettings:
    return CDPSettings()