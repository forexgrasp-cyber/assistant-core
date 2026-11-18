"""Gamification API Endpoints."""

from __future__ import annotations

from typing import List, Optional
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.gamification import Achievement
from app.schemas.gamification import (
    StreakResponse,
    XPResponse,
    QuestResponse,
    QuestProgressResponse,
    AchievementResponse,
    UserAchievementResponse,
    LeagueResponse,
    FriendResponse,
    GemBalanceResponse,
    GemTransactionResponse,
    DailyQuestGenerateResponse,
    QuestClaimResponse,
)
from app.services.gamification_service import GamificationService

router = APIRouter(prefix="/gamification", tags=["gamification"])


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    # TODO: Add proper JWT auth - for now using first user for testing
) -> User:
    """Get current user from token."""
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# =============================================================================
# Streak Endpoints
# =============================================================================

@router.get("/streak", response_model=StreakResponse)
async def get_streak(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's current streak info."""
    service = GamificationService(db)
    streak = await service.get_or_create_streak(current_user.id)
    return StreakResponse(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_activity_date=streak.last_activity_date,
        freezes_available=streak.freezes_available,
        freezes_used_this_week=streak.freezes_used_this_week,
        weekend_amulet_active=streak.weekend_amulet_active,
        weekend_amulet_expires=streak.weekend_amulet_expires,
        repairs_used=streak.repairs_used,
    )


@router.post("/streak/activity", response_model=StreakResponse)
async def record_activity(
    activity_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record activity for today (updates streak)."""
    service = GamificationService(db)
    result = await service.update_streak_on_activity(current_user.id, activity_date)
    streak = await service.get_or_create_streak(current_user.id)
    return StreakResponse(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_activity_date=streak.last_activity_date,
        freezes_available=streak.freezes_available,
        freezes_used_this_week=streak.freezes_used_this_week,
        weekend_amulet_active=streak.weekend_amulet_active,
        weekend_amulet_expires=streak.weekend_amulet_expires,
        repairs_used=streak.repairs_used,
    )


@router.post("/streak/freeze", response_model=StreakResponse)
async def use_streak_freeze(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Use a streak freeze (costs gems if no free freezes)."""
    service = GamificationService(db)
    success = await service.use_streak_freeze(current_user.id)
    if not success:
        raise HTTPException(status_code=400, detail="Insufficient gems for streak freeze")
    streak = await service.get_or_create_streak(current_user.id)
    return StreakResponse(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_activity_date=streak.last_activity_date,
        freezes_available=streak.freezes_available,
        freezes_used_this_week=streak.freezes_used_this_week,
        weekend_amulet_active=streak.weekend_amulet_active,
        weekend_amulet_expires=streak.weekend_amulet_expires,
        repairs_used=streak.repairs_used,
    )


@router.post("/streak/repair", response_model=StreakResponse)
async def repair_streak(
    target_date: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Repair a broken streak (costs gems)."""
    service = GamificationService(db)
    success = await service.repair_streak(current_user.id, target_date)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot repair streak (insufficient gems or too old)")
    streak = await service.get_or_create_streak(current_user.id)
    return StreakResponse(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_activity_date=streak.last_activity_date,
        freezes_available=streak.freezes_available,
        freezes_used_this_week=streak.freezes_used_this_week,
        weekend_amulet_active=streak.weekend_amulet_active,
        weekend_amulet_expires=streak.weekend_amulet_expires,
        repairs_used=streak.repairs_used,
    )


@router.post("/streak/weekend-amulet", response_model=StreakResponse)
async def activate_weekend_amulet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Activate weekend amulet (protects Sat/Sun streak for a week)."""
    service = GamificationService(db)
    success = await service.activate_weekend_amulet(current_user.id)
    if not success:
        raise HTTPException(status_code=400, detail="Insufficient gems for weekend amulet")
    streak = await service.get_or_create_streak(current_user.id)
    return StreakResponse(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_activity_date=streak.last_activity_date,
        freezes_available=streak.freezes_available,
        freezes_used_this_week=streak.freezes_used_this_week,
        weekend_amulet_active=streak.weekend_amulet_active,
        weekend_amulet_expires=streak.weekend_amulet_expires,
        repairs_used=streak.repairs_used,
    )


# =============================================================================
# XP & Level Endpoints
# =============================================================================

@router.get("/xp", response_model=XPResponse)
async def get_xp(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's XP, level, and league info."""
    service = GamificationService(db)
    xp = await service.get_or_create_xp(current_user.id)
    return XPResponse(
        total_xp=xp.total_xp,
        level=xp.level,
        xp_to_next_level=xp.xp_to_next_level,
        league_tier=xp.league_tier.value,
        league_rank=xp.league_rank,
        weekly_xp=xp.weekly_xp,
        gems=xp.gems,
    )


@router.post("/xp/award", response_model=XPResponse)
async def award_xp(
    amount: int,
    source: str,
    reference_id: Optional[int] = None,
    reference_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Award XP to user (internal use)."""
    service = GamificationService(db)
    result = await service.award_xp(current_user.id, amount, source, reference_id, reference_type)
    xp = await service.get_or_create_xp(current_user.id)
    return XPResponse(
        total_xp=xp.total_xp,
        level=xp.level,
        xp_to_next_level=xp.xp_to_next_level,
        league_tier=xp.league_tier.value,
        league_rank=xp.league_rank,
        weekly_xp=xp.weekly_xp,
        gems=xp.gems,
    )


# =============================================================================
# Quest Endpoints
# =============================================================================

@router.get("/quests", response_model=List[QuestResponse])
async def get_quests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's active quests (daily + weekly)."""
    service = GamificationService(db)
    daily_quests = await service.generate_daily_quests(current_user.id)
    weekly_quests = await service.generate_weekly_quests(current_user.id)
    all_quests = daily_quests + weekly_quests
    return [
        QuestResponse(
            id=q.id,
            quest_type=q.quest_type.value,
            title=q.title,
            description=q.description,
            target_value=q.target_value,
            current_value=q.current_value,
            xp_reward=q.xp_reward,
            gems_reward=q.gems_reward,
            is_daily=q.is_daily,
            status=q.status,
            expires_at=q.expires_at,
            completed_at=q.completed_at,
            claimed_at=q.claimed_at,
        )
        for q in all_quests
    ]


@router.post("/quests/daily/generate", response_model=DailyQuestGenerateResponse)
async def generate_daily_quests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate new daily quests (replaces existing)."""
    service = GamificationService(db)
    quests = await service.generate_daily_quests(current_user.id)
    return DailyQuestGenerateResponse(
        quests=[
            QuestResponse(
                id=q.id,
                quest_type=q.quest_type.value,
                title=q.title,
                description=q.description,
                target_value=q.target_value,
                current_value=q.current_value,
                xp_reward=q.xp_reward,
                gems_reward=q.gems_reward,
                is_daily=q.is_daily,
                status=q.status,
                expires_at=q.expires_at,
                completed_at=q.completed_at,
                claimed_at=q.claimed_at,
            )
            for q in quests
        ]
    )


@router.post("/quests/progress", response_model=List[QuestProgressResponse])
async def update_quest_progress(
    quest_type: str,
    increment: int = 1,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update progress for quests of a specific type."""
    from app.models.gamification import QuestType
    try:
        qt = QuestType(quest_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid quest type")

    service = GamificationService(db)
    results = await service.update_quest_progress(current_user.id, qt, increment)
    return [
        QuestProgressResponse(
            quest_id=r.quest_id,
            quest_type=r.quest_type.value,
            current_value=r.current_value,
            target_value=r.target_value,
            completed=r.completed,
            claimed=r.claimed,
        )
        for r in results
    ]


@router.post("/quests/{quest_id}/claim", response_model=QuestClaimResponse)
async def claim_quest_reward(
    quest_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Claim reward for completed quest."""
    service = GamificationService(db)
    result = await service.claim_quest_reward(current_user.id, quest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Quest not found or not completed")

    xp = await service.get_or_create_xp(current_user.id)
    return QuestClaimResponse(
        xp_awarded=result.xp_awarded,
        new_level=result.new_level,
        leveled_up=result.leveled_up,
        total_xp=xp.total_xp,
        gems=xp.gems,
        message=result.message,
    )


# =============================================================================
# Achievement Endpoints
# =============================================================================

@router.get("/achievements", response_model=List[AchievementResponse])
async def get_all_achievements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all achievement definitions with unlock status."""
    service = GamificationService(db)

    # Get user's unlocked achievements
    unlocked = await service.get_user_achievements(current_user.id)
    unlocked_ids = {ua.achievement_id for ua in unlocked}

    # Get all achievements
    from app.models.gamification import Achievement
    result = await db.execute(
        select(Achievement).where(Achievement.is_hidden == False).order_by(Achievement.category, Achievement.id)
    )
    all_achievements = list(result.scalars().all())

    return [
        AchievementResponse(
            id=a.id,
            key=a.key,
            name=a.name,
            description=a.description,
            category=a.category.value,
            icon=a.icon,
            xp_reward=a.xp_reward,
            gems_reward=a.gems_reward,
            criteria=a.criteria,
            is_hidden=a.is_hidden,
            unlocked=a.id in unlocked_ids,
            unlocked_at=next((ua.unlocked_at for ua in unlocked if ua.achievement_id == a.id), None),
        )
        for a in all_achievements
    ]


@router.get("/achievements/user", response_model=List[UserAchievementResponse])
async def get_user_achievements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's unlocked achievements with details."""
    service = GamificationService(db)
    unlocked = await service.get_user_achievements(current_user.id)

    # Get achievement details for each unlocked achievement
    from app.models.gamification import Achievement
    achievement_ids = [ua.achievement_id for ua in unlocked]
    if achievement_ids:
        result = await db.execute(
            select(Achievement).where(Achievement.id.in_(achievement_ids))
        )
        achievements = {a.id: a for a in result.scalars().all()}
    else:
        achievements = {}

    return [
        UserAchievementResponse(
            id=ua.id,
            achievement_id=ua.achievement_id,
            key=achievements[ua.achievement_id].key if ua.achievement_id in achievements else ua.achievement_id,
            name=achievements[ua.achievement_id].name if ua.achievement_id in achievements else "Unknown",
            description=achievements[ua.achievement_id].description if ua.achievement_id in achievements else "",
            category=achievements[ua.achievement_id].category.value if ua.achievement_id in achievements else "progress",
            icon=achievements[ua.achievement_id].icon if ua.achievement_id in achievements else "award",
            xp_reward=achievements[ua.achievement_id].xp_reward if ua.achievement_id in achievements else 0,
            gems_reward=achievements[ua.achievement_id].gems_reward if ua.achievement_id in achievements else 0,
            unlocked_at=ua.unlocked_at or ua.created_at,
        )
        for ua in unlocked
    ]


@router.post("/achievements/check", response_model=List[AchievementResponse])
async def check_achievements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check and unlock any new achievements."""
    service = GamificationService(db)
    newly_unlocked = await service.check_achievements(current_user.id)

    # Return full achievement details for newly unlocked
    result = []
    for achievement in newly_unlocked:
        result.append(AchievementResponse(
            id=achievement.id,
            key=achievement.key,
            name=achievement.name,
            description=achievement.description,
            category=achievement.category.value,
            icon=achievement.icon,
            xp_reward=achievement.xp_reward,
            gems_reward=achievement.gems_reward,
            criteria=achievement.criteria,
            is_hidden=achievement.is_hidden,
            unlocked=True,
            unlocked_at=datetime.now(timezone.utc),
        ))
    return result


# =============================================================================
# League Endpoints
# =============================================================================

@router.get("/league", response_model=LeagueResponse)
async def get_league(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's league standing."""
    service = GamificationService(db)
    xp = await service.get_or_create_xp(current_user.id)
    return LeagueResponse(
        tier=xp.league_tier.value,
        rank=xp.league_rank,
        weekly_xp=xp.weekly_xp,
        previous_tier=xp.previous_week_tier.value if xp.previous_week_tier else None,
        previous_rank=xp.previous_week_rank,
    )


@router.get("/league/standings", response_model=List[dict])
async def get_league_standings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current week's league standings (top 30)."""
    from app.models.gamification import LeagueStanding
    from datetime import date, timedelta

    # Get current week's Monday
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    result = await db.execute(
        select(LeagueStanding)
        .where(LeagueStanding.week_start == week_start)
        .order_by(LeagueStanding.rank)
        .limit(30)
    )
    standings = list(result.scalars().all())

    return [
        {
            "rank": s.rank,
            "user_id": s.user_id,
            "weekly_xp": s.weekly_xp,
            "promoted": s.promoted,
            "demoted": s.demoted,
        }
        for s in standings
    ]


# =============================================================================
# Friends / Social Endpoints
# =============================================================================

@router.get("/friends", response_model=List[FriendResponse])
async def get_friends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's friends."""
    service = GamificationService(db)
    friends = await service.get_friends(current_user.id)
    return [
        FriendResponse(
            id=f.id,
            friend_id=f.friend.id,
            friend_username=f.friend.username,
            friend_full_name=f.friend.full_name,
            friend_avatar_url=f.friend.avatar_url,
            status=f.status,
            created_at=f.created_at,
            accepted_at=f.accepted_at,
        )
        for f in friends
    ]


@router.post("/friends/add", response_model=FriendResponse)
async def add_friend(
    username: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send friend request."""
    service = GamificationService(db)
    friendship = await service.add_friend(current_user.id, username)
    if not friendship:
        raise HTTPException(status_code=400, detail="User not found or already friends")

    # Load friend details
    from app.models.user import User
    friend_result = await db.execute(select(User).where(User.id == friendship.friend_id))
    friend = friend_result.scalar_one()

    return FriendResponse(
        id=friendship.id,
        friend_id=friend.id,
        friend_username=friend.username,
        friend_full_name=friend.full_name,
        friend_avatar_url=friend.avatar_url,
        status=friendship.status,
        created_at=friendship.created_at,
        accepted_at=friendship.accepted_at,
    )


@router.post("/friends/{friend_id}/accept", response_model=FriendResponse)
async def accept_friend(
    friend_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept friend request."""
    service = GamificationService(db)
    success = await service.accept_friend(current_user.id, friend_id)
    if not success:
        raise HTTPException(status_code=404, detail="Friend request not found")

    # Load friend details
    from app.models.user import User
    friend_result = await db.execute(select(User).where(User.id == friend_id))
    friend = friend_result.scalar_one()

    # Get the friendship record
    from app.models.gamification import UserFriend
    fs_result = await db.execute(
        select(UserFriend).where(
            UserFriend.user_id == friend_id,
            UserFriend.friend_id == current_user.id,
        )
    )
    friendship = fs_result.scalar_one()

    return FriendResponse(
        id=friendship.id,
        friend_id=friend.id,
        friend_username=friend.username,
        friend_full_name=friend.full_name,
        friend_avatar_url=friend.avatar_url,
        status=friendship.status,
        created_at=friendship.created_at,
        accepted_at=friendship.accepted_at,
    )


# =============================================================================
# Gem Endpoints
# =============================================================================

@router.get("/gems", response_model=GemBalanceResponse)
async def get_gem_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's gem balance."""
    service = GamificationService(db)
    balance = await service.get_gem_balance(current_user.id)
    return GemBalanceResponse(gems=balance)


@router.get("/gems/history", response_model=List[GemTransactionResponse])
async def get_gem_history(
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get gem transaction history."""
    service = GamificationService(db)
    transactions = await service.get_gem_history(current_user.id, limit)
    return [
        GemTransactionResponse(
            id=t.id,
            type=t.type,
            amount=t.amount,
            balance_after=t.balance_after,
            description=t.description,
            reference_id=t.reference_id,
            reference_type=t.reference_type,
            created_at=t.created_at,
        )
        for t in transactions
    ]


