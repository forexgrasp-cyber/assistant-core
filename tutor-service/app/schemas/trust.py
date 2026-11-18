"""Trust & Social Proof Pydantic Schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =============================================================================
# Trust Stats / Signals
# =============================================================================

class TrustStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_users: int
    total_lessons_completed: int
    total_countries: int
    average_rating: float
    total_hours_learned: int
    languages_offered: int
    active_learners_today: int
    success_stories: int


class TrustSignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    value: int
    display_format: str
    icon: Optional[str] = None
    description: Optional[str] = None


# =============================================================================
# Testimonials
# =============================================================================

class TestimonialSubmitRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=2000)
    rating: int = Field(..., ge=1, le=5)
    language: Optional[str] = Field(None, pattern="^[a-z]{2}$")
    cefr_level: Optional[str] = Field(None, pattern="^(A1|A2|B1|B2|C1|C2)$")


class TestimonialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    rating: int
    author_name: str
    author_avatar_url: Optional[str] = None
    author_location: Optional[str] = None
    author_level: Optional[int] = None
    language: Optional[str] = None
    cefr_level: Optional[str] = None
    is_featured: bool
    created_at: datetime


# =============================================================================
# Activity Feed
# =============================================================================

class ActivityFeedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user_name: str
    user_avatar_url: Optional[str] = None
    user_location: Optional[str] = None
    activity_type: str
    title: str
    description: str
    language: Optional[str] = None
    created_at: datetime


# =============================================================================
# Referrals
# =============================================================================

class ReferralCreateRequest(BaseModel):
    email: EmailStr


class ReferralResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    referred_email: str
    status: str
    referrer_reward_gems: int
    referred_reward_gems: int
    created_at: datetime


class ReferralStatsResponse(BaseModel):
    total_referrals: int
    signed_up: int
    activated: int
    rewarded: int
    conversion_rate: float
    total_gems_earned: int
    total_xp_earned: int
    referral_code: str


# =============================================================================
# Press Mentions
# =============================================================================

class PressMentionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    publication: str
    publication_logo_url: Optional[str] = None
    url: Optional[str] = None
    excerpt: Optional[str] = None
    published_at: date
    is_featured: bool