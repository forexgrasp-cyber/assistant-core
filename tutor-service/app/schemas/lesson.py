"""
Lesson schemas for Tutor Service API
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.lesson import ContentType, FocusArea, CEFRLevel, ExerciseType
from app.schemas.user import LessonProgressResponse


# Lesson Content schemas
class LessonContentBase(BaseModel):
    content_id: str
    type: ContentType
    title: str
    order: int
    estimated_time: int
    required: bool = True
    data: Dict[str, Any] = {}
    xp_reward: int = 0
    focus_area: Optional[FocusArea] = None


class LessonContentCreate(LessonContentBase):
    pass


class LessonContentUpdate(BaseModel):
    type: Optional[ContentType] = None
    title: Optional[str] = None
    order: Optional[int] = None
    estimated_time: Optional[int] = None
    required: Optional[bool] = None
    data: Optional[Dict[str, Any]] = None
    xp_reward: Optional[int] = None
    focus_area: Optional[FocusArea] = None


class LessonContentResponse(LessonContentBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    lesson_id: str
    created_at: datetime
    updated_at: datetime


# Lesson schemas
class LessonBase(BaseModel):
    id: str
    title: str = Field(..., min_length=1, max_length=200)
    description: str
    language: str = Field(..., min_length=2, max_length=10)
    level: CEFRLevel
    focus_area: FocusArea
    target_age_group: str = Field("adult", pattern="^(child|teen|young_adult|adult|senior)$")
    gamification_level: str = Field("medium", pattern="^(none|light|medium|full)$")
    duration: int = Field(..., gt=0)
    xp_reward: int = Field(..., ge=0)
    prerequisites: List[str] = []
    order: int
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class LessonCreate(LessonBase):
    content: List[LessonContentCreate] = []


class LessonUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    level: Optional[CEFRLevel] = None
    focus_area: Optional[FocusArea] = None
    target_age_group: Optional[str] = Field(None, pattern="^(child|teen|young_adult|adult|senior)$")
    gamification_level: Optional[str] = Field(None, pattern="^(none|light|medium|full)$")
    duration: Optional[int] = Field(None, gt=0)
    xp_reward: Optional[int] = Field(None, ge=0)
    prerequisites: Optional[List[str]] = None
    order: Optional[int] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    content: Optional[List[LessonContentCreate]] = None
    is_active: Optional[bool] = None
    is_premium: Optional[bool] = None


class LessonResponse(LessonBase):
    model_config = ConfigDict(from_attributes=True)
    
    is_active: bool
    is_premium: bool
    content: List[LessonContentResponse] = []
    created_at: datetime
    updated_at: datetime


class LessonListItem(BaseModel):
    """Lightweight lesson for lists"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    title: str
    description: str
    language: str
    level: CEFRLevel
    focus_area: FocusArea
    target_age_group: str = "adult"
    gamification_level: str = "medium"
    duration: int
    xp_reward: int
    prerequisites: List[str]
    tags: List[str]
    order: int
    is_active: bool
    is_premium: bool


# Lesson with progress
class LessonWithProgress(LessonResponse):
    progress: Optional["LessonProgressResponse"] = None
    is_unlocked: bool = True


# Vocabulary schemas
class VocabularyItemBase(BaseModel):
    language: str
    word: str
    translation: str
    transliteration: Optional[str] = None
    part_of_speech: Optional[str] = None
    difficulty: Optional[str] = None
    example_sentence: Optional[str] = None
    example_translation: Optional[str] = None
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
    tags: List[str] = []


class VocabularyItemCreate(VocabularyItemBase):
    pass


class VocabularyItemUpdate(BaseModel):
    translation: Optional[str] = None
    transliteration: Optional[str] = None
    part_of_speech: Optional[str] = None
    difficulty: Optional[str] = None
    example_sentence: Optional[str] = None
    example_translation: Optional[str] = None
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
    tags: Optional[List[str]] = None
    is_learned: Optional[bool] = None
    is_archived: Optional[bool] = None


