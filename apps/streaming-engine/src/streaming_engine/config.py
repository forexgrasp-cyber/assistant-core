"""
Streaming Engine Configuration
"""
from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StreamingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Kafka Configuration
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers"
    )
    kafka_security_protocol: str = Field(
        default="PLAINTEXT",
        description="Kafka security protocol"
    )
    kafka_sasl_mechanism: Optional[str] = Field(
        default=None,
        description="Kafka SASL mechanism"
    )
    kafka_sasl_username: Optional[str] = Field(
        default=None,
        description="Kafka SASL username"
    )
    kafka_sasl_password: Optional[str] = Field(
        default=None,
        description="Kafka SASL password"
    )

    # Consumer Group Configuration
    kafka_consumer_group: str = Field(
        default="streaming-engine",
        description="Kafka consumer group ID"
    )
    kafka_auto_offset_reset: str = Field(
        default="earliest",
        description="Kafka auto offset reset policy"
    )
    kafka_enable_auto_commit: bool = Field(
        default=True,
        description="Enable auto commit for consumers"
    )

    # Topic Configuration
    events_topic: str = Field(
        default="retention.events",
        description="Main events topic"
    )
    raw_events_topic: str = Field(
        default="retention.events.raw",
        description="Raw events topic for replay"
    )
    processed_events_topic: str = Field(
        default="retention.events.processed",
        description="Processed events topic"
    )
    dead_letter_topic: str = Field(
        default="retention.events.dlq",
        description="Dead letter queue topic"
    )

    # RisingWave Configuration
    risingwave_host: str = Field(
        default="localhost",
        description="RisingWave host"
    )
    risingwave_port: int = Field(
        default=4566,
        description="RisingWave port"
    )
    risingwave_database: str = Field(
        default="dev",
        description="RisingWave database"
    )
    risingwave_user: str = Field(
        default="root",
        description="RisingWave user"
    )
    risingwave_password: str = Field(
        default="",
        description="RisingWave password"
    )

    # RisingWave Connection Pool
    risingwave_pool_size: int = Field(
        default=10,
        description="RisingWave connection pool size"
    )
    risingwave_max_overflow: int = Field(
        default=20,
        description="RisingWave max overflow"
    )

    # Stream Processing Configuration
    stream_processing_batch_size: int = Field(
        default=1000,
        description="Batch size for stream processing"
    )
    stream_processing_interval_ms: int = Field(
        default=100,
        description="Processing interval in milliseconds"
    )
    stream_parallelism: int = Field(
        default=4,
        description="Parallelism for stream processing"
    )

    # Exactly-once semantics
    exactly_once_enabled: bool = Field(
        default=True,
        description="Enable exactly-once processing semantics"
    )
    transaction_timeout_ms: int = Field(
        default=30000,
        description="Transaction timeout in milliseconds"
    )

    # Window Configuration
    tumbling_window_size_seconds: int = Field(
        default=60,
        description="Tumbling window size in seconds"
    )
    hopping_window_size_seconds: int = Field(
        default=300,
        description="Hopping window size in seconds"
    )
    hopping_window_advance_seconds: int = Field(
        default=60,
        description="Hopping window advance in seconds"
    )
    session_window_gap_seconds: int = Field(
        default=1800,
        description="Session window gap in seconds"
    )

    # State Store Configuration
    state_store_type: str = Field(
        default="rocksdb",
        description="State store type (rocksdb, memory)"
    )
    state_store_path: str = Field(
        default="/var/lib/streaming-engine/state",
        description="State store path"
    )
    state_ttl_days: int = Field(
        default=7,
        description="State TTL in days"
    )

    # Monitoring
    metrics_port: int = Field(
        default=9090,
        description="Metrics port"
    )
    health_check_port: int = Field(
        default=8080,
        description="Health check port"
    )

    # Schema Registry
    schema_registry_url: Optional[str] = Field(
        default=None,
        description="Schema registry URL (Confluent)"
    )
    schema_registry_auth: Optional[str] = Field(
        default=None,
        description="Schema registry authentication"
    )


@lru_cache
def get_streaming_settings() -> StreamingSettings:
    return StreamingSettings()