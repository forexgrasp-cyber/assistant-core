"""
Email service models.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, EmailStr
from pydantic_extra_types.color import Color


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CampaignType(str, Enum):
    REGULAR = "regular"
    A_B_TEST = "ab_test"
    RSS = "rss"
    AUTOMATED = "automated"


class MessageStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    UNSUBSCRIBED = "unsubscribed"
    FAILED = "failed"


class BounceType(str, Enum):
    HARD = "hard"
    SOFT = "soft"
    BLOCK = "block"
    TECHNICAL = "technical"


class EmailCampaignBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    subject: str = Field(min_length=1, max_length=998)
    preview_text: Optional[str] = Field(default=None, max_length=200)
    from_name: str = Field(min_length=1, max_length=100)
    from_email: EmailStr
    reply_to: Optional[EmailStr] = None
    type: CampaignType = CampaignType.REGULAR
    html_content: str
    text_content: Optional[str] = None
    template_id: Optional[UUID] = None
    segment_id: Optional[UUID] = None
    tags: List[str] = Field(default_factory=list)
    settings: Dict[str, Any] = Field(default_factory=dict)
    ab_test_config: Optional[Dict[str, Any]] = None


class EmailCampaignCreate(EmailCampaignBase):
    client_id: UUID
    scheduled_at: Optional[datetime] = None


class EmailCampaignUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    subject: Optional[str] = Field(default=None, min_length=1, max_length=998)
    preview_text: Optional[str] = Field(default=None, max_length=200)
    from_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    from_email: Optional[EmailStr] = None
    reply_to: Optional[EmailStr] = None
    html_content: Optional[str] = None
    text_content: Optional[str] = None
    template_id: Optional[UUID] = None
    segment_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    settings: Optional[Dict[str, Any]] = None
    ab_test_config: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None


class EmailCampaign(EmailCampaignBase):
    id: UUID
    client_id: UUID
    status: CampaignStatus = CampaignStatus.DRAFT
    sent_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    recipient_count: int = 0
    stats: Dict[str, Any] = Field(default_factory=dict)
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailTemplateBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    channel: Literal["email"] = "email"
    subject: str = Field(min_length=1, max_length=998)
    preview_text: Optional[str] = Field(default=None, max_length=200)
    html_content: str
    text_content: Optional[str] = None
    mjml_content: Optional[str] = None
    variables: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class EmailTemplateCreate(EmailTemplateBase):
    client_id: UUID


class EmailTemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    subject: Optional[str] = Field(default=None, min_length=1, max_length=998)
    preview_text: Optional[str] = Field(default=None, max_length=200)
    html_content: Optional[str] = None
    text_content: Optional[str] = None
    mjml_content: Optional[str] = None
    variables: Optional[List[str]] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class EmailTemplate(EmailTemplateBase):
    id: UUID
    client_id: UUID
    version: int = 1
    is_active: bool = True
    thumbnail_url: Optional[str] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailMessageBase(BaseModel):
    campaign_id: UUID
    template_id: Optional[UUID] = None
    recipient_email: EmailStr
    recipient_name: Optional[str] = None
    recipient_id: Optional[UUID] = None  # Customer ID
    subject: str
    html_content: str
    text_content: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EmailMessage(EmailMessageBase):
    id: UUID
    client_id: UUID
    flow_id: Optional[UUID] = None
    status: MessageStatus = MessageStatus.QUEUED
    provider: Optional[str] = None
    provider_message_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    complained_at: Optional[datetime] = None
    unsubscribed_at: Optional[datetime] = None
    bounce_type: Optional[BounceType] = None
    bounce_reason: Optional[str] = None
    click_url: Optional[str] = None
    attribution_data: Dict[str, Any] = Field(default_factory=dict)
    revenue_attributed: Decimal = Decimal("0")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SendResult(BaseModel):
    success: bool
    message_id: Optional[UUID] = None
    provider_message_id: Optional[str] = None
    error: Optional[str] = None
    recipient: Optional[str] = None


class BatchSendResult(BaseModel):
    total: int
    successful: int
    failed: int
    results: List[SendResult]


class CampaignStats(BaseModel):
    campaign_id: UUID
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    bounced: int = 0
    complained: int = 0
    unsubscribed: int = 0
    failed: int = 0
    delivery_rate: float = 0.0
    open_rate: float = 0.0
    click_rate: float = 0.0
    bounce_rate: float = 0.0
    complaint_rate: float = 0.0
    unsubscribe_rate: float = 0.0
    attributed_revenue: Decimal = Decimal("0")
    attributed_orders: int = 0
    revenue_per_recipient: Decimal = Decimal("0")
    roas: float = 0.0
    variants: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ABTestVariant(BaseModel):
    variant_id: str
    name: str
    subject: Optional[str] = None
    from_name: Optional[str] = None
    from_email: Optional[str] = None
    html_content: Optional[str] = None
    text_content: Optional[str] = None
    split_percentage: int
    stats: CampaignStats


class ABTestConfig(BaseModel):
    enabled: bool = True
    variants: List[ABTestVariant]
    winner_criteria: Literal["open_rate", "click_rate", "revenue"] = "click_rate"
    test_size_percentage: int = 20
    winner_selection_delay_hours: int = 24


class EmailEvent(BaseModel):
    """Event emitted by email service for analytics pipeline."""
    event_type: str  # sent, delivered, opened, clicked, bounced, complained, unsubscribed
    client_id: UUID
    campaign_id: Optional[UUID] = None
    flow_id: Optional[UUID] = None
    template_id: Optional[UUID] = None
    message_id: UUID
    recipient_email: str
    recipient_id: Optional[UUID] = None
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # Event-specific fields
    bounce_type: Optional[BounceType] = None
    bounce_reason: Optional[str] = None
    click_url: Optional[str] = None
    user_agent: Optional[str] = None
    ip: Optional[str] = None
    geo: Optional[Dict[str, str]] = None