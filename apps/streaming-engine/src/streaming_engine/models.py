"""
Streaming Engine Event Models
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class EventMetadata(BaseModel):
    """Event metadata"""
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: str
    event_version: str = "1.0"
    source: str
    source_version: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    received_at: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[uuid.UUID] = None
    causation_id: Optional[uuid.UUID] = None
    tags: Dict[str, str] = Field(default_factory=dict)


class UserIdentity(BaseModel):
    """User identity for event attribution"""
    user_id: Optional[str] = None
    anonymous_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    external_ids: Dict[str, str] = Field(default_factory=dict)


class EventContext(BaseModel):
    """Event context"""
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    screen_resolution: Optional[str] = None
    viewport_size: Optional[str] = None
    referrer: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_term: Optional[str] = None
    utm_content: Optional[str] = None


class BaseEvent(BaseModel):
    """Base event model"""
    metadata: EventMetadata
    user: Optional[UserIdentity] = None
    context: Optional[EventContext] = None
    properties: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v),
        }
    )


class PageViewEvent(BaseEvent):
    """Page view event"""
    metadata: EventMetadata = Field(default_factory=lambda: EventMetadata(
        event_type="page_view",
        source="web"
    ))
    page_url: str
    page_title: Optional[str] = None
    page_path: Optional[str] = None
    referrer: Optional[str] = None
    duration_ms: Optional[int] = None


class TrackEvent(BaseEvent):
    """Custom track event"""
    metadata: EventMetadata = Field(default_factory=lambda: EventMetadata(
        event_type="track",
        source="api"
    ))
    event_name: str
    value: Optional[float] = None


class IdentifyEvent(BaseEvent):
    """User identify event"""
    metadata: EventMetadata = Field(default_factory=lambda: EventMetadata(
        event_type="identify",
        source="api"
    ))
    user_id: str
    traits: Dict[str, Any] = Field(default_factory=dict)


class GroupEvent(BaseEvent):
    """Group event"""
    metadata: EventMetadata = Field(default_factory=lambda: EventMetadata(
        event_type="group",
        source="api"
    ))
    group_id: str
    traits: Dict[str, Any] = Field(default_factory=dict)


class AliasEvent(BaseEvent):
    """Alias event"""
    metadata: EventMetadata = Field(default_factory=lambda: EventMetadata(
        event_type="alias",
        source="api"
    ))
    previous_id: str
    user_id: str


class ScreenEvent(BaseEvent):
    """Screen view event (mobile)"""
    metadata: EventMetadata = Field(default_factory=lambda: EventMetadata(
        event_type="screen",
        source="mobile"
    ))
    screen_name: str
    screen_class: Optional[str] = None


class EcommerceEvent(BaseEvent):
    """E-commerce event"""
    metadata: EventMetadata = Field(default_factory=lambda: EventMetadata(
        event_type="ecommerce",
        source="api"
    ))
    action: Literal[
        "product_viewed",
        "product_added",
        "product_removed",
        "cart_viewed",
        "checkout_started",
        "checkout_completed",
        "order_completed",
        "order_refunded",
        "order_cancelled",
        "payment_info_added",
        "promotion_viewed",
        "promotion_clicked"
    ]
    products: List[Dict[str, Any]] = Field(default_factory=list)
    cart_id: Optional[str] = None
    order_id: Optional[str] = None
    revenue: Optional[float] = None
    currency: str = "USD"
    shipping: Optional[float] = None
    tax: Optional[float] = None
    discount: Optional[float] = None
    coupon: Optional[str] = None
    payment_method: Optional[str] = None
    shipping_method: Optional[str] = None


class EventEnvelope(BaseModel):
    """Event envelope for Kafka transport"""
    event: BaseEvent
    schema_version: str = "1.0"
    partition_key: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)


class ProcessedEvent(BaseModel):
    """Processed event with enriched data"""
    original_event: BaseEvent
    enriched_data: Dict[str, Any] = Field(default_factory=dict)
    derived_properties: Dict[str, Any] = Field(default_factory=dict)
    user_profile: Optional[Dict[str, Any]] = None
    session_data: Optional[Dict[str, Any]] = None
    attribution: Optional[Dict[str, Any]] = None
    predictions: Optional[Dict[str, Any]] = None
    anomalies: Optional[List[Dict[str, Any]]] = None
    processing_timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_duration_ms: Optional[int] = None


class StreamWindow(BaseModel):
    """Stream window definition"""
    window_type: Literal["tumbling", "hopping", "session"]
    window_size_seconds: int
    window_advance_seconds: Optional[int] = None
    session_gap_seconds: Optional[int] = None
    start_time: datetime
    end_time: datetime


class AggregationResult(BaseModel):
    """Stream aggregation result"""
    window: StreamWindow
    dimensions: Dict[str, str]
    metrics: Dict[str, float]
    count: int
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class StreamCheckpoint(BaseModel):
    """Stream processing checkpoint"""
    topic: str
    partition: int
    offset: int
    timestamp: datetime
    processed_count: int
    last_event_timestamp: Optional[datetime] = None


class DeadLetterEvent(BaseModel):
    """Dead letter event"""
    original_event: EventEnvelope
    error: str
    error_type: str
    retry_count: int = 0
    first_failed_at: datetime = Field(default_factory=datetime.utcnow)
    last_failed_at: datetime = Field(default_factory=datetime.utcnow)
    processing_context: Dict[str, Any] = Field(default_factory=dict)