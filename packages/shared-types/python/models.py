"""
Shared types for retention analytics platform.

These types are used across Python services and can be exported to TypeScript
for frontend use.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict
from pydantic_extra_types.payment import PaymentCardBrand
from pydantic_extra_types.color import Color


# ============================================================================
# Enums
# ============================================================================

class Platform(str, Enum):
    """Supported marketing/ecommerce platforms."""
    KLAVIYO = "klaviyo"
    ATTENTIVE = "attentive"
    POSTSCRIPT = "postscript"
    OMNISEND = "omnisend"
    SENDLANE = "sendlane"
    SHOPIFY = "shopify"
    RECHARGE = "recharge"
    SKIO = "skio"
    LOOP = "loop"
    STAY_AI = "stay_ai"
    ORDERGROOVE = "ordergroove"
    ALIA = "alia"
    SLACK = "slack"


class ConnectionStatus(str, Enum):
    """Connection status for platform integrations."""
    PENDING = "pending"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ERROR = "error"
    DISCONNECTED = "disconnected"
    EXPIRED = "expired"


class SyncStatus(str, Enum):
    """Sync job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class CampaignType(str, Enum):
    """Campaign types."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    FLOW = "flow"
    MANUAL = "manual"


class CampaignStatus(str, Enum):
    """Campaign status."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FlowStatus(str, Enum):
    """Flow status."""
    DRAFT = "draft"
    LIVE = "live"
    PAUSED = "paused"
    ARCHIVED = "archived"


class SubscriptionStatus(str, Enum):
    """Subscription status."""
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"
    TRIALING = "trialing"


class MessageChannel(str, Enum):
    """Message channel."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class MessageStatus(str, Enum):
    """Message delivery status."""
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    SPAM = "spam"
    UNSUBSCRIBED = "unsubscribed"
    FAILED = "failed"


class RFMSegment(str, Enum):
    """RFM segment names."""
    CHAMPIONS = "champions"
    LOYAL = "loyal"
    POTENTIAL_LOYALISTS = "potential_loyalists"
    NEW_CUSTOMERS = "new_customers"
    PROMISING = "promising"
    NEED_ATTENTION = "need_attention"
    ABOUT_TO_SLEEP = "about_to_sleep"
    AT_RISK = "at_risk"
    CANNOT_LOSE = "cannot_lose"
    HIBERNATING = "hibernating"
    LOST = "lost"


class ReportFormat(str, Enum):
    """Report output format."""
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    CSV = "csv"


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class UserRole(str, Enum):
    """User roles within an agency."""
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"
    CLIENT = "client"


# ============================================================================
# Core Models
# ============================================================================

class TenantContext(BaseModel):
    """Multi-tenant context for requests."""
    agency_id: UUID
    client_id: Optional[UUID] = None
    user_id: UUID
    roles: List[UserRole] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AgencyBase(BaseModel):
    """Base agency model."""
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9-]+$", max_length=100)
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[Color] = None
    secondary_color: Optional[Color] = None
    white_label_domain: Optional[str] = None
    white_label_enabled: bool = False
    timezone: str = Field(default="UTC")
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    settings: Dict[str, Any] = Field(default_factory=dict)


class AgencyCreate(AgencyBase):
    """Agency creation model."""
    owner_email: str
    owner_name: str
    owner_password: str


class AgencyUpdate(BaseModel):
    """Agency update model."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[Color] = None
    secondary_color: Optional[Color] = None
    white_label_domain: Optional[str] = None
    white_label_enabled: Optional[bool] = None
    timezone: Optional[str] = None
    currency: Optional[str] = Field(default=None, pattern=r"^[A-Z]{3}$")
    settings: Optional[Dict[str, Any]] = None


class Agency(AgencyBase):
    """Full agency model."""
    id: UUID
    owner_id: UUID
    billing_customer_id: Optional[str] = None
    subscription_status: str = "trial"
    trial_ends_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    """Base user model."""
    email: str
    name: str
    avatar_url: Optional[str] = None
    timezone: str = Field(default="UTC")
    locale: str = Field(default="en")


class UserCreate(UserBase):
    """User creation model."""
    password: str
    role: UserRole = UserRole.ANALYST
    agency_id: UUID


class UserUpdate(BaseModel):
    """User update model."""
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class User(UserBase):
    """Full user model."""
    id: UUID
    agency_id: UUID
    role: UserRole
    is_active: bool = True
    mfa_enabled: bool = False
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientBase(BaseModel):
    """Base client (sub-tenant) model."""
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9-]+$", max_length=100)
    shop_domain: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    timezone: str = Field(default="UTC")
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    settings: Dict[str, Any] = Field(default_factory=dict)
    attribution_config: Dict[str, Any] = Field(default_factory=dict)


