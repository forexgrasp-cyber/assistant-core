"""Gamification Service - Core logic for streaks, XP, leagues, quests, achievements."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.gamification import (
    UserStreak,
    UserXP,
    UserQuest,
    Achievement,
    LeagueStanding,
    UserFriend,
    GemTransaction,
    LeagueTier,
    QuestType,
    AchievementCategory,
)
from app.models.user import User, UserAchievement, LessonProgress
from app.core.config import settings


# =============================================================================
# Constants
# =============================================================================

XP_PER_LEVEL_BASE = 100
XP_PER_LEVEL_MULTIPLIER = 1.5

LEAGUE_TIERS = [
    LeagueTier.BRONZE,
    LeagueTier.SILVER,
    LeagueTier.GOLD,
    LeagueTier.PLATINUM,
    LeagueTier.DIAMOND,
    LeagueTier.OBSIDIAN,
]

LEAGUE_SIZE = 30  # Users per league
PROMOTION_COUNT = 10  # Top 10 promote
DEMOTION_COUNT = 5   # Bottom 5 demote

# XP Rewards
XP_REWARDS = {
    "lesson_complete": 50,
    "lesson_perfect": 100,
    "practice_minute": 5,
    "word_review": 2,
    "streak_bonus": 10,  # Per day of streak
    "quest_complete": 0,  # Varies by quest
    "achievement_unlock": 0,  # Varies by achievement
    "human_tutor_session": 200,
    "social_share": 25,
}

# Gem costs
GEM_COSTS = {
    "streak_freeze": 50,
    "streak_repair": 200,
    "weekend_amulet": 300,
    "legendary_outfit": 1000,
}

# Daily Quest Templates
DAILY_QUEST_TEMPLATES = [
    {
        "type": QuestType.COMPLETE_LESSONS,
        "title": "Lesson Learner",
        "description": "Complete {target} lessons today",
        "target_range": (2, 4),
        "xp_reward": 50,
        "gems_reward": 5,
    },
    {
        "type": QuestType.PRACTICE_MINUTES,
        "title": "Practice Makes Perfect",
        "description": "Practice for {target} minutes",
        "target_range": (10, 20),
        "xp_reward": 40,
        "gems_reward": 3,
    },
    {
        "type": QuestType.REVIEW_WORDS,
        "title": "Vocabulary Review",
        "description": "Review {target} words",
        "target_range": (10, 20),
        "xp_reward": 30,
        "gems_reward": 2,
    },
    {
        "type": QuestType.PERFECT_LESSON,
        "title": "Perfectionist",
        "description": "Complete a lesson with 100% accuracy",
        "target_range": (1, 1),
        "xp_reward": 75,
        "gems_reward": 10,
    },
    {
        "type": QuestType.STREAK_MAINTAIN,
        "title": "Streak Keeper",
        "description": "Maintain your streak today",
        "target_range": (1, 1),
        "xp_reward": 25,
        "gems_reward": 5,
    },
]

WEEKLY_QUEST_TEMPLATES = [
    {
        "type": QuestType.COMPLETE_LESSONS,
        "title": "Weekly Scholar",
        "description": "Complete {target} lessons this week",
        "target_range": (15, 25),
        "xp_reward": 300,
        "gems_reward": 30,
    },
    {
        "type": QuestType.PRACTICE_MINUTES,
        "title": "Dedication",
        "description": "Practice for {target} minutes this week",
        "target_range": (120, 180),
        "xp_reward": 250,
        "gems_reward": 25,
    },
    {
        "type": QuestType.HUMAN_TUTOR_SESSION,
        "title": "Conversation Partner",
        "description": "Complete {target} human tutor session(s)",
        "target_range": (1, 2),
        "xp_reward": 500,
        "gems_reward": 50,
    },
]


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class StreakResult:
    """Result of streak update."""
    streak_updated: bool
    current_streak: int
    longest_streak: int
    freeze_used: bool
    repair_used: bool
    xp_bonus: int
    message: str


@dataclass
class XPResult:
    """Result of XP award."""
    xp_awarded: int
    total_xp: int
    new_level: int
    leveled_up: bool
    league_updated: bool
    message: str


@dataclass
class QuestProgress:
    """Quest progress update."""
    quest_id: int
    quest_type: QuestType
    current_value: int
    target_value: int
    completed: bool
    claimed: bool


# =============================================================================
# Gamification Service
# =============================================================================

class GamificationService:
    """Core gamification logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Streak Management
    # -------------------------------------------------------------------------

    async def get_or_create_streak(self, user_id: int) -> UserStreak:
        """Get or create user's streak record."""
        result = await self.db.execute(
            select(UserStreak).where(UserStreak.user_id == user_id)
        )
        streak = result.scalar_one_or_none()
        if not streak:
            streak = UserStreak(user_id=user_id)
            self.db.add(streak)
            await self.db.flush()
        return streak

    async def update_streak_on_activity(self, user_id: int, activity_date: Optional[date] = None) -> StreakResult:
        """Update streak when user completes an activity."""
        if activity_date is None:
            activity_date = date.today()

        streak = await self.get_or_create_streak(user_id)
        today = date.today()
        yesterday = today - timedelta(days=1)

        freeze_used = False
        repair_used = False
        xp_bonus = 0
        streak_updated = False
        message = ""

        if streak.last_activity_date == today:
            # Already active today
            return StreakResult(
                streak_updated=False,
                current_streak=streak.current_streak,
                longest_streak=streak.longest_streak,
                freeze_used=False,
                repair_used=False,
                xp_bonus=0,
                message="Streak already active today",
            )

        if streak.last_activity_date == yesterday:
            # Continued streak
            streak.current_streak += 1
            streak.last_activity_date = today
            streak_updated = True
            xp_bonus = min(streak.current_streak * 2, 100)  # Streak bonus XP, capped
            message = f"Streak continued! Day {streak.current_streak}"

        elif streak.last_activity_date is None or streak.last_activity_date < yesterday:
            # Streak broken - check for freeze/amulet
            days_missed = (today - (streak.last_activity_date or today)).days

            # Check weekend amulet
            if streak.weekend_amulet_active and streak.weekend_amulet_expires:
                if streak.weekend_amulet_expires.replace(tzinfo=None) > datetime.now():
                    if activity_date.weekday() in (5, 6):  # Sat/Sun
                        streak.current_streak += 1
                        streak.last_activity_date = today
                        streak_updated = True
                        message = "Weekend amulet protected your streak!"
                    else:
                        # Weekday after weekend - amulet expires
                        streak.weekend_amulet_active = False

            # Check streak freeze
            if not streak_updated and days_missed == 1 and streak.freezes_available > 0:
                streak.current_streak += 1
                streak.last_activity_date = today
                streak.freezes_available -= 1
                streak.freezes_used_this_week += 1
                freeze_used = True
                streak_updated = True
                message = "Streak freeze used! Streak preserved."

            # Streak broken - reset
            if not streak_updated:
                streak.current_streak = 1
                streak.last_activity_date = today
                message = "Streak broken! Starting fresh at day 1."

        # Update longest streak
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak

        # Reset weekly freeze counter on Monday
        if today.weekday() == 0:  # Monday
            streak.freezes_used_this_week = 0
            streak.freezes_available = min(streak.freezes_available + 1, 3)  # Max 3 banked

        await self.db.flush()
        return StreakResult(
            streak_updated=streak_updated,
            current_streak=streak.current_streak,
            longest_streak=streak.longest_streak,
            freeze_used=freeze_used,
            repair_used=repair_used,
            xp_bonus=xp_bonus,
            message=message,
        )

    async def use_streak_freeze(self, user_id: int) -> bool:
        """Manually use a streak freeze (costs gems)."""
        streak = await self.get_or_create_streak(user_id)
        xp_record = await self.get_or_create_xp(user_id)

        if streak.freezes_available > 0:
            streak.freezes_available -= 1
            streak.freezes_used_this_week += 1
            await self._spend_gems(user_id, GEM_COSTS["streak_freeze"], "streak_freeze", "Manual streak freeze")
            return True
        elif xp_record.gems >= GEM_COSTS["streak_freeze"]:
            # Buy freeze with gems
            streak.freezes_available += 1
            streak.freezes_used_this_week += 1
            streak.freezes_available -= 1
            await self._spend_gems(user_id, GEM_COSTS["streak_freeze"], "streak_freeze", "Purchased streak freeze")
            return True
        return False

    async def repair_streak(self, user_id: int, target_date: date) -> bool:
        """Repair a broken streak (costs gems)."""
        streak = await self.get_or_create_streak(user_id)
        xp_record = await self.get_or_create_xp(user_id)

        if xp_record.gems < GEM_COSTS["streak_repair"]:
            return False

        days_since_activity = (date.today() - (streak.last_activity_date or date.today())).days
        if days_since_activity > 30:  # Can't repair ancient streaks
            return False

        # Repair: set streak to what it would have been
        streak.current_streak += days_since_activity
        streak.last_activity_date = target_date
        streak.repairs_used += 1
        streak.last_repair_date = date.today()

        await self._spend_gems(user_id, GEM_COSTS["streak_repair"], "streak_repair", f"Streak repair ({days_since_activity} days)")
        return True

    async def activate_weekend_amulet(self, user_id: int) -> bool:
        """Activate weekend amulet (protects Sat/Sun streak)."""
        streak = await self.get_or_create_streak(user_id)
        xp_record = await self.get_or_create_xp(user_id)

        if xp_record.gems < GEM_COSTS["weekend_amulet"]:
            return False

        streak.weekend_amulet_active = True
        streak.weekend_amulet_expires = datetime.now() + timedelta(days=7)
        await self._spend_gems(user_id, GEM_COSTS["weekend_amulet"], "weekend_amulet", "Weekend amulet activated")
        return True

    # -------------------------------------------------------------------------
    # XP & Level Management
    # -------------------------------------------------------------------------

    async def get_or_create_xp(self, user_id: int) -> UserXP:
        """Get or create user's XP record."""
        result = await self.db.execute(
            select(UserXP).where(UserXP.user_id == user_id)
        )
        xp = result.scalar_one_or_none()
        if not xp:
            xp = UserXP(user_id=user_id)
            self.db.add(xp)
            await self.db.flush()
        return xp

    def _calculate_xp_for_level(self, level: int) -> int:
        """Calculate XP required for a given level."""
        return int(XP_PER_LEVEL_BASE * (XP_PER_LEVEL_MULTIPLIER ** (level - 1)))

    async def award_xp(
        self,
        user_id: int,
        amount: int,
        source: str,
        reference_id: Optional[int] = None,
        reference_type: Optional[str] = None,
    ) -> XPResult:
        """Award XP to user, handle level ups and league updates."""
        xp_record = await self.get_or_create_xp(user_id)

        old_level = xp_record.level
        old_total_xp = xp_record.total_xp

        xp_record.total_xp += amount
        xp_record.weekly_xp += amount

        # Check for level up
        leveled_up = False
        while xp_record.total_xp >= xp_record.xp_to_next_level:
            xp_record.total_xp -= xp_record.xp_to_next_level
            xp_record.level += 1
            xp_record.xp_to_next_level = self._calculate_xp_for_level(xp_record.level)
            leveled_up = True

        new_level = xp_record.level

        # Award gems on level up
        if leveled_up:
            gem_bonus = new_level * 10
            xp_record.gems += gem_bonus
            xp_record.gems_earned_total += gem_bonus
            await self._record_gem_transaction(
                user_id, gem_bonus, "earned", f"Level up to {new_level}", reference_id, reference_type
            )

        # Update league if weekly XP changed significantly
        league_updated = await self._maybe_update_league(user_id, xp_record)

        await self.db.flush()

        return XPResult(
            xp_awarded=amount,
            total_xp=xp_record.total_xp + (old_total_xp - xp_record.total_xp + amount),  # Actual total
            new_level=new_level,
            leveled_up=leveled_up,
            league_updated=league_updated,
            message=f"+{amount} XP" + (f" • Level {new_level}!" if leveled_up else ""),
        )

    async def _maybe_update_league(self, user_id: int, xp_record: UserXP) -> bool:
        """Check and update user's league tier based on weekly XP."""
        # This is a simplified version - full league calculation runs weekly
        # Just update the tier based on total XP for now
        total_xp = xp_record.total_xp + (xp_record.level - 1) * XP_PER_LEVEL_BASE

        # Rough tier assignment based on total XP
        if total_xp >= 50000:
            new_tier = LeagueTier.OBSIDIAN
        elif total_xp >= 20000:
            new_tier = LeagueTier.DIAMOND
        elif total_xp >= 8000:
            new_tier = LeagueTier.PLATINUM
        elif total_xp >= 3000:
            new_tier = LeagueTier.GOLD
        elif total_xp >= 1000:
            new_tier = LeagueTier.SILVER
        else:
            new_tier = LeagueTier.BRONZE

        if new_tier != xp_record.league_tier:
            xp_record.league_tier = new_tier
            return True
        return False

    # -------------------------------------------------------------------------
    # Quest Management
    # -------------------------------------------------------------------------

    async def get_active_quests(self, user_id: int) -> List[UserQuest]:
        """Get user's active quests."""
        result = await self.db.execute(
            select(UserQuest)
            .where(
                UserQuest.user_id == user_id,
                UserQuest.status == "active",
                UserQuest.expires_at > datetime.now(timezone.utc),
            )
            .order_by(UserQuest.is_daily.desc(), UserQuest.created_at)
        )
        return list(result.scalars().all())

    async def generate_daily_quests(self, user_id: int) -> List[UserQuest]:
        """Generate 3 daily quests for user."""
        # Clear expired quests
        await self.db.execute(
            delete(UserQuest).where(
                UserQuest.user_id == user_id,
                UserQuest.is_daily == True,
                UserQuest.expires_at < datetime.now(timezone.utc),
            )
        )

        # Check existing active daily quests
        existing = await self.get_active_quests(user_id)
        daily_existing = [q for q in existing if q.is_daily]
        if len(daily_existing) >= 3:
            return daily_existing

        # Generate new quests
        templates = random.sample(DAILY_QUEST_TEMPLATES, k=min(3, len(DAILY_QUEST_TEMPLATES)))
        quests = []
        expires_at = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=0) + timedelta(days=1)

        for template in templates:
            target = random.randint(*template["target_range"])
            quest = UserQuest(
                user_id=user_id,
                quest_type=template["type"],
                title=template["title"],
                description=template["description"].format(target=target),
                target_value=target,
                current_value=0,
                xp_reward=template["xp_reward"],
                gems_reward=template["gems_reward"],
                is_daily=True,
                expires_at=expires_at,
            )
            self.db.add(quest)
            quests.append(quest)

        await self.db.flush()
        return quests

    async def generate_weekly_quests(self, user_id: int) -> List[UserQuest]:
        """Generate 1-2 weekly quests for user."""
        # Similar to daily but weekly
        existing = await self.get_active_quests(user_id)
        weekly_existing = [q for q in existing if not q.is_daily]
        if weekly_existing:
            return weekly_existing

        templates = random.sample(WEEKLY_QUEST_TEMPLATES, k=min(2, len(WEEKLY_QUEST_TEMPLATES)))
        quests = []
        # Expires next Monday 23:59
        now = datetime.now(timezone.utc)
        days_until_monday = (7 - now.weekday()) % 7 or 7
        expires_at = now.replace(hour=23, minute=59, second=59, microsecond=0) + timedelta(days=days_until_monday)

        for template in templates:
            target = random.randint(*template["target_range"])
            quest = UserQuest(
                user_id=user_id,
                quest_type=template["type"],
                title=template["title"],
                description=template["description"].format(target=target),
                target_value=target,
                current_value=0,
                xp_reward=template["xp_reward"],
                gems_reward=template["gems_reward"],
                is_daily=False,
                expires_at=expires_at,
            )
            self.db.add(quest)
            quests.append(quest)

        await self.db.flush()
        return quests

    async def update_quest_progress(
        self,
        user_id: int,
        quest_type: QuestType,
        increment: int = 1,
    ) -> List[QuestProgress]:
        """Update progress for quests matching type."""
        quests = await self.get_active_quests(user_id)
        matching = [q for q in quests if q.quest_type == quest_type and q.status == "active"]

        results = []
        for quest in matching:
            old_value = quest.current_value
            quest.current_value = min(quest.current_value + increment, quest.target_value)

            completed = quest.current_value >= quest.target_value
            if completed and quest.status == "active":
                quest.status = "completed"
                quest.completed_at = datetime.now(timezone.utc)

            results.append(QuestProgress(
                quest_id=quest.id,
                quest_type=quest.quest_type,
                current_value=quest.current_value,
                target_value=quest.target_value,
                completed=completed,
                claimed=quest.status == "claimed",
            ))

        await self.db.flush()
        return results

    async def claim_quest_reward(self, user_id: int, quest_id: int) -> Optional[XPResult]:
        """Claim completed quest reward."""
        result = await self.db.execute(
            select(UserQuest).where(
                UserQuest.id == quest_id,
                UserQuest.user_id == user_id,
                UserQuest.status == "completed",
            )
        )
        quest = result.scalar_one_or_none()
        if not quest:
            return None

        quest.status = "claimed"
        quest.claimed_at = datetime.now(timezone.utc)

        # Award XP
        xp_result = await self.award_xp(user_id, quest.xp_reward, f"quest_{quest.quest_type.value}", quest.id, "quest")

        # Award gems
        if quest.gems_reward > 0:
            xp_record = await self.get_or_create_xp(user_id)
            xp_record.gems += quest.gems_reward
            xp_record.gems_earned_total += quest.gems_reward
            await self._record_gem_transaction(
                user_id, quest.gems_reward, "earned", f"Quest reward: {quest.title}", quest.id, "quest"
            )

        await self.db.flush()
        return xp_result

    # -------------------------------------------------------------------------
    # Achievements
    # -------------------------------------------------------------------------

    async def check_achievements(self, user_id: int) -> List[Achievement]:
        """Check and unlock any new achievements for user."""
        # Get user stats
        streak = await self.get_or_create_streak(user_id)
        xp_record = await self.get_or_create_xp(user_id)

        # Get lesson stats
        lesson_result = await self.db.execute(
            select(func.count(LessonProgress.id)).where(
                LessonProgress.user_id == user_id,
                LessonProgress.completed == True,
            )
        )
        lessons_completed = lesson_result.scalar() or 0

        perfect_result = await self.db.execute(
            select(func.count(LessonProgress.id)).where(
                LessonProgress.user_id == user_id,
                LessonProgress.score == 100,
            )
        )
        perfect_lessons = perfect_result.scalar() or 0

        # Get all achievements not yet unlocked (using existing UserAchievement model)
        unlocked_subq = select(UserAchievement.achievement_id).where(UserAchievement.user_id == user_id)
        result = await self.db.execute(
            select(Achievement).where(
                Achievement.id.not_in(unlocked_subq),
                Achievement.is_hidden == False,
            )
        )
        available_achievements = list(result.scalars().all())

        newly_unlocked = []
        for achievement in available_achievements:
            if self._check_achievement_criteria(achievement, {
                "streak_days": streak.current_streak,
                "longest_streak": streak.longest_streak,
                "total_xp": xp_record.total_xp,
                "level": xp_record.level,
                "lessons_completed": lessons_completed,
                "perfect_lessons": perfect_lessons,
                "league_tier": xp_record.league_tier.value,
                "gems_earned": xp_record.gems_earned_total,
            }):
                # Use existing UserAchievement model (achievement_id is String)
                unlocked = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id,  # String ID
                    unlocked=True,
                    unlocked_at=datetime.now(timezone.utc),
                    progress=1,
                    target=1,
                )
                self.db.add(unlocked)
                newly_unlocked.append(achievement)

                # Award rewards
                if achievement.xp_reward > 0:
                    await self.award_xp(user_id, achievement.xp_reward, f"achievement_{achievement.key}", achievement.id, "achievement")
                if achievement.gems_reward > 0:
                    xp_record.gems += achievement.gems_reward
                    xp_record.gems_earned_total += achievement.gems_reward
                    await self._record_gem_transaction(
                        user_id, achievement.gems_reward, "earned", f"Achievement: {achievement.name}", achievement.id, "achievement"
                    )

        await self.db.flush()
        return newly_unlocked

    def _check_achievement_criteria(self, achievement: Achievement, stats: Dict[str, Any]) -> bool:
        """Check if user meets achievement criteria."""
        criteria = achievement.criteria
        for key, required_value in criteria.items():
            if key not in stats:
                return False
            if isinstance(required_value, dict):
                # Complex criteria (e.g., {"min": 7, "max": 30})
                if "min" in required_value and stats[key] < required_value["min"]:
                    return False
                if "max" in required_value and stats[key] > required_value["max"]:
                    return False
            else:
                if stats[key] < required_value:
                    return False
        return True

    async def get_user_achievements(self, user_id: int) -> List[UserAchievement]:
        """Get all unlocked achievements for user."""
        result = await self.db.execute(
            select(UserAchievement)
            .where(UserAchievement.user_id == user_id)
            .order_by(UserAchievement.unlocked_at.desc().nullslast())
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # League System (Weekly)
    # -------------------------------------------------------------------------

    async def run_weekly_league_update(self) -> Dict[str, int]:
        """Run weekly league calculation (called by cron)."""
        # This is a heavy operation - run weekly via cron
        # Simplified version here
        pass

    # -------------------------------------------------------------------------
    # Social / Friends
    # -------------------------------------------------------------------------

    async def add_friend(self, user_id: int, friend_username: str) -> Optional[UserFriend]:
        """Send friend request."""
        result = await self.db.execute(
            select(User).where(User.username == friend_username)
        )
        friend = result.scalar_one_or_none()
        if not friend or friend.id == user_id:
            return None

        # Check existing relationship
        existing = await self.db.execute(
            select(UserFriend).where(
                or_(
                    and_(UserFriend.user_id == user_id, UserFriend.friend_id == friend.id),
                    and_(UserFriend.user_id == friend.id, UserFriend.friend_id == user_id),
                )
            )
        )
        if existing.scalar_one_or_none():
            return None

        friendship = UserFriend(user_id=user_id, friend_id=friend.id, status="pending")
        self.db.add(friendship)
        await self.db.flush()
        return friendship

    async def accept_friend(self, user_id: int, friend_id: int) -> bool:
        """Accept friend request."""
        result = await self.db.execute(
            select(UserFriend).where(
                UserFriend.user_id == friend_id,
                UserFriend.friend_id == user_id,
                UserFriend.status == "pending",
            )
        )
        friendship = result.scalar_one_or_none()
        if not friendship:
            return False

        friendship.status = "accepted"
        friendship.accepted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    async def get_friends(self, user_id: int) -> List[UserFriend]:
        """Get user's accepted friends."""
        result = await self.db.execute(
            select(UserFriend)
            .options(selectinload(UserFriend.friend))
            .where(
                UserFriend.user_id == user_id,
                UserFriend.status == "accepted",
            )
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Gem Management
    # -------------------------------------------------------------------------

    async def _spend_gems(self, user_id: int, amount: int, type_: str, description: str, reference_id: Optional[int] = None, reference_type: Optional[str] = None) -> bool:
        """Spend gems, return False if insufficient."""
        xp_record = await self.get_or_create_xp(user_id)
        if xp_record.gems < amount:
            return False

        xp_record.gems -= amount
        xp_record.gems_spent_total += amount
        await self._record_gem_transaction(user_id, -amount, type_, description, reference_id, reference_type)
        return True

    async def _record_gem_transaction(
        self,
        user_id: int,
        amount: int,
        type_: str,
        description: str,
        reference_id: Optional[int] = None,
        reference_type: Optional[str] = None,
    ) -> GemTransaction:
        """Record gem transaction."""
        xp_record = await self.get_or_create_xp(user_id)
        txn = GemTransaction(
            user_id=user_id,
            type=type_,
            amount=amount,
            balance_after=xp_record.gems,
            description=description,
            reference_id=reference_id,
            reference_type=reference_type,
        )
        self.db.add(txn)
        return txn

    async def get_gem_balance(self, user_id: int) -> int:
        """Get current gem balance."""
        xp_record = await self.get_or_create_xp(user_id)
        return xp_record.gems

    async def get_gem_history(self, user_id: int, limit: int = 50) -> List[GemTransaction]:
        """Get gem transaction history."""
        result = await self.db.execute(
            select(GemTransaction)
            .where(GemTransaction.user_id == user_id)
            .order_by(GemTransaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())