class VocabularyItemResponse(VocabularyItemBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    ease_factor: float
    interval: int
    repetitions: int
    next_review: datetime
    last_reviewed: Optional[datetime] = None
    source_lesson_id: Optional[str] = None
    source_content_id: Optional[str] = None
    is_learned: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime


# Pronunciation Exercise schemas
class PronunciationExerciseBase(BaseModel):
    language: str
    level: CEFRLevel
    target_text: str
    translation: Optional[str] = None
    context: Optional[str] = None
    phonemes: List[Dict[str, Any]] = []
    audio_url: str
    duration: float
    difficulty: str = "medium"
    tips: List[str] = []
    tags: List[str] = []


class PronunciationExerciseCreate(PronunciationExerciseBase):
    pass


class PronunciationExerciseUpdate(BaseModel):
    target_text: Optional[str] = None
    translation: Optional[str] = None
    context: Optional[str] = None
    phonemes: Optional[List[Dict[str, Any]]] = None
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    difficulty: Optional[str] = None
    tips: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class PronunciationExerciseResponse(PronunciationExerciseBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Writing Prompt schemas
class WritingPromptBase(BaseModel):
    language: str
    level: CEFRLevel
    focus_area: FocusArea = FocusArea.WRITING
    prompt: str
    min_words: Optional[int] = None
    max_words: Optional[int] = None
    template: Optional[str] = None
    criteria: List[Dict[str, Any]] = []
    examples: List[str] = []
    vocabulary_hints: List[Dict[str, str]] = []
    tags: List[str] = []


class WritingPromptCreate(WritingPromptBase):
    pass


class WritingPromptUpdate(BaseModel):
    prompt: Optional[str] = None
    min_words: Optional[int] = None
    max_words: Optional[int] = None
    template: Optional[str] = None
    criteria: Optional[List[Dict[str, Any]]] = None
    examples: Optional[List[str]] = None
    vocabulary_hints: Optional[List[Dict[str, str]]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class WritingPromptResponse(WritingPromptBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Exercise Submission schemas
class ExerciseSubmission(BaseModel):
    lesson_id: str
    content_id: str
    answer: Any  # string, list, or dict depending on exercise type
    time_spent: int = 0  # seconds
    audio_data: Optional[str] = None  # base64 encoded audio for speaking exercises


class ExerciseResult(BaseModel):
    correct: bool
    score: float  # 0-100
    feedback: str
    corrections: List[Dict[str, Any]] = []
    xp_earned: int
    next_content_id: Optional[str] = None


# Pronunciation Evaluation schemas
class PronunciationEvaluationRequest(BaseModel):
    exercise_id: int
    audio_data: str  # base64 encoded audio
    target_text: str


class PronunciationEvaluationResponse(BaseModel):
    overall_score: float
    phoneme_scores: List[Dict[str, Any]]
    fluency_score: float
    intonation_score: float
    feedback: str
    xp_earned: int


# Writing Evaluation schemas
class WritingEvaluationRequest(BaseModel):
    prompt_id: int
    text: str
    criteria: Optional[List[str]] = None


class WritingEvaluationResponse(BaseModel):
    overall_score: float
    criteria_scores: Dict[str, float]
    corrections: List[Dict[str, Any]]
    feedback: str
    xp_earned: int


# Curriculum schemas
class CurriculumLevelResponse(BaseModel):
    level: CEFRLevel
    label: str
    total_lessons: int
    completed_lessons: int
    mastered_lessons: int
    total_duration: int
    total_xp: int
    progress_percent: int


class CurriculumResponse(BaseModel):
    levels: List[CurriculumLevelResponse]
    total_lessons: int
    total_duration: int
    total_xp: int
    current_level: CEFRLevel


# Rebuild models to resolve forward references
LessonWithProgress.model_rebuild()