"""
SQLAlchemy models for VA Matching Platform.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from marketplace.database import Base


class UserRole(str, PyEnum):
    ADMIN = "admin"
    CLIENT = "client"
    VA = "va"


class UserStatus(str, PyEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class VAStatus(str, PyEnum):
    PENDING = "pending"
    VETTING = "vetting"
    ACTIVE = "active"
    MATCHED = "matched"
    INACTIVE = "inactive"
    REJECTED = "rejected"


class MatchStatus(str, PyEnum):
    PROPOSED = "proposed"
    INTRO_SENT = "intro_sent"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    COMPLETED = "completed"
    DISPUTED = "disputed"


class ClientStatus(str, PyEnum):
    LEAD = "lead"
    QUALIFIED = "qualified"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    PAUSED = "paused"
    CHURNED = "churned"


class PaymentStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    DISPUTED = "disputed"
    CANCELED = "canceled"


class PaymentType(str, PyEnum):
    PLACEMENT_FEE = "placement_fee"
    PLATFORM_FEE = "platform_fee"
    MONTHLY_SUBSCRIPTION = "monthly_subscription"
    REFUND = "refund"


class VAProfile(Base):
    """VA profile with skills, vetting results, and source info."""

    __tablename__ = "va_profiles"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=True
    )

    # Profile info
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    availability_hours_per_week: Mapped[int] = mapped_column(Integer, default=0)
    languages: Mapped[list[str]] = mapped_column(JSON, default=list)
    location: Mapped[str] = mapped_column(String(255), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    portfolio_url: Mapped[str] = mapped_column(String(500), default="")
    linkedin_url: Mapped[str] = mapped_column(String(500), default="")

    # Source
    source: Mapped[str] = mapped_column(String(50), default="direct")
    source_profile_url: Mapped[str] = mapped_column(String(500), default="")
    source_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0)
    source_reviews_count: Mapped[int] = mapped_column(Integer, default=0)

    # Payouts (Stripe Connect Express account, canonical onboarding)
    payout_account_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Vetting results
    status: Mapped[VAStatus] = mapped_column(
        Enum(VAStatus), default=VAStatus.PENDING, nullable=False
    )
    vetting_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=0)
    english_test_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=0)
    trial_task_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=0)
    reference_check_passed: Mapped[bool] = mapped_column(default=False)

    # Skills
    skills: Mapped[list[dict]] = mapped_column(JSON, default=list)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="va_profile")
    matches: Mapped[list["Match"]] = relationship(
        back_populates="va", foreign_keys="Match.va_id"
    )


class ClientProfile(Base):
    """Client profile with requirements and preferences."""

    __tablename__ = "client_profiles"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )

    # Company info
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    industry: Mapped[str] = mapped_column(String(100), default="")
    company_size: Mapped[int] = mapped_column(Integer, default=1)

    # Requirements
    monthly_budget: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    needed_hours_per_week: Mapped[int] = mapped_column(Integer, default=0)
    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    tasks_to_delegate: Mapped[list[str]] = mapped_column(JSON, default=list)
    current_tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_timezone_overlap_hours: Mapped[int] = mapped_column(Integer, default=4)
    max_hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

    # Status
    status: Mapped[ClientStatus] = mapped_column(
        Enum(ClientStatus), default=ClientStatus.LEAD, nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), default="direct")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="client_profile")
    matches: Mapped[list["Match"]] = relationship(
        back_populates="client", foreign_keys="Match.client_id"
    )


class User(Base):
    """User account with authentication."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.CLIENT, nullable=False
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus), default=UserStatus.PENDING, nullable=False
    )
    email_verified: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Profile relationships
    va_profile: Mapped[Optional[VAProfile]] = relationship(
        back_populates="user", uselist=False
    )
    client_profile: Mapped[Optional[ClientProfile]] = relationship(
        back_populates="user", uselist=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    payment_intents: Mapped[list["PaymentIntent"]] = relationship(
        back_populates="client", foreign_keys="PaymentIntent.client_id"
    )


class RefreshToken(Base):
    """JWT refresh tokens for authentication."""

    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationship
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class Match(Base):
    """Match between client and VA."""

    __tablename__ = "matches"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    client_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("client_profiles.id"), nullable=False
    )
    va_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("va_profiles.id"), nullable=False
    )

    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus), default=MatchStatus.PROPOSED, nullable=False
    )
    match_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=0)
    match_factors: Mapped[dict] = mapped_column(JSON, default=dict)

    # Lifecycle timestamps
    proposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    intro_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    interview_scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str] = mapped_column(Text, default="")
    onboarding_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    onboarding_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    placement_fee_charged: Mapped[bool] = mapped_column(default=False)
    platform_fee_charged: Mapped[bool] = mapped_column(default=False)

    # Metadata
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # Relationships
    client: Mapped[ClientProfile] = relationship(
        back_populates="matches", foreign_keys=[client_id]
    )
    va: Mapped[VAProfile] = relationship(
        back_populates="matches", foreign_keys=[va_id]
    )
    payments: Mapped[list["PaymentIntent"]] = relationship(back_populates="match")
    onboarding_plan: Mapped[Optional["OnboardingPlan"]] = relationship(
        back_populates="match", uselist=False
    )
    deliveries: Mapped[list["Delivery"]] = relationship(back_populates="match")