class ClientCreate(ClientBase):
    """Client creation model."""
    pass


class ClientUpdate(BaseModel):
    """Client update model."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    shop_domain: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = Field(default=None, pattern=r"^[A-Z]{3}$")
    settings: Optional[Dict[str, Any]] = None
    attribution_config: Optional[Dict[str, Any]] = None


class Client(ClientBase):
    """Full client model."""
    id: UUID
    agency_id: UUID
    is_active: bool = True
    last_sync_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Connection Models
# ============================================================================

class ConnectionBase(BaseModel):
    """Base platform connection model."""
    platform: Platform
    external_account_id: str
    account_name: Optional[str] = None
    auth_type: str = "oauth"  # oauth, api_key
    config: Dict[str, Any] = Field(default_factory=dict)
    sync_enabled: bool = True
    sync_frequency_hours: int = 24
    backfill_enabled: bool = True
    backfill_days: int = 365


class ConnectionCreate(ConnectionBase):
    """Connection creation model."""
    credentials: Dict[str, Any]  # Encrypted before storage


class ConnectionUpdate(BaseModel):
    """Connection update model."""
    account_name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    sync_enabled: Optional[bool] = None
    sync_frequency_hours: Optional[int] = None
    backfill_enabled: Optional[bool] = None
    backfill_days: Optional[int] = None
    credentials: Optional[Dict[str, Any]] = None


class Connection(ConnectionBase):
    """Full connection model."""
    id: UUID
    client_id: UUID
    status: ConnectionStatus = ConnectionStatus.PENDING
    last_sync_at: Optional[datetime] = None
    last_successful_sync_at: Optional[datetime] = None
    last_error: Optional[str] = None
    sync_cursor: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SyncJobBase(BaseModel):
    """Base sync job model."""
    platform: Platform
    sync_type: Literal["incremental", "full", "backfill"] = "incremental"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    records_processed: int = 0
    records_synced: int = 0
    records_failed: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SyncJob(SyncJobBase):
    """Full sync job model."""
    id: UUID
    client_id: UUID
    connection_id: UUID
    status: SyncStatus = SyncStatus.PENDING
    triggered_by: Literal["schedule", "manual", "webhook", "backfill"] = "schedule"
    progress: float = 0.0
    current_step: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Normalized Data Models
# ============================================================================

class CustomerBase(BaseModel):
    """Base customer model."""
    external_id: str
    email: Optional[str] = None
    email_hash: Optional[str] = None
    phone: Optional[str] = None
    phone_hash: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None


class Customer(CustomerBase):
    """Full customer model."""
    id: UUID
    client_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderBase(BaseModel):
    """Base order model."""
    external_id: str
    order_number: str
    customer_external_id: str
    total: Decimal
    currency: str = "USD"
    subtotal: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    shipping: Optional[Decimal] = None
    discount: Optional[Decimal] = None
    status: str
    placed_at: datetime
    processed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    shipping_address: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, Any]] = None
    attribution: Optional[Dict[str, Any]] = None


class Order(OrderBase):
    """Full order model."""
    id: UUID
    client_id: UUID
    customer_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageBase(BaseModel):
    """Base message model."""
    external_id: str
    campaign_external_id: Optional[str] = None
    flow_external_id: Optional[str] = None
    channel: MessageChannel
    subject: Optional[str] = None
    preview_text: Optional[str] = None
    content: Optional[str] = None
    recipient_external_id: str
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    unsubscribed_at: Optional[datetime] = None
    status: MessageStatus = MessageStatus.SENT
    revenue_attributed: Decimal = Decimal("0")
    attribution_data: Dict[str, Any] = Field(default_factory=dict)


class Message(MessageBase):
    """Full message model."""
    id: UUID
    client_id: UUID
    customer_id: Optional[UUID] = None
    campaign_id: Optional[UUID] = None
    flow_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignBase(BaseModel):
    """Base campaign model."""
    external_id: str
    name: str
    type: CampaignType
    status: CampaignStatus
    subject: Optional[str] = None
    preview_text: Optional[str] = None
    content: Optional[str] = None
    sent_at: Optional[datetime] = None
    stats: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class Campaign(CampaignBase):
    """Full campaign model."""
    id: UUID
    client_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FlowBase(BaseModel):
    """Base flow model."""
    external_id: str
    name: str
    status: FlowStatus
    trigger_type: str
    trigger_config: Dict[str, Any] = Field(default_factory=dict)
    branches: List[Dict[str, Any]] = Field(default_factory=list)


class Flow(FlowBase):
    """Full flow model."""
    id: UUID
    client_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionBase(BaseModel):
    """Base subscription model."""
    external_id: str
    customer_external_id: str
    product_external_id: str
    product_name: str
    variant_external_id: Optional[str] = None
    variant_name: Optional[str] = None
    status: SubscriptionStatus
    billing_interval: str  # monthly, quarterly, yearly
    billing_interval_count: int = 1
    price: Decimal
    currency: str = "USD"
    quantity: int = 1
    started_at: datetime
    cancelled_at: Optional[datetime] = None
    next_billing_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    attribution: Optional[Dict[str, Any]] = None


class Subscription(SubscriptionBase):
    """Full subscription model."""
    id: UUID
    client_id: UUID
    customer_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventBase(BaseModel):
    """Base event model (for aggregated metrics)."""
    event_type: str
    timestamp: datetime
    customer_external_id: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    attribution: Optional[Dict[str, Any]] = None


class Event(EventBase):
    """Full event model."""
    id: UUID
    client_id: UUID
    customer_id: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Computed Metrics Models
# ============================================================================

class DailyMetrics(BaseModel):
    """Daily aggregated metrics for a client."""
    client_id: UUID
    date: datetime
    # Revenue
    total_revenue: Decimal = Decimal("0")
    attributed_revenue: Decimal = Decimal("0")
    email_revenue: Decimal = Decimal("0")
    sms_revenue: Decimal = Decimal("0")
    push_revenue: Decimal = Decimal("0")
    organic_revenue: Decimal = Decimal("0")
    # Orders
    total_orders: int = 0
    new_customer_orders: int = 0
    returning_customer_orders: int = 0
    aov: Decimal = Decimal("0")
    # Customers
    new_customers: int = 0
    returning_customers: int = 0
    active_customers: int = 0
    # Email
    emails_sent: int = 0
    emails_delivered: int = 0
    emails_opened: int = 0
    emails_clicked: int = 0
    emails_bounced: int = 0
    emails_unsubscribed: int = 0
    email_open_rate: float = 0.0
    email_click_rate: float = 0.0
    # SMS
    sms_sent: int = 0
    sms_delivered: int = 0
    sms_clicked: int = 0
    sms_opted_out: int = 0
    # Subscriptions
    new_subscriptions: int = 0
    cancelled_subscriptions: int = 0
    active_subscriptions: int = 0
    subscription_revenue: Decimal = Decimal("0")
    mrr: Decimal = Decimal("0")
    # Meta
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class CohortRetention(BaseModel):
    """Cohort retention metrics."""
    client_id: UUID
    cohort_month: str  # YYYY-MM
    period: int  # 0, 1, 2, 3, 6, 12 months
    cohort_size: int
    retained_customers: int
    repeat_rate: float
    revenue_per_customer: Decimal
    avg_ltv: Decimal

    model_config = ConfigDict(from_attributes=True)


class RFMSegmentMetrics(BaseModel):
    """RFM segment metrics."""
    client_id: UUID
    segment: RFMSegment
    customer_count: int
    total_revenue: Decimal
    avg_order_value: Decimal
    avg_orders_per_customer: float
    days_since_last_order: float
    pct_of_customers: float
    pct_of_revenue: float

    model_config = ConfigDict(from_attributes=True)


class AttributionSummary(BaseModel):
    """Attribution summary by channel."""
    client_id: UUID
    date: datetime
    channel: str
    touchpoints: int
    attributed_revenue: Decimal
    attributed_orders: int
    roas: float
    cpa: Decimal

    model_config = ConfigDict(from_attributes=True)


class CampaignPerformance(BaseModel):
    """Campaign performance metrics."""
    campaign_id: UUID
    client_id: UUID
    name: str
    type: CampaignType
    sent_at: Optional[datetime]
    # Volume
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    bounced: int = 0
    unsubscribed: int = 0
    spam_complaints: int = 0
    # Rates
    delivery_rate: float = 0.0
    open_rate: float = 0.0
    click_rate: float = 0.0
    bounce_rate: float = 0.0
    unsubscribe_rate: float = 0.0
    spam_rate: float = 0.0
    # Revenue
    attributed_revenue: Decimal = Decimal("0")
    attributed_orders: int = 0
    revenue_per_recipient: Decimal = Decimal("0")
    roas: float = 0.0
    # Products
    products_purchased: List[Dict[str, Any]] = Field(default_factory=list)
    # Variants (A/B)
    variants: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class FlowPerformance(BaseModel):
    """Flow performance metrics."""
    flow_id: UUID
    client_id: UUID
    name: str
    status: FlowStatus
    # Aggregate
    total_entered: int = 0
    total_completed: int = 0
    total_revenue: Decimal = Decimal("0")
    # Per-message
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    # Branches
    branch_performance: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SubscriptionMetrics(BaseModel):
    """Subscription analytics metrics."""
    client_id: UUID
    date: datetime
    # Growth
    active_subscriptions: int = 0
    new_subscriptions: int = 0
    cancelled_subscriptions: int = 0
    net_starts: int = 0
    # Revenue
    mrr: Decimal = Decimal("0")
    arr: Decimal = Decimal("0")
    new_mrr: Decimal = Decimal("0")
    expansion_mrr: Decimal = Decimal("0")
    contraction_mrr: Decimal = Decimal("0")
    churned_mrr: Decimal = Decimal("0")
    # Churn
    churn_rate: float = 0.0
    revenue_churn_rate: float = 0.0
    # LTV
    avg_ltv: Decimal = Decimal("0")
    ltv_by_product: Dict[str, Decimal] = Field(default_factory=dict)
    # Conversion
    one_time_to_subscriber_rate: float = 0.0
    # Attribution
    marketing_attributed_subs: int = 0
    marketing_attributed_revenue: Decimal = Decimal("0")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Reporting Models
# ============================================================================

class ReportBase(BaseModel):
    """Base report model."""
    name: str
    description: Optional[str] = None
    format: ReportFormat = ReportFormat.PDF
    template: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    schedule: Optional[str] = None  # cron expression
    recipients: List[str] = Field(default_factory=list)
    client_ids: List[UUID] = Field(default_factory=list)


class ReportCreate(ReportBase):
    """Report creation model."""
    pass


class ReportUpdate(BaseModel):
    """Report update model."""
    name: Optional[str] = None
    description: Optional[str] = None
    format: Optional[ReportFormat] = None
    template: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = None
    recipients: Optional[List[str]] = None
    client_ids: Optional[List[UUID]] = None
    is_active: Optional[bool] = None


class Report(ReportBase):
    """Full report model."""
    id: UUID
    agency_id: UUID
    created_by: UUID
    is_active: bool = True
    last_generated_at: Optional[datetime] = None
    next_generation_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportRun(BaseModel):
    """Report generation run."""
    id: UUID
    report_id: UUID
    status: ReportStatus = ReportStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Alert Models
# ============================================================================

class AlertBase(BaseModel):
    """Base alert model."""
    name: str
    description: Optional[str] = None
    metric: str
    condition: str  # gt, lt, eq, gte, lte, change_pct
    threshold: Decimal
    window: str = "1d"  # 1h, 6h, 1d, 7d, 30d
    severity: AlertSeverity = AlertSeverity.WARNING
    channels: List[str] = Field(default_factory=list)  # email, slack, webhook
    client_ids: List[UUID] = Field(default_factory=list)  # empty = all


class AlertCreate(AlertBase):
    """Alert creation model."""
    pass


class AlertUpdate(BaseModel):
    """Alert update model."""
    name: Optional[str] = None
    description: Optional[str] = None
    metric: Optional[str] = None
    condition: Optional[str] = None
    threshold: Optional[Decimal] = None
    window: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    channels: Optional[List[str]] = None
    client_ids: Optional[List[UUID]] = None
    is_active: Optional[bool] = None


class Alert(AlertBase):
    """Full alert model."""
    id: UUID
    agency_id: UUID
    created_by: UUID
    is_active: bool = True
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertEvent(BaseModel):
    """Alert trigger event."""
    id: UUID
    alert_id: UUID
    client_id: UUID
    metric_value: Decimal
    threshold: Decimal
    severity: AlertSeverity
    message: str
    acknowledged: bool = False
    acknowledged_by: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# API Response Models
# ============================================================================

class PaginatedResponse(BaseModel):
    """Generic paginated response."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


