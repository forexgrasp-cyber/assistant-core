"""
Analytics models: Events, Metrics, Attribution, Cohorts, RFM, Predictive.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index, Enum as SQLEnum, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from .base import SoftDeleteModel


class Event(SoftDeleteModel):
    """Raw event for analytics pipeline."""
    __tablename__ = "events"
    
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Source
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    channel: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)  # email, sms, push, web, api, social
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
    
    # Properties
    properties: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Context
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referrer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    referrer_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Geo
    country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    
    # Device
    device_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # desktop, mobile, tablet
    os: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    browser: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Attribution
    attribution: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Processing
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship("Customer")
    
    __table_args__ = (
        Index("ix_events_type_timestamp", "event_type", "timestamp"),
        Index("ix_events_customer_timestamp", "customer_id", "timestamp"),
        Index("ix_events_session", "session_id"),
        Index("ix_events_campaign_timestamp", "campaign_id", "timestamp"),
    )


class EventProperty(SoftDeleteModel):
    """Event property definitions for schema validation."""
    __tablename__ = "event_properties"
    
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    property_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Schema
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # string, number, boolean, object, array
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_pii: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Validation
    enum_values: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    min_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    max_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    pattern: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # UI
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    group: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    __table_args__ = (
        Index("ix_event_properties_type_name", "event_type", "property_name", unique=True),
    )


class DailyMetric(SoftDeleteModel):
    """Daily aggregated metrics for a client."""
    __tablename__ = "daily_metrics"
    
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # Revenue
    total_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    attributed_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    email_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    sms_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    push_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    organic_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    subscription_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    one_time_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Orders
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_customer_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    returning_customer_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aov: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Customers
    new_customers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    returning_customers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_customers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_customers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Email
    emails_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_delivered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_opened: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_clicked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_bounced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_unsubscribed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    email_open_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    email_click_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    email_delivery_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    
    # SMS
    sms_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sms_delivered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sms_clicked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sms_opted_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sms_delivery_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    
    # Push
    push_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    push_delivered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    push_opened: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    push_clicked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    push_dismissed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Flows
    flow_entries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flow_completions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flow_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Subscriptions
    new_subscriptions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancelled_subscriptions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_subscriptions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mrr: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    arr: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    churned_mrr: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    expansion_mrr: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    contraction_mrr: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    new_mrr: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    reactivation_mrr: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Traffic
    sessions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    page_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bounce_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    avg_session_duration: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    
    # Conversion
    conversion_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    add_to_cart_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    checkout_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    
    # Retention
    day_1_retention: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    day_7_retention: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    day_30_retention: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    
    # Engagement
    email_engagement_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    sms_engagement_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    
    # Meta
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    computation_version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)
    
    __table_args__ = (
        Index("ix_daily_metrics_client_date", "client_id", "date", unique=True),
    )


class CohortMetric(SoftDeleteModel):
    """Cohort retention metrics."""
    __tablename__ = "cohort_metrics"
    
    cohort_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM
    period: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 0, 1, 2, 3, 6, 12 (months)
    cohort_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retained_customers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    repeat_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    revenue_per_customer: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    avg_ltv: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    cumulative_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Channel breakdown
    email_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    sms_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    push_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    organic_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Orders
    repeat_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_orders_per_customer: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    
    # Meta
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("ix_cohort_metrics_client_cohort_period", "client_id", "cohort_month", "period", unique=True),
    )


class RFMMetric(SoftDeleteModel):
    """RFM segment metrics for a customer."""
    __tablename__ = "rfm_metrics"
    
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    segment: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # champions, loyal, potential_loyalists, new, promising, need_attention, about_to_sleep, at_risk, cannot_lose, hibernating, lost
    recency: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    monetary: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    
    # Scores (1-5)
    r_score: Mapped[int] = mapped_column(Integer, nullable=False)
    f_score: Mapped[int] = mapped_column(Integer, nullable=False)
    m_score: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Percentiles
    recency_percentile: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    frequency_percentile: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    monetary_percentile: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    
    # Movement
    previous_segment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    segment_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    segment_stable_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Predicted
    predicted_next_segment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    churn_probability: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    expected_ltv: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    
    # Meta
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    customer: Mapped["Customer"] = relationship("Customer")
    
    __table_args__ = (
        Index("ix_rfm_metrics_client_segment", "client_id", "segment"),
        Index("ix_rfm_metrics_customer", "customer_id"),
    )


class AttributionTouchpoint(SoftDeleteModel):
    """Individual touchpoint in attribution journey."""
    __tablename__ = "attribution_touchpoints"
    
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Touchpoint details
    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # email, sms, push, organic, direct, referral, paid_social, paid_search, affiliate
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    medium: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    campaign: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    term: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Touchpoint identifiers
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
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Timing
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # Interaction
    interaction_type: Mapped[str] = mapped_column(String(20), nullable=False)  # click, open, view, impression
    interaction_value: Mapped[float] = mapped_column(Numeric(5, 2), default=1.0, nullable=False)
    
    # Attribution
    is_attributed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attribution_weight: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0, nullable=False)
    attribution_model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # position in journey
    
    # Revenue attribution
    attributed_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Meta
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    customer: Mapped["Customer"] = relationship("Customer")
    
    __table_args__ = (
        Index("ix_attribution_touchpoints_customer_timestamp", "customer_id", "timestamp"),
        Index("ix_attribution_touchpoints_order", "order_id"),
        Index("ix_attribution_touchpoints_channel_timestamp", "channel", "timestamp"),
    )


class AttributionResult(SoftDeleteModel):
    """Attribution result for an order or subscription."""
    __tablename__ = "attribution_results"
    
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Model
    model: Mapped[str] = mapped_column(String(50), nullable=False)  # last_click, first_click, linear, time_decay, u_shaped, custom_ml
    model_version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)
    
    # Total revenue
    total_revenue: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    attributed_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    organic_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Channel breakdown
    channel_attribution: Mapped[Dict[str, float]] = mapped_column(JSONB, default=dict, nullable=False)
    channel_touchpoints: Mapped[Dict[str, int]] = mapped_column(JSONB, default=dict, nullable=False)
    channel_revenue: Mapped[Dict[str, float]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Top touchpoints
    top_touchpoints: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Confidence
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(20), default="low", nullable=False)  # low, medium, high
    
    # Reconciliation
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reconciliation_diff: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    reconciled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reconciled_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Meta
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    customer: Mapped["Customer"] = relationship("Customer")
    order: Mapped[Optional["Order"]] = relationship("Order")
    subscription: Mapped[Optional["Subscription"]] = relationship("Subscription")
    
    __table_args__ = (
        Index("ix_attribution_results_order", "order_id", unique=True),
        Index("ix_attribution_results_subscription", "subscription_id", unique=True),
    )


class PredictiveMetric(SoftDeleteModel):
    """ML-based predictive metrics for a customer."""
    __tablename__ = "predictive_metrics"
    
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # LTV Prediction
    predicted_ltv: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    ltv_confidence_lower: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    ltv_confidence_upper: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    ltv_model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    ltv_features: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Churn Prediction
    churn_probability: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    churn_risk_level: Mapped[str] = mapped_column(String(20), nullable=False)  # low, medium, high, critical
    churn_model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    churn_features: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    churn_predicted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Next Order Prediction
    next_order_probability: Mapped[float] = mapped_column(Numeric(5, 4), nullable=True)
    next_order_predicted_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_order_predicted_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    next_order_model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Product Affinity
    top_product_affinities: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    recommended_products: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    affinity_model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Subscription
    subscription_probability: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    subscription_model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Meta
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    features_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    model_confidence: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0, nullable=False)
    
    # Relationships
    customer: Mapped["Customer"] = relationship("Customer")
    
    __table_args__ = (
        Index("ix_predictive_metrics_customer", "customer_id"),
        Index("ix_predictive_metrics_churn_risk", "churn_risk_level"),
    )


class AnomalyEvent(SoftDeleteModel):
    """Detected anomaly in metrics."""
    __tablename__ = "anomaly_events"
    
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    dimension: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)  # channel, campaign, segment, etc.
    dimension_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Anomaly details
    anomaly_type: Mapped[str] = mapped_column(String(50), nullable=False)  # spike, drop, trend_change, seasonality_break, outlier
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # low, medium, high, critical
    
    # Values
    expected_value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    actual_value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    deviation: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    deviation_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    
    # Detection
    detection_method: Mapped[str] = mapped_column(String(50), nullable=False)  # statistical, ml, threshold, seasonal
    model_version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0, nullable=False)
    
    # Context
    context: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    related_metrics: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Resolution
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)  # open, investigating, resolved, false_positive, acknowledged
    acknowledged_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    first_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    acknowledged_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[acknowledged_by_id])
    
    __table_args__ = (
        Index("ix_anomaly_events_status_detected", "status", "detected_at"),
        Index("ix_anomaly_events_metric_dimension", "metric_name", "dimension", "dimension_value"),
    )
