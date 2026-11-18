"""Gamification Models - Streaks, XP, Leagues, Achievements, Quests."""

from __future__ import annotations

import enum
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LeagueTier(str, enum.Enum):
    """League tiers from lowest to highest."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"
    OBSIDIAN = "obsidian"  # Top 1%


class QuestType(str, enum.Enum):
    """Types of daily/weekly quests."""
    COMPLETE_LESSONS = "complete_lessons"
    PRACTICE_MINUTES = "practice_minutes"
    REVIEW_WORDS = "review_words"
    PERFECT_LESSON = "perfect_lesson"
    STREAK_MAINTAIN = "streak_maintain"
    SOCIAL_SHARE = "social_share"
    HUMAN_TUTOR_SESSION = "human_tutor_session"


class AchievementCategory(str, enum.Enum):
    """Achievement categories."""
    STREAK = "streak"
    PROGRESS = "progress"
    MASTERY = "mastery"
    SOCIAL = "social"
    EXPLORATION = "exploration"
    DEDICATION = "dedication"


class UserStreak(Base):
    """User's streak tracking with freeze/repair mechanics."""

    __tablename__ = "user_streaks"
    __table_args__ = (
        Index("ix_user_streaks_user_id", "user_id"),
        Index("ix_user_streaks_current_streak", "current_streak"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Streak freeze mechanics
    freezes_available: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1 free per week
    freezes_used_this_week: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    weekend_amulet_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weekend_amulet_expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Streak repair (paid with gems)
    repairs_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_repair_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="streak")


class UserXP(Base):
    """User's XP, level, and league tracking."""

    __tablename__ = "user_xp"
    __table_args__ = (
        Index("ix_user_xp_user_id", "user_id"),
        Index("ix_user_xp_league_tier", "league_tier"),
        Index("ix_user_xp_weekly_xp", "weekly_xp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    total_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    xp_to_next_level: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # League system (weekly reset)
    league_tier: Mapped[LeagueTier] = mapped_column(Enum(LeagueTier), default=LeagueTier.BRONZE, nullable=False)
    league_rank: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Rank within league
    weekly_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    previous_week_tier: Mapped[Optional[LeagueTier]] = mapped_column(Enum(LeagueTier), nullable=True)
    previous_week_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Gems currency
    gems: Mapped[int] = mapped_column(Integer, default=50, nullable=False)  # Starting gems
    gems_earned_total: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    gems_spent_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="xp")


class UserQuest(Base):
    """Daily and weekly quests for users."""

    __tablename__ = "user_quests"
    __table_args__ = (
        Index("ix_user_quests_user_id", "user_id"),
        Index("ix_user_quests_type_status", "quest_type", "status"),
        Index("ix_user_quests_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    quest_type: Mapped[QuestType] = mapped_column(Enum(QuestType), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    target_value: Mapped[int] = mapped_column(Integer, nullable=False)  # e.g., 3 lessons
    current_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    xp_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gems_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_daily: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, completed, claimed, expired

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="quests")
    """Daily and weekly quests for users."""

    __tablename__ = "user_quests"
    __table_args__ = (
        Index("ix_user_quests_user_id", "user_id"),
        Index("ix_user_quests_type_status", "quest_type", "status"),
        Index("ix_user_quests_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    quest_type: Mapped[QuestType] = mapped_column(Enum(QuestType), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    target_value: Mapped[int] = mapped_column(Integer, nullable=False)  # e.g., 3 lessons
    current_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    xp_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gems_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_daily: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, completed, claimed, expired

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class Achievement(Base):
    """Achievement definitions (static data, seeded)."""

    __tablename__ = "achievements"
    __table_args__ = (
        UniqueConstraint("key", name="uq_achievements_key"),
    )

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # Use key as ID (e.g., "first_lesson", "streak_7")
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[AchievementCategory] = mapped_column(Enum(AchievementCategory), nullable=False)

    icon: Mapped[str] = mapped_column(String(50), nullable=False)  # Lucide icon name or emoji
    xp_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gems_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Unlock criteria (JSON for flexibility)
    criteria: Mapped[dict] = mapped_column(JSON, nullable=False)  # e.g., {"streak_days": 7}
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Secret achievements

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)





class LeagueStanding(Base):
    """Weekly league standings snapshot."""

    __tablename__ = "league_standings"
    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uq_league_standings_user_week"),
        Index("ix_league_standings_week_tier_rank", "week_start", "league_tier", "rank"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    week_start: Mapped[date] = mapped_column(Date, nullable=False)  # Monday of the week
    league_tier: Mapped[LeagueTier] = mapped_column(Enum(LeagueTier), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    weekly_xp: Mapped[int] = mapped_column(Integer, nullable=False)

    promoted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    demoted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class UserFriend(Base):
    """Friend relationships for social features."""

    __tablename__ = "user_friends"
    __table_args__ = (
        UniqueConstraint("user_id", "friend_id", name="uq_user_friends"),
        Index("ix_user_friends_user_id", "user_id"),
        Index("ix_user_friends_friend_id", "friend_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    friend_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, accepted, blocked
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="friends")
    friend: Mapped["User"] = relationship("User", foreign_keys=[friend_id], back_populates="friend_of")


class GemTransaction(Base):
    """Audit log for gem transactions."""

    __tablename__ = "gem_transactions"
    __table_args__ = (
        Index("ix_gem_transactions_user_id", "user_id"),
        Index("ix_gem_transactions_type", "type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    type: Mapped[str] = mapped_column(String(50), nullable=False)  # earned, spent, refund, bonus
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Positive for earned, negative for spent
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)

    description: Mapped[str] = mapped_column(String(500), nullable=False)
    reference_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Quest ID, Achievement ID, etc.
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)