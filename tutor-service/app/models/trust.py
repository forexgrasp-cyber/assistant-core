"""Trust & Social Proof Models - Testimonials, Activity Feed, Referrals, Trust Signals."""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TestimonialStatus(str, enum.Enum):
    """Testimonial moderation status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FEATURED = "featured"


class ActivityType(str, enum.Enum):
    """Types of user activities for the feed."""
    LESSON_COMPLETED = "lesson_completed"
    STREAK_MILESTONE = "streak_milestone"
    LEVEL_UP = "level_up"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    LEAGUE_PROMOTION = "league_promotion"
    LANGUAGE_STARTED = "language_started"
    HUMAN_TUTOR_SESSION = "human_tutor_session"
    PERFECT_LESSON = "perfect_lesson"


class ReferralStatus(str, enum.Enum):
    """Referral tracking status."""
    PENDING = "pending"
    SIGNED_UP = "signed_up"
    ACTIVATED = "activated"  # Completed first lesson
    REWARDED = "rewarded"


class Testimonial(Base):
    """User testimonials for social proof."""

    __tablename__ = "testimonials"
    __table_args__ = (
        Index("ix_testimonials_status", "status"),
        Index("ix_testimonials_featured", "is_featured"),
        Index("ix_testimonials_language", "language"),
        Index("ix_testimonials_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5 stars

    # User info (denormalized for display even if user deleted)
    author_name: Mapped[str] = mapped_column(String(100), nullable=False)
    author_avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    author_location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    author_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Context
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # Language learned
    cefr_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # Level achieved

    # Moderation
    status: Mapped[TestimonialStatus] = mapped_column(Enum(TestimonialStatus), default=TestimonialStatus.PENDING, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    moderated_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id], back_populates="testimonials")
    moderator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[moderated_by])


class ActivityFeed(Base):
    """Real-time activity feed for social proof."""

    __tablename__ = "activity_feed"
    __table_args__ = (
        Index("ix_activity_feed_user_id", "user_id"),
        Index("ix_activity_feed_type", "activity_type"),
        Index("ix_activity_feed_created_at", "created_at"),
        Index("ix_activity_feed_public", "is_public"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    activity_type: Mapped[ActivityType] = mapped_column(Enum(ActivityType), nullable=False)

    # Activity details (JSON for flexibility)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # lesson_id, xp_gained, etc.

    # Display
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # Show in public feed
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="activities")


class Referral(Base):
    """Referral program tracking."""

    __tablename__ = "referrals"
    __table_args__ = (
        UniqueConstraint("referrer_id", "referred_email", name="uq_referral_referrer_email"),
        Index("ix_referrals_referrer_id", "referrer_id"),
        Index("ix_referrals_referred_id", "referred_id"),
        Index("ix_referrals_code", "code"),
        Index("ix_referrals_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    referred_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    referred_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    status: Mapped[ReferralStatus] = mapped_column(Enum(ReferralStatus), default=ReferralStatus.PENDING, nullable=False)

    # Rewards
    referrer_reward_gems: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referred_reward_gems: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referrer_reward_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referred_reward_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    rewarded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    referrer: Mapped["User"] = relationship("User", foreign_keys=[referrer_id], back_populates="referrals_sent")
    referred: Mapped[Optional["User"]] = relationship("User", foreign_keys=[referred_id], back_populates="referral_received")


class TrustSignal(Base):
    """Global trust signals / stats for landing page."""

    __tablename__ = "trust_signals"
    __table_args__ = (
        UniqueConstraint("key", name="uq_trust_signals_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)  # e.g., "total_users", "lessons_completed"
    label: Mapped[str] = mapped_column(String(200), nullable=False)  # Display label
    value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Current value
    display_format: Mapped[str] = mapped_column(String(50), default="number", nullable=False)  # number, k_format, m_format, percentage
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Lucide icon name
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class PressMention(Base):
    """Press mentions / media coverage."""

    __tablename__ = "press_mentions"
    __table_args__ = (
        Index("ix_press_mentions_featured", "is_featured"),
        Index("ix_press_mentions_published_at", "published_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    publication: Mapped[str] = mapped_column(String(200), nullable=False)
    publication_logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    published_at: Mapped[date] = mapped_column(Date, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)