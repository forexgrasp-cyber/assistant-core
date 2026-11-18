"""
User models for Tutor Service
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List
from sqlalchemy import (
    String, Integer, DateTime, ForeignKey, Enum, Text, Boolean, JSON, Float, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class CEFRLevel(str, PyEnum):
    """CEFR Language Proficiency Levels"""
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class UserRole(str, PyEnum):
    """User roles"""
    LEARNER = "learner"
    TEACHER = "teacher"
    ADMIN = "admin"


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Language settings
    native_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), default="es", nullable=False)
    cefr_level: Mapped[CEFRLevel] = mapped_column(Enum(CEFRLevel), default=CEFRLevel.A1, nullable=False)
    
    # Gamification
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Settings
    daily_goal_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    auto_play_audio: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_translations: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_haptics: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    playback_speed: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    
    # Role & status
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.LEARNER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # LLM Configuration (BYOK keys, tier, preferences)
    llm_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    progress: Mapped[List["UserProgress"]] = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    lesson_progress: Mapped[List["LessonProgress"]] = relationship("LessonProgress", back_populates="user", cascade="all, delete-orphan")
    achievements: Mapped[List["UserAchievement"]] = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    practice_sessions: Mapped[List["PracticeSession"]] = relationship("PracticeSession", back_populates="user", cascade="all, delete-orphan")
    chat_sessions: Mapped[List["ChatSession"]] = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")

    # Gamification relationships
    streak: Mapped["UserStreak"] = relationship("UserStreak", back_populates="user", cascade="all, delete-orphan", uselist=False)
    xp: Mapped["UserXP"] = relationship("UserXP", back_populates="user", cascade="all, delete-orphan", uselist=False)
    quests: Mapped[List["UserQuest"]] = relationship("UserQuest", back_populates="user", cascade="all, delete-orphan")
    friends: Mapped[List["UserFriend"]] = relationship("UserFriend", foreign_keys="UserFriend.user_id", back_populates="user", cascade="all, delete-orphan")
    friend_of: Mapped[List["UserFriend"]] = relationship("UserFriend", foreign_keys="UserFriend.friend_id", back_populates="friend", cascade="all, delete-orphan")

    # Trust relationships
    testimonials: Mapped[List["Testimonial"]] = relationship("Testimonial", back_populates="user", foreign_keys="Testimonial.user_id", cascade="all, delete-orphan")
    activities: Mapped[List["ActivityFeed"]] = relationship("ActivityFeed", back_populates="user", cascade="all, delete-orphan")
    referrals_sent: Mapped[List["Referral"]] = relationship("Referral", foreign_keys="Referral.referrer_id", back_populates="referrer", cascade="all, delete-orphan")
    referral_received: Mapped[Optional["Referral"]] = relationship("Referral", foreign_keys="Referral.referred_id", back_populates="referred", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
        Index("ix_users_target_language", "target_language"),
    )


class UserProgress(Base):
    """User language learning progress"""
    __tablename__ = "user_progress"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Level progress
    current_level: Mapped[CEFRLevel] = mapped_column(Enum(CEFRLevel), default=CEFRLevel.A1, nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level_progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0-100
    
    # Streaks
    streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Time tracking
    total_time_spent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # seconds
    lessons_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lessons_mastered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Focus area progress (0-100 each)
    focus_area_progress: Mapped[dict] = mapped_column(JSON, default={
        "conversation": 0, "grammar": 0, "vocabulary": 0, "pronunciation": 0,
        "writing": 0, "reading": 0, "listening": 0, "culture": 0
    }, nullable=False)
    
    weak_areas: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    strong_areas: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    
    # Daily goal
    daily_goal_target: Mapped[int] = mapped_column(Integer, default=15, nullable=False)  # minutes
    daily_goal_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_goal_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_goal_last_completed: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Weekly stats
    weekly_stats: Mapped[dict] = mapped_column(JSON, default={
        "week_start": None, "minutes": 0, "lessons": 0, "xp": 0, "streak_days": 0
    }, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="progress")
    
    __table_args__ = (
        Index("ix_user_progress_user_language", "user_id", "language", unique=True),
    )


class LessonProgress(Base):
    """Individual lesson progress tracking"""
    __tablename__ = "lesson_progress"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id: Mapped[str] = mapped_column(String(100), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="not_started", nullable=False)  # not_started, in_progress, completed, mastered
    current_content_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_content: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    
    # Scoring
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mastery_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-100
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Time
    time_spent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # seconds
    last_accessed: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="lesson_progress")
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="progress_records")
    
    __table_args__ = (
        Index("ix_lesson_progress_user_lesson", "user_id", "lesson_id", unique=True),
    )


class UserAchievement(Base):
    """User achievements"""
    __tablename__ = "user_achievements"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    achievement_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Progress for locked achievements
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    target: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Unlock info
    unlocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="achievements")
    
    __table_args__ = (
        Index("ix_user_achievement_user_achievement", "user_id", "achievement_id", unique=True),
    )


class PracticeSession(Base):
    """Practice session tracking"""
    __tablename__ = "practice_sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)  # conversation, pronunciation, vocabulary, etc.
    content_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Session data
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # seconds
    
    # Results
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    xp_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    corrections_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Metadata
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="practice_sessions")
    
    __table_args__ = (
        Index("ix_practice_sessions_user_started", "user_id", "started_at"),
    )


class ChatSession(Base):
    """Chat session with AI tutor"""
    __tablename__ = "chat_sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    lesson_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Session data
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Messages stored as JSON
    messages: Mapped[List[dict]] = mapped_column(JSON, default=list, nullable=False)
    
    # Metadata
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chat_sessions")
    
    __table_args__ = (
        Index("ix_chat_sessions_user_started", "user_id", "started_at"),
    )