"""
Engagement service models: Email, SMS, Push, Flows, Templates, Deliverability.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index, Enum as SQLEnum, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from .base import SoftDeleteModel, TenantMixin


class EmailTemplate(SoftDeleteModel):
    """Email template with MJML/HTML content."""
    __tablename__ = "email_templates"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    # Content
    subject: Mapped[str] = mapped_column(String(998), nullable=False)
    preview_text: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    mjml_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Variables
    variables: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Metadata
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Relationships
    campaigns: Mapped[List["EmailCampaign"]] = relationship("EmailCampaign", back_populates="template")
    
    __table_args__ = (
        Index("ix_email_templates_client_slug", "client_id", "slug", unique=True),
    )


class EmailCampaign(SoftDeleteModel):
    """Email campaign."""
    __tablename__ = "email_campaigns"
    
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    segment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customer_segments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="regular", nullable=False)  # regular, ab_test, rss, automated
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False, index=True)
    
    # Content (can override template)
    subject: Mapped[str] = mapped_column(String(998), nullable=False)
    preview_text: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    from_name: Mapped[str] = mapped_column(String(100), nullable=False)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    reply_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # A/B Test
    ab_test_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Tracking
    track_opens: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    track_clicks: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    track_plaintext_clicks: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Stats
    recipient_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stats: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Settings
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Relationships
    template: Mapped[Optional["EmailTemplate"]] = relationship("EmailTemplate", back_populates="campaigns")
    messages: Mapped[List["EmailMessage"]] = relationship("EmailMessage", back_populates="campaign", cascade="all, delete-orphan")
    ab_variants: Mapped[List["EmailCampaign"]] = relationship(
        "EmailCampaign",
        backref="parent_campaign",
        remote_side="EmailCampaign.id",
        cascade="all, delete-orphan",
    )
    
    __table_args__ = (
        Index("ix_email_campaigns_status_scheduled", "status", "scheduled_at"),
    )


class EmailMessage(SoftDeleteModel):
    """Individual email message."""
    __tablename__ = "email_messages"
    
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    flow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("flow_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Recipient
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    recipient_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Content
    subject: Mapped[str] = mapped_column(String(998), nullable=False)
    preview_text: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Headers
    headers: Mapped[Dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Provider
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False, index=True)
    
    # Timestamps
    queued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    bounced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    complained_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    unsubscribed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Bounce details
    bounce_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # hard, soft, block, technical
    bounce_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bounce_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Click tracking
    click_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    click_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Attribution
    attribution_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    revenue_attributed: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    campaign: Mapped[Optional["EmailCampaign"]] = relationship("EmailCampaign", back_populates="messages")
    events: Mapped[List["EmailEvent"]] = relationship("EmailEvent", back_populates="message", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_email_messages_campaign_status", "campaign_id", "status"),
        Index("ix_email_messages_customer_status", "customer_id", "status"),
    )


class EmailEvent(SoftDeleteModel):
    """Email event for tracking."""
    __tablename__ = "email_events"
    
    message_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    flow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("flow_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # sent, delivered, opened, clicked, bounced, complained, unsubscribed
    
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # Event data
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    geo: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Event-specific
    bounce_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bounce_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    click_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    __table_args__ = (
        Index("ix_email_events_type_timestamp", "event_type", "timestamp"),
    )


# SMS Models
class SMSTemplate(SoftDeleteModel):
    """SMS template."""
    __tablename__ = "sms_templates"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    __table_args__ = (
        Index("ix_sms_templates_client_slug", "client_id", "slug", unique=True),
    )


class SMSCampaign(SoftDeleteModel):
    """SMS campaign."""
    __tablename__ = "sms_campaigns"
    
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sms_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    segment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customer_segments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False, index=True)
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    from_number: Mapped[str] = mapped_column(String(50), nullable=False)
    
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    recipient_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stats: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    __table_args__ = (
        Index("ix_sms_campaigns_status_scheduled", "status", "scheduled_at"),
    )


class SMSMessage(SoftDeleteModel):
    """Individual SMS message."""
    __tablename__ = "sms_messages"
    
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sms_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    flow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("flow_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sms_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    recipient_phone: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    recipient_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    from_number: Mapped[str] = mapped_column(String(50), nullable=False)
    
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False, index=True)
    
    queued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    segments: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    cost: Mapped[float] = mapped_column(Numeric(10, 6), default=0, nullable=False)
    
    attribution_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    revenue_attributed: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    __table_args__ = (
        Index("ix_sms_messages_campaign_status", "campaign_id", "status"),
    )


# Push Models
class PushTemplate(SoftDeleteModel):
    """Push notification template."""
    __tablename__ = "push_templates"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    action_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    actions: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    variables: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    __table_args__ = (
        Index("ix_push_templates_client_slug", "client_id", "slug", unique=True),
    )


class PushCampaign(SoftDeleteModel):
    """Push notification campaign."""
    __tablename__ = "push_campaigns"
    
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("push_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    segment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customer_segments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False, index=True)
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    action_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    recipient_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stats: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    __table_args__ = (
        Index("ix_push_campaigns_status_scheduled", "status", "scheduled_at"),
    )


class PushMessage(SoftDeleteModel):
    """Individual push notification message."""
    __tablename__ = "push_messages"
    
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("push_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    flow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("flow_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("push_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    recipient_token: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # web, ios, android
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    action_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False, index=True)
    
    queued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    attribution_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    revenue_attributed: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    __table_args__ = (
        Index("ix_push_messages_campaign_status", "campaign_id", "status"),
    )


# Flow Models
class FlowDefinition(SoftDeleteModel):
    """Flow/automation definition."""
    __tablename__ = "flow_definitions"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False, index=True)  # draft, live, paused, archived
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Trigger
    trigger_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # event, date, segment, api, webhook
    trigger_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Definition (React Flow JSON)
    nodes: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    edges: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    viewport: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Settings
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Status timestamps
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Stats
    total_entries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_completions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Relationships
    executions: Mapped[List["FlowExecution"]] = relationship("FlowExecution", back_populates="flow", cascade="all, delete-orphan")
    messages: Mapped[List["EmailMessage"]] = relationship("EmailMessage", back_populates="flow")
    push_messages: Mapped[List["PushMessage"]] = relationship("PushMessage", back_populates="flow")
    
    __table_args__ = (
        Index("ix_flow_definitions_client_slug", "client_id", "slug", unique=True),
    )


class FlowExecution(SoftDeleteModel):
    """Flow execution instance."""
    __tablename__ = "flow_executions"
    
    flow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("flow_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    trigger_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    context: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False, index=True)  # running, completed, failed, paused
    current_node_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_step_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Revenue attribution
    revenue_attributed: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Relationships
    flow: Mapped["FlowDefinition"] = relationship("FlowDefinition", back_populates="executions")
    node_executions: Mapped[List["FlowNodeExecution"]] = relationship("FlowNodeExecution", back_populates="execution", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_flow_executions_flow_status", "flow_id", "status"),
        Index("ix_flow_executions_customer", "customer_id"),
    )


class FlowNodeExecution(SoftDeleteModel):
    """Individual node execution within a flow."""
    __tablename__ = "flow_node_executions"
    
    execution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("flow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, running, completed, failed, skipped
    input_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    output_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    execution: Mapped["FlowExecution"] = relationship("FlowExecution", back_populates="node_executions")
    
    __table_args__ = (
        Index("ix_flow_node_executions_execution", "execution_id"),
    )


# Template Components
class TemplateComponent(SoftDeleteModel):
    """Reusable template component."""
    __tablename__ = "template_components"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Component definition
    mjml_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    css: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Props schema
    props_schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    default_props: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Preview
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    preview_props: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    __table_args__ = (
        Index("ix_template_components_client_slug", "client_id", "slug", unique=True),
    )


# Deliverability
class DeliverabilityConfig(SoftDeleteModel):
    """Deliverability configuration for a client."""
    __tablename__ = "deliverability_configs"
    
    # DKIM
    dkim_selector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dkim_private_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dkim_public_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dkim_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dkim_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # SPF
    spf_record: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    spf_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # DMARC
    dmarc_record: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dmarc_policy: Mapped[str] = mapped_column(String(20), default="none", nullable=False)
    dmarc_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Tracking domain
    tracking_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tracking_domain_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tracking_domain_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # IP Pool
    dedicated_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    ip_pool_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ip_warmup_schedule: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    ip_warmup_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Settings
    auto_warmup: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    bounce_threshold: Mapped[float] = mapped_column(Numeric(5, 2), default=5.0, nullable=False)  # percentage
    complaint_threshold: Mapped[float] = mapped_column(Numeric(5, 2), default=0.1, nullable=False)
    
    # Monitoring
    seed_list_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    seed_list_emails: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Relationships
    events: Mapped[List["DeliverabilityEvent"]] = relationship("DeliverabilityEvent", back_populates="config", cascade="all, delete-orphan")


class DeliverabilityEvent(SoftDeleteModel):
    """Deliverability event (bounce, complaint, spam report, etc.)."""
    __tablename__ = "deliverability_events"
    
    config_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("deliverability_configs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # bounce, complaint, delivery, open, click, unsubscribe
    event_subtype: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Details
    bounce_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bounce_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bounce_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    complaint_feedback_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Analysis
    severity: Mapped[str] = mapped_column(String(20), default="info", nullable=False)  # info, warning, critical
    action_taken: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    auto_suppressed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Raw data
    raw_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    __table_args__ = (
        Index("ix_deliverability_events_type_timestamp", "event_type", "timestamp"),
    )


class SuppressionList(SoftDeleteModel):
    """Email suppression list."""
    __tablename__ = "suppression_lists"
    
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    reason: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # bounce, complaint, unsubscribe, manual, list_unsubscribe
    source: Mapped[str] = mapped_column(String(50), default="auto", nullable=False)  # auto, manual, import
    
    # Details
    bounce_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bounce_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_bounce_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    added_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    added_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[added_by_id])
    
    __table_args__ = (
        Index("ix_suppression_lists_client_email", "client_id", "email", unique=True),
        Index("ix_suppression_lists_reason_active", "reason", "is_active"),
    )