class APIError(BaseModel):
    """API error response."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class HealthCheck(BaseModel):
    """Health check response."""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    timestamp: datetime
    checks: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# MCP Tool Models
# ============================================================================

class MCPToolInput(BaseModel):
    """Base input for MCP tools."""
    agency_id: Optional[str] = None
    client_id: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class RosterSummaryInput(MCPToolInput):
    """Input for get_roster_summary tool."""
    pass


class ClientMetricsInput(MCPToolInput):
    """Input for get_client_metrics tool."""
    client_id: str


class CampaignPerformanceInput(MCPToolInput):
    """Input for get_campaign_performance tool."""
    campaign_id: Optional[str] = None
    limit: int = 20


class FlowPerformanceInput(MCPToolInput):
    """Input for get_flow_performance tool."""
    flow_id: Optional[str] = None
    limit: int = 20


class RetentionCohortsInput(MCPToolInput):
    """Input for get_retention_cohorts tool."""
    cohort_months: int = 12


class RFMSegmentsInput(MCPToolInput):
    """Input for get_rfm_segments tool."""
    pass


class SubscriptionMetricsInput(MCPToolInput):
    """Input for get_subscription_metrics tool."""
    pass


class CreativeSearchInput(MCPToolInput):
    """Input for search_creatives tool."""
    query: str
    channel: Optional[MessageChannel] = None
    limit: int = 10