class OnboardingPlan(Base):
    """Onboarding plan for a match."""

    __tablename__ = "onboarding_plans"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    match_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id"), unique=True, nullable=False
    )
    client_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("client_profiles.id"), nullable=False
    )
    va_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("va_profiles.id"), nullable=False
    )

    stage: Mapped[str] = mapped_column(String(50), default="vetting_complete")
    tasks: Mapped[list[dict]] = mapped_column(JSON, default=list)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_task_index: Mapped[int] = mapped_column(Integer, default=0)

    # Relationship
    match: Mapped["Match"] = relationship(back_populates="onboarding_plan")


class Delivery(Base):
    """Work delivery tracking."""

    __tablename__ = "deliveries"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    match_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False
    )
    task_id: Mapped[str] = mapped_column(String(255), nullable=False)
    va_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("va_profiles.id"), nullable=False
    )
    client_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("client_profiles.id"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    hours_logged: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    deliverables: Mapped[list[str]] = mapped_column(JSON, default=list)
    feedback: Mapped[str] = mapped_column(Text, default="")
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationship
    match: Mapped["Match"] = relationship(back_populates="deliveries")


class PaymentIntent(Base):
    """Payment intents for placement fees and subscriptions."""

    __tablename__ = "payment_intents"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="usd")
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False
    )
    payment_type: Mapped[PaymentType] = mapped_column(
        Enum(PaymentType), nullable=False
    )
    client_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    match_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id"), nullable=True
    )
    va_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("va_profiles.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, default="")
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    succeeded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    client: Mapped[User] = relationship(
        back_populates="payment_intents", foreign_keys=[client_id]
    )
    match: Mapped[Optional[Match]] = relationship(back_populates="payments")
    subscription: Mapped[Optional["Subscription"]] = relationship(
        back_populates="payment_intent", uselist=False
    )


class Subscription(Base):
    """Monthly platform fee subscriptions."""

    __tablename__ = "subscriptions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    payment_intent_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_intents.id"), nullable=True
    )
    client_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    match_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id"), nullable=True
    )
    va_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("va_profiles.id"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="usd")
    interval: Mapped[str] = mapped_column(String(20), default="month")
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False
    )
    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    payment_intent: Mapped[Optional[PaymentIntent]] = relationship(
        back_populates="subscription", uselist=False, foreign_keys=[payment_intent_id]
    )


class JournalEntry(Base):
    """Double-entry ledger entries."""

    __tablename__ = "journal_entries"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference: Mapped[str] = mapped_column(String(255), nullable=False)
    lines: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Account(Base):
    """Chart of accounts for double-entry bookkeeping."""

    __tablename__ = "accounts"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Notification(Base):
    """In-app notifications."""

    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    read: Mapped[bool] = mapped_column(default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationship
    user: Mapped["User"] = relationship()


class VettingResult(Base):
    """VA vetting results storage."""

    __tablename__ = "vetting_results"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    va_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("va_profiles.id"), nullable=False
    )
    test_type: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    passed: Mapped[bool] = mapped_column(default=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationship
    va: Mapped[VAProfile] = relationship()


# Indexes
Index("ix_users_email", User.email, unique=True)
Index("ix_va_profiles_status", VAProfile.status)
Index("ix_client_profiles_status", ClientProfile.status)
Index("ix_matches_status", Match.status)
Index("ix_matches_client_id", Match.client_id)
Index("ix_matches_va_id", Match.va_id)
Index("ix_payment_intents_status", PaymentIntent.status)
Index("ix_subscriptions_client_id", Subscription.client_id)
Index("ix_journal_entries_date", JournalEntry.date)
Index("ix_notifications_user_id", Notification.user_id)
Index("ix_vetting_results_va_id", VettingResult.va_id)