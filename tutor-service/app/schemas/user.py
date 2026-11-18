"""
User schemas for Tutor Service API
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.user import CEFRLevel, UserRole


# Base schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    native_language: str = Field(default="en", min_length=2, max_length=10)
    target_language: str = Field(default="es", min_length=2, max_length=10)
    cefr_level: CEFRLevel = Field(default=CEFRLevel.A1)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    native_language: Optional[str] = Field(None, min_length=2, max_length=10)
    target_language: Optional[str] = Field(None, min_length=2, max_length=10)
    cefr_level: Optional[CEFRLevel] = None
    daily_goal_minutes: Optional[int] = Field(None, ge=5, le=120)
    auto_play_audio: Optional[bool] = None
    show_translations: Optional[bool] = None
    enable_haptics: Optional[bool] = None
    playback_speed: Optional[float] = Field(None, ge=0.5, le=2.0)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    avatar_url: Optional[str] = None
    xp: int
    streak: int
    longest_streak: int
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None


class UserWithProgress(UserResponse):
    progress: Optional["UserProgressResponse"] = None


# Progress schemas
class UserProgressBase(BaseModel):
    language: str
    current_level: CEFRLevel
    xp: int
    level_progress: float
    streak: int
    longest_streak: int
    total_time_spent: int
    lessons_completed: int
    lessons_mastered: int
    focus_area_progress: Dict[str, float]
    weak_areas: List[str]
    strong_areas: List[str]
    daily_goal_target: int
    daily_goal_completed: int
    daily_goal_streak: int
    daily_goal_last_completed: Optional[datetime] = None
    weekly_stats: Dict[str, Any]


class UserProgressCreate(UserProgressBase):
    pass


class UserProgressUpdate(BaseModel):
    current_level: Optional[CEFRLevel] = None
    xp: Optional[int] = None
    level_progress: Optional[float] = None
    streak: Optional[int] = None
    longest_streak: Optional[int] = None
    total_time_spent: Optional[int] = None
    lessons_completed: Optional[int] = None
    lessons_mastered: Optional[int] = None
    focus_area_progress: Optional[Dict[str, float]] = None
    weak_areas: Optional[List[str]] = None
    strong_areas: Optional[List[str]] = None
    daily_goal_completed: Optional[int] = None
    daily_goal_streak: Optional[int] = None
    daily_goal_last_completed: Optional[datetime] = None
    weekly_stats: Optional[Dict[str, Any]] = None


class UserProgressResponse(UserProgressBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


# Lesson Progress schemas
class LessonProgressBase(BaseModel):
    lesson_id: str
    status: str = "not_started"
    current_content_index: int = 0
    completed_content: List[str] = []
    score: Optional[float] = None
    mastery_level: int = 0
    attempts: int = 0
    time_spent: int = 0


class LessonProgressCreate(LessonProgressBase):
    pass


class LessonProgressUpdate(BaseModel):
    status: Optional[str] = None
    current_content_index: Optional[int] = None
    completed_content: Optional[List[str]] = None
    score: Optional[float] = None
    mastery_level: Optional[int] = None
    attempts: Optional[int] = None
    time_spent: Optional[int] = None


class LessonProgressResponse(LessonProgressBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    last_accessed: datetime


# Achievement schemas
class UserAchievementBase(BaseModel):
    achievement_id: str
    progress: int = 0
    target: int = 1
    unlocked: bool = False


class UserAchievementCreate(UserAchievementBase):
    pass


class UserAchievementUpdate(BaseModel):
    progress: Optional[int] = None
    unlocked: Optional[bool] = None


class UserAchievementResponse(UserAchievementBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    unlocked_at: Optional[datetime] = None
    created_at: datetime


# Practice Session schemas
class PracticeSessionBase(BaseModel):
    mode: str
    content_id: Optional[str] = None
    duration: int = 0
    score: Optional[float] = None
    xp_earned: int = 0
    corrections_count: int = 0
    metadata: Dict[str, Any] = {}


class PracticeSessionCreate(PracticeSessionBase):
    pass


class PracticeSessionResponse(PracticeSessionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None


# Chat Session schemas
class ChatMessageBase(BaseModel):
    role: str  # user, assistant, system
    content: str
    type: str = "text"
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class ChatSessionBase(BaseModel):
    session_id: str
    lesson_id: Optional[str] = None
    messages: List[ChatMessageBase] = []


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionResponse(ChatSessionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    message_count: int


# Auth schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(UserCreate):
    pass


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Password change
class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


# Email verification
class EmailVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationConfirm(BaseModel):
    email: EmailStr
    code: str


# Settings
class UserSettingsResponse(BaseModel):
    daily_goal_minutes: int
    auto_play_audio: bool
    show_translations: bool
    enable_haptics: bool
    playback_speed: float
    native_language: str
    target_language: str
    cefr_level: CEFRLevel


class UserSettingsUpdate(BaseModel):
    daily_goal_minutes: Optional[int] = Field(None, ge=5, le=120)
    auto_play_audio: Optional[bool] = None
    show_translations: Optional[bool] = None
    enable_haptics: Optional[bool] = None
    playback_speed: Optional[float] = Field(None, ge=0.5, le=2.0)
    native_language: Optional[str] = None
    target_language: Optional[str] = None
    cefr_level: Optional[CEFRLevel] = None