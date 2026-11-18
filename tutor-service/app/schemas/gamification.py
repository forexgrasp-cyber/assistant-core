"""Gamification Pydantic Schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Streak Schemas
# =============================================================================

class StreakResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_streak: int
    longest_streak: int
    last_activity_date: Optional[date] = None
    freezes_available: int
    freezes_used_this_week: int
    weekend_amulet_active: bool
    weekend_amulet_expires: Optional[datetime] = None
    repairs_used: int


# =============================================================================
# XP & Level Schemas
# =============================================================================

class XPResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_xp: int
    level: int
    xp_to_next_level: int
    league_tier: str
    league_rank: int
    weekly_xp: int
    gems: int


# =============================================================================
# Quest Schemas
# =============================================================================

class QuestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quest_type: str
    title: str
    description: str
    target_value: int
    current_value: int
    xp_reward: int
    gems_reward: int
    is_daily: bool
    status: str
    expires_at: datetime
    completed_at: Optional[datetime] = None
    claimed_at: Optional[datetime] = None


class QuestProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quest_id: int
    quest_type: str
    current_value: int
    target_value: int
    completed: bool
    claimed: bool


class DailyQuestGenerateResponse(BaseModel):
    quests: List[QuestResponse]


class QuestClaimResponse(BaseModel):
    xp_awarded: int
    new_level: int
    leveled_up: bool
    total_xp: int
    gems: int
    message: str


# =============================================================================
# Achievement Schemas
# =============================================================================

class AchievementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name: str
    description: str
    category: str
    icon: str
    xp_reward: int
    gems_reward: int
    criteria: Dict[str, Any]
    is_hidden: bool
    unlocked: bool = False
    unlocked_at: Optional[datetime] = None


class UserAchievementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    achievement_id: int
    key: str
    name: str
    description: str
    category: str
    icon: str
    xp_reward: int
    gems_reward: int
    unlocked_at: datetime


# =============================================================================
# League Schemas
# =============================================================================

class LeagueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tier: str
    rank: int
    weekly_xp: int
    previous_tier: Optional[str] = None
    previous_rank: Optional[int] = None


# =============================================================================
# Friend Schemas
# =============================================================================

class FriendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    friend_id: int
    friend_username: str
    friend_full_name: Optional[str] = None
    friend_avatar_url: Optional[str] = None
    status: str
    created_at: datetime
    accepted_at: Optional[datetime] = None


# =============================================================================
# Gem Schemas
# =============================================================================

class GemBalanceResponse(BaseModel):
    gems: int


class GemTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    amount: int
    balance_after: int
    description: str
    reference_id: Optional[int] = None
    reference_type: Optional[str] = None
    created_at: datetime