"""Shared types used across services, workers, and frontend.

Defines the canonical domain models so services are not siloed: every package
imports the same entities, events, and payloads, and the frontend consumes the
same contracts via the API gateway.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class EntityType(str, Enum):
    """Canonical entity types handled by the dynamic entity kernel."""

    CLIENT = "client"
    CAMPAIGN = "campaign"
    FLOW = "flow"
    SUBSCRIPTION = "subscription"
    ORDER = "order"
    PRODUCT = "product"
    METRIC = "metric"
    REPORT = "report"
    TENANT = "tenant"
    USER = "user"


class EventType(str, Enum):
    """Canonical platform events that trigger workflows and pipelines."""

    CLIENT_CREATED = "client.created"
    CLIENT_UPDATED = "client.updated"
    CLIENT_CHURN_RISK = "client.churn_risk"
    CAMPAIGN_SENT = "campaign.sent"
    CAMPAIGN_BOUNCED = "campaign.bounced"
    CAMPAIGN_CLICKED = "campaign.clicked"
    FLOW_TRIGGERED = "flow.triggered"
    FLOW_STEP_COMPLETED = "flow.step_completed"
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    SUBSCRIPTION_PAST_DUE = "subscription.past_due"
    ORDER_PLACED = "order.placed"
    ORDER_ABANDONED_CART = "order.abandoned_cart"
    METRIC_COMPUTED = "metric.computed"
    REPORT_GENERATED = "report.generated"
    RETENTION_COHORT_READY = "retention.cohort_ready"

    # Competitor-parity events (Baremetrics Recover/Cancel Insights, Churnkey Cancel Flows/Payment Recovery,
    # ChurnZero health scores/playbooks, Vitally NPS/surveys)
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_RECOVERED = "payment.recovered"
    SUBSCRIPTION_PAUSED = "subscription.paused"
    SUBSCRIPTION_DOWNGRADED = "subscription.downgraded"
    SUBSCRIPTION_RENEWAL_DUE = "subscription.renewal_due"
    TRIAL_ENDING = "trial.ending"
    USAGE_DROPPED = "usage.dropped"
    FEATURE_UNUSED = "feature.unused"
    SEAT_OVERAGE = "account.seat_overage"
    CLIENT_REACTIVATED = "client.reactivated"
    NPS_SURVEY_DUE = "survey.nps_due"
    CSAT_SURVEY_DUE = "survey.csat_due"
    HEALTH_SCORE_LOW = "health.score_low"
    ONBOARDING_MILESTONE = "onboarding.milestone"
    REFERRAL_ELIGIBLE = "referral.eligible"
    CANCEL_FLOW_STARTED = "cancel.flow_started"
    ANNUAL_UPSELL_ELIGIBLE = "upsell.annual_eligible"

    # Universal service-lifecycle events (any recurring service: oil change,
    # beauty treatment, fitness membership, maintenance, prescriptions)
    SERVICE_DUE_SOON = "service.due_soon"
    SERVICE_OVERDUE = "service.overdue"
    SERVICE_COMPLETED = "service.completed"
    CROSS_SELL_ELIGIBLE = "cross_sell.eligible"
    SEQUENCE_ENROLLED = "sequence.enrolled"
    CES_LOW = "ces.low"
    TOUCHPOINT_LOGGED = "touchpoint.logged"
    SURVEY_RESPONDED = "survey.responded"

    # Pain-point events (what the end user experiences)
    AUTH_LOGIN_FAILED = "auth.login_failed"
    APP_ERROR_OCCURRED = "app.error_occurred"
    SUPPORT_TICKET_OPENED = "support.ticket_opened"
    SUPPORT_TICKET_RESOLVED = "support.ticket_resolved"
    BILLING_PRICE_CHANGED = "billing.price_changed"
    BILLING_INVOICE_CREATED = "billing.invoice_created"
    USAGE_QUOTA_NEAR_LIMIT = "usage.quota_near_limit"
    ONBOARDING_NO_LOGIN = "onboarding.no_login"
    ONBOARDING_STUCK = "onboarding.stuck"
    INVENTORY_BACK_IN_STOCK = "inventory.back_in_stock"
    PRICING_PRICE_DROPPED = "pricing.price_dropped"
    SECURITY_SUSPICIOUS_LOGIN = "security.suspicious_login"
    TEAM_INVITE_SENT = "team.invite_sent"


class Channel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class BaseEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Client(BaseEntity):
    name: str
    email: str
    status: str = "active"
    vertical: str | None = None
    churn_score: float = 0.0


class Campaign(BaseEntity):
    name: str
    channel: Channel
    status: str = "draft"
    audience_size: int = 0


class Flow(BaseEntity):
    name: str
    definition: dict[str, Any]
    status: str = "draft"
    trigger_event: EventType | None = None


class Subscription(BaseEntity):
    plan: str
    status: str = "active"
    mrr: float = 0.0
    expires_at: datetime | None = None


class Order(BaseEntity):
    customer_email: str
    total: float
    status: str = "pending"


class Metric(BaseEntity):
    name: str
    value: float
    dimension: str | None = None
    period_start: datetime
    period_end: datetime


class Report(BaseEntity):
    name: str
    format: str = "pdf"
    status: str = "queued"
    download_url: str | None = None


class Event(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    type: EventType
    tenant_id: UUID
    payload: T
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = False


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool


__all__ = [
    "EntityType",
    "EventType",
    "Channel",
    "BaseEntity",
    "Client",
    "Campaign",
    "Flow",
    "Subscription",
    "Order",
    "Metric",
    "Report",
    "Event",
    "Page",
]
