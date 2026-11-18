"""
Tutor Memory models for persistent conversation context
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON, Float, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class TutorMemory(Base):
    """Persistent tutor memory for each user-language pair"""
    __tablename__ = "tutor_memories"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    # Learner Profile (from shared/agent_runtime/tutor_memory.py)
    learner_profile: Mapped[Dict[str, Any]] = mapped_column(JSON, default={
        "native_language": "en",
        "target_language": "es",
        "cefr_level": "A1",
        "learning_goals": [],
        "interests": [],
        "preferred_topics": [],
        "weak_areas": [],
        "strong_areas": [],
        "learning_style": "balanced",  # visual, auditory, kinesthetic, balanced
        "daily_goal_minutes": 15,
        "preferred_session_length": 30,
        "timezone": "UTC",
    }, nullable=False)
    
    # Study Plan
    study_plan: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Conversation History Summary
    total_sessions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_messages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_session_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Key memories (important facts about the learner)
    key_memories: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    
    # Vocabulary learned (tracked separately from spaced repetition)
    vocabulary_mastered: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    vocabulary_struggling: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    
    # Grammar patterns mastered
    grammar_mastered: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    grammar_struggling: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    
    # Pronunciation patterns
    pronunciation_issues: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    pronunciation_improved: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    
    # Writing patterns
    writing_errors: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    writing_improvements: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    
    # Cultural knowledge
    cultural_topics_covered: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    
    # Preferences
    preferences: Mapped[Dict[str, Any]] = mapped_column(JSON, default={
        "correction_style": "gentle",  # gentle, direct, minimal
        "explanation_depth": "moderate",  # minimal, moderate, detailed
        "use_native_language": True,
        "speak_speed": "normal",  # slow, normal, fast
        "include_cultural_notes": True,
    }, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint("user_id", "language", name="uq_tutor_memory_user_lang"),
        Index("ix_tutor_memory_user_lang", "user_id", "language"),
    )


class TutorSessionContext(Base):
    """Per-session context that can be loaded for continuity"""
    __tablename__ = "tutor_session_contexts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Session type
    session_type: Mapped[str] = mapped_column(String(50), nullable=False)  # lesson, practice, chat, assessment
    lesson_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Context snapshot
    context_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    
    # Summary
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_takeaways: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    new_vocabulary: Mapped[List[Dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)
    corrections_made: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("ix_tutor_session_user_started", "user_id", "started_at"),
        Index("ix_tutor_session_session_id", "session_id"),
    )


class UserVoiceSettings(Base):
    """Voice settings per user per language"""
    __tablename__ = "user_voice_settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    # Voice selection
    voice_id: Mapped[str] = mapped_column(String(100), nullable=False)  # Provider-specific voice ID
    provider: Mapped[str] = mapped_column(String(50), default="edge_tts", nullable=False)  # edge_tts, elevenlabs, azure, google
    
    # Voice characteristics
    gender: Mapped[str] = mapped_column(String(20), default="neutral", nullable=False)  # male, female, neutral
    age_group: Mapped[str] = mapped_column(String(20), default="adult", nullable=False)  # child, teen, adult, senior
    accent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # regional accent
    
    # Speech settings
    rate: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)  # 0.5 - 2.0
    pitch: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)  # 0.5 - 2.0
    volume: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)  # 0.0 - 1.0
    
    # Per-language overrides
    language_specific: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint("user_id", "language", name="uq_voice_settings_user_lang"),
        Index("ix_voice_settings_user_lang", "user_id", "language"),
    )


class AvailableVoice(Base):
    """Catalog of available voices per language"""
    __tablename__ = "available_voices"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Voice ID in provider
    voice_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Characteristics
    gender: Mapped[str] = mapped_column(String(20), nullable=False)  # male, female, neutral
    age_group: Mapped[str] = mapped_column(String(20), nullable=False)  # child, teen, adult, senior
    accent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Sample
    sample_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Capabilities
    supports_ssml: Mapped[bool] = mapped_column(default=False, nullable=False)
    supports_emotion: Mapped[bool] = mapped_column(default=False, nullable=False)
    max_length: Mapped[int] = mapped_column(default=5000, nullable=False)  # characters
    
    # Status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_premium: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint("provider", "voice_id", name="uq_available_voice_provider_id"),
        Index("ix_available_voices_lang_provider", "language", "provider"),
        Index("ix_available_voices_lang_gender_age", "language", "gender", "age_group"),
    )