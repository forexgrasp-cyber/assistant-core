"""
Lesson models for Tutor Service
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String, Integer, DateTime, ForeignKey, Enum, Text, Boolean, JSON, Float, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ContentType(str, PyEnum):
    """Lesson content types"""
    DIALOGUE = "dialogue"
    EXERCISE = "exercise"
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    QUIZ = "quiz"
    PRONUNCIATION = "pronunciation"
    WRITING = "writing"
    FLASHCARD = "flashcard"
    READING = "reading"


class FocusArea(str, PyEnum):
    """Learning focus areas"""
    CONVERSATION = "conversation"
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    PRONUNCIATION = "pronunciation"
    WRITING = "writing"
    READING = "reading"
    LISTENING = "listening"
    CULTURE = "culture"


class CEFRLevel(str, PyEnum):
    """CEFR Language Proficiency Levels"""
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class ExerciseType(str, PyEnum):
    """Exercise types"""
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_BLANK = "fill_blank"
    MATCH = "match"
    ORDER = "order"
    SPEAK = "speak"
    WRITE = "write"
    TRANSLATE = "translate"
    TRUE_FALSE = "true_false"
    INPUT = "input"


class Lesson(Base):
    """Lesson model"""
    __tablename__ = "lessons"
    
    id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    level: Mapped[CEFRLevel] = mapped_column(Enum(CEFRLevel), nullable=False, index=True)
    focus_area: Mapped[FocusArea] = mapped_column(Enum(FocusArea), nullable=False, index=True)
    
    # Target audience
    target_age_group: Mapped[str] = mapped_column(String(20), default="adult", nullable=False)  # child, teen, young_adult, adult, senior
    gamification_level: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # none, light, medium, full
    
    # Duration & XP
    duration: Mapped[int] = mapped_column(Integer, nullable=False)  # minutes
    xp_reward: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Prerequisites & ordering
    prerequisites: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Tags & metadata
    tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Alias for metadata_json for schema compatibility"""
        return self.metadata_json
    
    @metadata.setter
    def metadata(self, value: Dict[str, Any]) -> None:
        self.metadata_json = value
    
    @property
    def content(self) -> List["LessonContent"]:
        """Alias for content_items for schema compatibility"""
        return self.content_items
    
    # Legacy content JSON (kept for backward compatibility)
    content_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    progress_records: Mapped[List["LessonProgress"]] = relationship("LessonProgress", back_populates="lesson")
    content_items: Mapped[List["LessonContent"]] = relationship("LessonContent", back_populates="lesson", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_lessons_language_level", "language", "level"),
    )


class LessonContent(Base):
    """Individual content item within a lesson"""
    __tablename__ = "lesson_content"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lesson_id: Mapped[str] = mapped_column(String(100), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    content_id: Mapped[str] = mapped_column(String(100), nullable=False)  # Unique within lesson
    
    # Content details
    type: Mapped[ContentType] = mapped_column(Enum(ContentType), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_time: Mapped[int] = mapped_column(Integer, nullable=False)  # minutes
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Content data (flexible JSON)
    data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    
    # XP reward for this content
    xp_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Focus area (can differ from lesson)
    focus_area: Mapped[Optional[FocusArea]] = mapped_column(Enum(FocusArea), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="content_items")
    
    __table_args__ = (
        UniqueConstraint("lesson_id", "content_id", name="uq_lesson_content"),
        Index("ix_lesson_content_lesson_order", "lesson_id", "order"),
    )


class VocabularyItem(Base):
    """Vocabulary items for spaced repetition"""
    __tablename__ = "vocabulary_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    # Word data
    word: Mapped[str] = mapped_column(String(100), nullable=False)
    translation: Mapped[str] = mapped_column(String(200), nullable=False)
    transliteration: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    part_of_speech: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # easy, medium, hard
    
    # Context
    example_sentence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    example_translation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Spaced repetition (SM-2 algorithm)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    interval: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # days
    repetitions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_review: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    last_reviewed: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Source
    source_lesson_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_content_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    
    # Status
    is_learned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("ix_vocabulary_user_language_next", "user_id", "language", "next_review"),
        Index("ix_vocabulary_word_language", "word", "language"),
    )


class PronunciationExercise(Base):
    """Pronunciation exercise definitions"""
    __tablename__ = "pronunciation_exercises"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    level: Mapped[CEFRLevel] = mapped_column(Enum(CEFRLevel), nullable=False)
    
    # Target
    target_text: Mapped[str] = mapped_column(Text, nullable=False)
    translation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Phonemes
    phonemes: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    
    # Audio
    audio_url: Mapped[str] = mapped_column(String(500), nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)  # seconds
    
    # Difficulty
    difficulty: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # easy, medium, hard
    
    # Tips
    tips: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    
    # Metadata
    tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("ix_pronunciation_language_level", "language", "level"),
    )


class WritingPrompt(Base):
    """Writing exercise prompts"""
    __tablename__ = "writing_prompts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    level: Mapped[CEFRLevel] = mapped_column(Enum(CEFRLevel), nullable=False)
    focus_area: Mapped[FocusArea] = mapped_column(Enum(FocusArea), default=FocusArea.WRITING, nullable=False)
    
    # Prompt
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    min_words: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_words: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Criteria
    criteria: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    
    # Examples
    examples: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    
    # Vocabulary hints
    vocabulary_hints: Mapped[List[Dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)
    
    # Metadata
    tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("ix_writing_language_level", "language", "level"),
    )