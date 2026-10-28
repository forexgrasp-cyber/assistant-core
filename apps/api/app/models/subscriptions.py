"""
Subscription models: Plans, Subscriptions, Invoices, Dunning, Coupons.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index, Enum as SQLEnum, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from .base import SoftDeleteModel


class SubscriptionPlan(SoftDeleteModel):
    """Subscription plan."""
    __tablename__ = "subscription_plans"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Pricing
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    interval: Mapped[str] = mapped_column(String(20), nullable=False)  # day, week, month, year
    interval_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Trial
    trial_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trial_requires_payment_method: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Features
    features: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    limits: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Setup
    setup_fee: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)  # active, archived
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Display
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    badge: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    badge_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="plan")
    
    __table_args__ = (
        Index("ix_subscription_plans_client_slug", "client_id", "slug", unique=True),
    )


class Subscription(SoftDeleteModel):
    """Customer subscription."""
    __tablename__ = "subscriptions"
    
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    payment_method_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("payment_methods.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # External reference
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    external_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)  # pending, active, past_due, paused, cancelled, expired, trialing
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cancellation_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Pricing (snapshot)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    interval: Mapped[str] = mapped_column(String(20), nullable=False)
    interval_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Quantities
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Trial
    trial_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Lifecycle
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Proration
    prorate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Dunning
    dunning_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_dunning_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_dunning_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Pause
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    pause_resumes_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    pause_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    custom_fields: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Attribution
    attribution: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="subscriptions")
    plan: Mapped["SubscriptionPlan"] = relationship("SubscriptionPlan", back_populates="subscriptions")
    payment_method: Mapped[Optional["PaymentMethod"]] = relationship("PaymentMethod")
    items: Mapped[List["SubscriptionItem"]] = relationship("SubscriptionItem", back_populates="subscription", cascade="all, delete-orphan")
    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")
    dunning_events: Mapped[List["DunningEvent"]] = relationship("DunningEvent", back_populates="subscription", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_subscriptions_client_status", "client_id", "status"),
        Index("ix_subscriptions_period_end", "current_period_end"),
        Index("ix_subscriptions_dunning", "next_dunning_attempt_at"),
    )


class SubscriptionItem(SoftDeleteModel):
    """Subscription line item (for metered/usage-based billing)."""
    __tablename__ = "subscription_items"
    
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
    # Pricing
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    interval: Mapped[str] = mapped_column(String(20), nullable=False)
    interval_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Metered billing
    is_metered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    meter_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    meter_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # usage, tiered, volume
    meter_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Usage
    current_usage: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    last_reported_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="items")
    
    __table_args__ = (
        Index("ix_subscription_items_subscription", "subscription_id"),
    )


class Invoice(SoftDeleteModel):
    """Invoice for subscription or one-time charge."""
    __tablename__ = "invoices"
    
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payment_method_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("payment_methods.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Invoice identifiers
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Type
    type: Mapped[str] = mapped_column(String(20), default="subscription", nullable=False)  # subscription, one_time, usage, adjustment
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)  # draft, open, paid, voided, uncollectible, partially_paid
    
    # Amounts
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    tax_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    discount_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    amount_due: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    amount_remaining: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    amount_credited: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Line items
    line_items: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Tax
    tax_rates: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Discounts
    discounts: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Period
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Dates
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Payment
    payment_method_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    payment_intent_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    charge_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Hosted
    hosted_invoice_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    invoice_pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Collection
    collection_method: Mapped[str] = mapped_column(String(20), default="charge_automatically", nullable=False)  # charge_automatically, send_invoice
    next_payment_attempt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    custom_fields: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    customer: Mapped["Customer"] = relationship("Customer")
    subscription: Mapped[Optional["Subscription"]] = relationship("Subscription", back_populates="invoices")
    payment_method: Mapped[Optional["PaymentMethod"]] = relationship("PaymentMethod")
    items: Mapped[List["InvoiceItem"]] = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments: Mapped[List["PaymentEvent"]] = relationship("PaymentEvent", back_populates="invoice", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_invoices_client_status", "client_id", "status"),
        Index("ix_invoices_due", "due_at"),
        Index("ix_invoices_subscription", "subscription_id"),
    )


class InvoiceItem(SoftDeleteModel):
    """Invoice line item."""
    __tablename__ = "invoice_items"
    
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscription_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Type
    type: Mapped[str] = mapped_column(String(50), default="subscription", nullable=False)  # subscription, usage, one_time, addon, discount, tax
    
    # Description
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Pricing
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Period
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Usage (for metered)
    usage: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    meter_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Proration
    proration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Tax
    tax_rates: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Discounts
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="items")
    
    __table_args__ = (
        Index("ix_invoice_items_invoice", "invoice_id"),
    )


class PaymentMethod(SoftDeleteModel):
    """Customer payment method."""
    __tablename__ = "payment_methods"
    
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Type
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # card, bank_account, paypal, apple_pay, google_pay, ach
    
    # Provider
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # stripe, adyen, braintree, paypal
    provider_payment_method_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Card details
    card_brand: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    card_last4: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    card_exp_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    card_exp_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    card_funding: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # credit, debit, prepaid
    card_country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    
    # Bank account
    bank_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bank_last4: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    bank_country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    
    # Billing details
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Status
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    customer: Mapped["Customer"] = relationship("Customer")
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="payment_method")
    
    __table_args__ = (
        Index("ix_payment_methods_customer_default", "customer_id", "is_default", unique=True, postgresql_where="is_default = true"),
    )


class PaymentEvent(SoftDeleteModel):
    """Payment transaction event."""
    __tablename__ = "payment_events"
    
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payment_method_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("payment_methods.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Type
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # charge, refund, payout, adjustment, dispute
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, succeeded, failed, cancelled, refunded
    
    # Amount
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    fee: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    net: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Provider
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    provider_transaction_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider_fee: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    
    # Status details
    failure_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    failure_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    
    # Dispute
    is_dispute: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dispute_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    dispute_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    dispute_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Refund
    is_refund: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    refund_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    refund_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Description
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    statement_descriptor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    customer: Mapped["Customer"] = relationship("Customer")
    invoice: Mapped[Optional["Invoice"]] = relationship("Invoice", back_populates="payments")
    
    __table_args__ = (
        Index("ix_payment_events_customer_created", "customer_id", "created_at"),
        Index("ix_payment_events_provider_transaction", "provider_transaction_id", unique=True),
    )


class DunningConfig(SoftDeleteModel):
    """Dunning configuration for failed payments."""
    __tablename__ = "dunning_configs"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Schedule
    attempts: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    # Example: [{"days_after_due": 1, "action": "email", "template": "dunning_1"}, {"days_after_due": 3, "action": "email", "template": "dunning_2"}, {"days_after_due": 7, "action": "pause", "template": "dunning_3"}, {"days_after_due": 14, "action": "cancel"}]
    
    # Settings
    pause_on_final_attempt: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cancel_on_final_attempt: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    send_final_email: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Retry
    retry_interval_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    max_retries_per_attempt: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    
    # Grace period
    grace_period_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Notifications
    notify_customer: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_team: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    team_notification_emails: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="dunning_config")
    
    __table_args__ = (
        Index("ix_dunning_configs_client_default", "client_id", "is_default", unique=True, postgresql_where="is_default = true"),
    )


class DunningEvent(SoftDeleteModel):
    """Dunning event for a subscription."""
    __tablename__ = "dunning_events"
    
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    config_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("dunning_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Attempt
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # email, sms, push, pause, cancel, retry
    template: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="scheduled", nullable=False)  # scheduled, sent, skipped, failed, completed
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Result
    result: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # payment_received, paused, cancelled, no_action
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Email/SMS tracking
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Timestamps
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="dunning_events")
    
    __table_args__ = (
        Index("ix_dunning_events_subscription_attempt", "subscription_id", "attempt_number", unique=True),
        Index("ix_dunning_events_scheduled_status", "scheduled_at", "status"),
    )


class Coupon(SoftDeleteModel):
    """Coupon/promo code."""
    __tablename__ = "coupons"
    
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Type
    type: Mapped[str] = mapped_column(String(20), default="percentage", nullable=False)  # percentage, fixed_amount, free_shipping
    value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    
    # Limits
    max_redemptions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_redemptions_per_customer: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    min_order_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    
    # Applicability
    applies_to: Mapped[str] = mapped_column(String(20), default="all", nullable=False)  # all, subscription, products, collections
    applies_to_ids: Mapped[List[uuid.UUID]] = mapped_column(JSONB, default=list, nullable=False)
    excludes_ids: Mapped[List[uuid.UUID]] = mapped_column(JSONB, default=list, nullable=False)
    customer_segments: Mapped[List[uuid.UUID]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Recurring
    applies_to_recurring: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_recurring_intervals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Validity
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Usage
    redemptions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    redemptions: Mapped[List["CouponRedemption"]] = relationship("CouponRedemption", back_populates="coupon", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_coupons_client_code", "client_id", "code", unique=True),
    )


class CouponRedemption(SoftDeleteModel):
    """Coupon redemption record."""
    __tablename__ = "coupon_redemptions"
    
    coupon_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("coupons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
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
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Discount
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Recurring
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurring_intervals_remaining: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Timestamps
    redeemed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    coupon: Mapped["Coupon"] = relationship("Coupon", back_populates="redemptions")
    customer: Mapped["Customer"] = relationship("Customer")
    
    __table_args__ = (
        Index("ix_coupon_redemptions_coupon_customer", "coupon_id", "customer_id"),
    )
