"""
Webhook models: Ingress, Egress, DLQ, Signatures, Retries.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index, Enum as SQLEnum, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from .base import SoftDeleteModel


class WebhookEndpoint(SoftDeleteModel):
    """Webhook endpoint for receiving external events."""
    __tablename__ = "webhook_endpoints"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Path & Method
    path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), default="POST", nullable=False)
    
    # Authentication
    auth_type: Mapped[str] = mapped_column(String(50), default="signature", nullable=False)  # none, signature, bearer, api_key, hmac
    secret_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    api_key_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Validation
    required_headers: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    allowed_ips: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    blocked_ips: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Rate limiting
    rate_limit: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)  # per minute
    rate_limit_window: Mapped[int] = mapped_column(Integer, default=60, nullable=False)  # seconds
    
    # Processing
    processor: Mapped[str] = mapped_column(String(100), nullable=False)  # email, sms, order, subscription, custom
    processor_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Deduplication
    deduplication_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deduplication_window_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    deduplication_key_header: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    deduplication_key_json_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Response
    response_template: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    response_status: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    response_headers: Mapped[Dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Retry
    retry_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_backoff_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    retry_backoff_multiplier: Mapped[float] = mapped_column(Numeric(3, 1), default=2.0, nullable=False)
    max_retry_delay_seconds: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    
    # Dead letter queue
    dlq_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    dlq_retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    
    # Monitoring
    alert_on_failure: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    alert_threshold: Mapped[int] = mapped_column(Integer, default=5, nullable=False)  # failures per window
    alert_window_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Stats
    total_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dlq_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_request_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    events: Mapped[List["WebhookEvent"]] = relationship("WebhookEvent", back_populates="endpoint", cascade="all, delete-orphan")
    deliveries: Mapped[List["WebhookDelivery"]] = relationship("WebhookDelivery", back_populates="endpoint", cascade="all, delete-orphan")
    dlq_entries: Mapped[List["DeadLetterQueue"]] = relationship("DeadLetterQueue", back_populates="endpoint", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_webhook_endpoints_path_method", "path", "method", unique=True),
        Index("ix_webhook_endpoints_processor", "processor"),
    )


class WebhookEvent(SoftDeleteModel):
    """Incoming webhook event."""
    __tablename__ = "webhook_events"
    
    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("webhook_endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Request
    request_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    request_method: Mapped[str] = mapped_column(String(10), nullable=False)
    request_path: Mapped[str] = mapped_column(String(500), nullable=False)
    request_headers: Mapped[Dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    request_body: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    request_query: Mapped[Dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    
    # Deduplication
    deduplication_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    original_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("webhook_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Processing
    status: Mapped[str] = mapped_column(String(20), default="received", nullable=False, index=True)  # received, processing, completed, failed, skipped
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Result
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Retry
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    
    # Response
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Timestamps
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    endpoint: Mapped["WebhookEndpoint"] = relationship("WebhookEndpoint", back_populates="events")
    deliveries: Mapped[List["WebhookDelivery"]] = relationship("WebhookDelivery", back_populates="event", cascade="all, delete-orphan")
    dlq_entry: Mapped[Optional["DeadLetterQueue"]] = relationship("DeadLetterQueue", back_populates="event", uselist=False)
    
    __table_args__ = (
        Index("ix_webhook_events_endpoint_status", "endpoint_id", "status"),
        Index("ix_webhook_events_dedup_key", "deduplication_key"),
    )


class WebhookDelivery(SoftDeleteModel):
    """Outbound webhook delivery."""
    __tablename__ = "webhook_deliveries"
    
    endpoint_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("webhook_endpoints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("webhook_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Target
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), default="POST", nullable=False)
    headers: Mapped[Dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    body: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Authentication
    auth_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    auth_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Retry
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)  # pending, sent, delivered, failed, cancelled
    
    # Request/Response
    request_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    request_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[Dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    response_body: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Error
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Timing
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    endpoint: Mapped[Optional["WebhookEndpoint"]] = relationship("WebhookEndpoint", back_populates="deliveries")
    event: Mapped[Optional["WebhookEvent"]] = relationship("WebhookEvent", back_populates="deliveries")
    retries: Mapped[List["WebhookRetry"]] = relationship("WebhookRetry", back_populates="delivery", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_webhook_deliveries_status_next_retry", "status", "next_retry_at"),
        Index("ix_webhook_deliveries_endpoint_status", "endpoint_id", "status"),
    )


class WebhookRetry(SoftDeleteModel):
    """Webhook delivery retry."""
    __tablename__ = "webhook_retries"
    
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("webhook_deliveries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Request
    request_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    request_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Response
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[Dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    response_body: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Error
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Result
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    delivery: Mapped["WebhookDelivery"] = relationship("WebhookDelivery", back_populates="retries")
    
    __table_args__ = (
        Index("ix_webhook_retries_delivery_attempt", "delivery_id", "attempt", unique=True),
    )


class DeadLetterQueue(SoftDeleteModel):
    """Dead letter queue for failed webhook events."""
    __tablename__ = "dead_letter_queue"
    
    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("webhook_endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("webhook_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    delivery_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("webhook_deliveries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Original request
    request_headers: Mapped[Dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    request_body: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    request_query: Mapped[Dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    
    # Failure details
    failure_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    failure_details: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Resolution
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)  # pending, investigating, resolved, discarded, replayed
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Replay
    replayed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    replayed_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("webhook_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    replay_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Timestamps
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    endpoint: Mapped["WebhookEndpoint"] = relationship("WebhookEndpoint", back_populates="dlq_entries")
    event: Mapped["WebhookEvent"] = relationship("WebhookEvent", back_populates="dlq_entry")
    delivery: Mapped[Optional["WebhookDelivery"]] = relationship("WebhookDelivery", foreign_keys=[delivery_id])
    resolved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[resolved_by_id])
    
    __table_args__ = (
        Index("ix_dlq_endpoint_status", "endpoint_id", "status"),
        Index("ix_dlq_received", "received_at"),
    )


class WebhookSignature(SoftDeleteModel):
    """Webhook signature verification record."""
    __tablename__ = "webhook_signatures"
    
    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("webhook_endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("webhook_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Signature
    signature_header: Mapped[str] = mapped_column(String(255), nullable=False)
    signature_value: Mapped[str] = mapped_column(String(500), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), default="hmac-sha256", nullable=False)
    
    # Verification
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expected_signature: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    timestamp_tolerance_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    
    # Timing
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    endpoint: Mapped["WebhookEndpoint"] = relationship("WebhookEndpoint")
    event: Mapped["WebhookEvent"] = relationship("WebhookEvent")
    
    __table_args__ = (
        Index("ix_webhook_signatures_endpoint_event", "endpoint_id", "event_id", unique=True),
    )
