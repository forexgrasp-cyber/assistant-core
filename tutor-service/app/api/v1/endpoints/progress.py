"""
Progress endpoints for Tutor Service
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.user import User, UserProgress, LessonProgress, UserAchievement, PracticeSession
from app.models.lesson import Lesson
from app.schemas.user import UserProgressResponse, UserAchievementResponse, PracticeSessionResponse
from app.api.v1.endpoints.auth import get_current_active_user

router = APIRouter()


@router.get("/overview")
async def get_progress_overview(
    language: str = Query("es", description="Target language"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive progress overview"""
    # Get user progress
    result = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == current_user.id,
            UserProgress.language == language
        )
    )
    progress = result.scalar_one_or_none()
    
    if not progress:
        progress = UserProgress(user_id=current_user.id, language=language)
        db.add(progress)
        await db.commit()
        await db.refresh(progress)
    
    # Get lesson stats
    result = await db.execute(
        select(func.count(Lesson.id)).where(Lesson.language == language, Lesson.is_active == True)
    )
    total_lessons = result.scalar() or 0
    
    result = await db.execute(
        select(func.count(LessonProgress.id)).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id.in_(
                select(Lesson.id).where(Lesson.language == language)
            ),
            LessonProgress.status.in_(["completed", "mastered"])
        )
    )
    completed_lessons = result.scalar() or 0
    
    result = await db.execute(
        select(func.count(LessonProgress.id)).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id.in_(
                select(Lesson.id).where(Lesson.language == language)
            ),
            LessonProgress.status == "mastered"
        )
    )
    mastered_lessons = result.scalar() or 0
    
    # Get recent activity (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    result = await db.execute(
        select(PracticeSession).where(
            PracticeSession.user_id == current_user.id,
            PracticeSession.started_at >= week_ago
        ).order_by(desc(PracticeSession.started_at))
    )
    recent_sessions = result.scalars().all()
    
    # Weekly stats
    weekly_minutes = sum(s.duration for s in recent_sessions) // 60
    weekly_xp = sum(s.xp_earned for s in recent_sessions)
    weekly_lessons = len([s for s in recent_sessions if s.xp_earned > 0])
    
    # Streak calculation
    current_streak = progress.streak
    longest_streak = progress.longest_streak
    
    return {
        "user_progress": progress,
        "stats": {
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "mastered_lessons": mastered_lessons,
            "completion_rate": round((completed_lessons / total_lessons * 100) if total_lessons > 0 else 0, 1),
            "current_level": progress.current_level,
            "level_progress": round(progress.level_progress, 1),
            "total_xp": progress.xp,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_time_hours": round(progress.total_time_spent / 3600, 1),
        },
        "weekly": {
            "minutes": weekly_minutes,
            "xp": weekly_xp,
            "lessons": weekly_lessons,
            "sessions": len(recent_sessions),
        },
        "focus_areas": progress.focus_area_progress,
        "weak_areas": progress.weak_areas,
        "strong_areas": progress.strong_areas,
    }


@router.get("/skills")
async def get_skill_breakdown(
    language: str = Query("es", description="Target language"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed skill breakdown"""
    result = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == current_user.id,
            UserProgress.language == language
        )
    )
    progress = result.scalar_one_or_none()
    
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    
    focus_areas = [
        "conversation", "grammar", "vocabulary", "pronunciation",
        "writing", "reading", "listening", "culture"
    ]
    
    skills = []
    for area in focus_areas:
        area_progress = progress.focus_area_progress.get(area, 0)
        skills.append({
            "area": area,
            "label": area.capitalize(),
            "progress": area_progress,
            "is_weak": area in progress.weak_areas,
            "is_strong": area in progress.strong_areas,
        })
    
    return {
        "skills": skills,
        "overall_level": progress.current_level,
        "level_progress": progress.level_progress,
    }


@router.get("/activity")
async def get_activity(
    language: str = Query("es", description="Target language"),
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get activity data for heatmap/chart"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(PracticeSession).where(
            PracticeSession.user_id == current_user.id,
            PracticeSession.started_at >= start_date
        ).order_by(PracticeSession.started_at)
    )
    sessions = result.scalars().all()
    
    # Group by date
    daily_data = {}
    for session in sessions:
        date_key = session.started_at.date().isoformat()
        if date_key not in daily_data:
            daily_data[date_key] = {"minutes": 0, "xp": 0, "sessions": 0}
        daily_data[date_key]["minutes"] += session.duration // 60
        daily_data[date_key]["xp"] += session.xp_earned
        daily_data[date_key]["sessions"] += 1
    
    # Fill missing days with zeros
    activity = []
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=i)).date().isoformat()
        data = daily_data.get(date, {"minutes": 0, "xp": 0, "sessions": 0})
        activity.append({
            "date": date,
            "minutes": data["minutes"],
            "xp": data["xp"],
            "sessions": data["sessions"],
        })
    
    activity.reverse()  # Chronological order
    
    return {
        "activity": activity,
        "summary": {
            "total_days": days,
            "active_days": len([d for d in daily_data.values() if d["minutes"] > 0]),
            "total_minutes": sum(d["minutes"] for d in daily_data.values()),
            "total_xp": sum(d["xp"] for d in daily_data.values()),
            "average_minutes": round(sum(d["minutes"] for d in daily_data.values()) / max(len(daily_data), 1), 1),
        }
    }


@router.get("/achievements", response_model=List[UserAchievementResponse])
async def get_achievements(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all user achievements"""
    result = await db.execute(
        select(UserAchievement).where(UserAchievement.user_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/leaderboard")
async def get_leaderboard(
    language: str = Query("es", description="Target language"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get leaderboard for language"""
    # Get top users by XP for this language
    result = await db.execute(
        select(UserProgress, User)
        .join(User, UserProgress.user_id == User.id)
        .where(UserProgress.language == language, User.is_active == True)
        .order_by(desc(UserProgress.xp))
        .limit(limit)
    )
    leaderboard = []
    for i, (progress, user) in enumerate(result.all()):
        leaderboard.append({
            "rank": i + 1,
            "user_id": user.id,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "level": progress.current_level,
            "xp": progress.xp,
            "streak": progress.streak,
        })
    
    # Check if current user is in leaderboard
    user_rank = None
    for entry in leaderboard:
        if entry["user_id"] == current_user.id:
            user_rank = entry["rank"]
            break
    
    if not user_rank and current_user.id not in [e["user_id"] for e in leaderboard]:
        # Get user's rank
        result = await db.execute(
            select(func.count(UserProgress.id)).where(
                UserProgress.language == language,
                UserProgress.xp > current_user.xp
            )
        )
        higher = result.scalar() or 0
        user_rank = higher + 1
    
    return {
        "leaderboard": leaderboard,
        "user_rank": user_rank,
        "total_users": len(leaderboard),
    }


@router.get("/report")
async def generate_progress_report(
    language: str = Query("es", description="Target language"),
    period: str = Query("month", description="Period: week, month, quarter, year, all"),
    format: str = Query("json", description="Format: json, pdf, html"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate progress report"""
    # Calculate date range
    now = datetime.utcnow()
    if period == "week":
        start_date = now - timedelta(weeks=1)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "quarter":
        start_date = now - timedelta(days=90)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:
        start_date = datetime(2020, 1, 1)  # All time
    
    # Get progress
    result = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == current_user.id,
            UserProgress.language == language
        )
    )
    progress = result.scalar_one_or_none()
    
    # Get sessions in period
    result = await db.execute(
        select(PracticeSession).where(
            PracticeSession.user_id == current_user.id,
            PracticeSession.started_at >= start_date
        ).order_by(desc(PracticeSession.started_at))
    )
    sessions = result.scalars().all()
    
    # Get lesson completions
    result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.last_accessed >= start_date,
            LessonProgress.status.in_(["completed", "mastered"])
        ).order_by(desc(LessonProgress.last_accessed))
    )
    completed_lessons = result.scalars().all()
    
    report = {
        "user": {
            "name": current_user.name,
            "email": current_user.email,
            "native_language": current_user.native_language,
            "target_language": language,
        },
        "period": period,
        "generated_at": now.isoformat(),
        "summary": {
            "current_level": progress.current_level if progress else "A1",
            "total_xp": progress.xp if progress else 0,
            "streak": progress.streak if progress else 0,
            "total_time_hours": round(progress.total_time_spent / 3600, 1) if progress else 0,
        },
        "period_stats": {
            "sessions": len(sessions),
            "minutes": sum(s.duration for s in sessions) // 60,
            "xp_earned": sum(s.xp_earned for s in sessions),
            "lessons_completed": len(completed_lessons),
            "lessons_mastered": len([l for l in completed_lessons if l.status == "mastered"]),
        },
        "focus_areas": progress.focus_area_progress if progress else {},
        "achievements_unlocked": 0,  # Would query achievements
        "sessions_detail": [
            {
                "date": s.started_at.isoformat(),
                "mode": s.mode,
                "duration": s.duration,
                "score": s.score,
                "xp": s.xp_earned,
            }
            for s in sessions[:50]  # Limit to 50
        ],
        "lessons_detail": [
            {
                "lesson_id": l.lesson_id,
                "status": l.status,
                "score": l.score,
                "completed_at": l.last_accessed.isoformat(),
            }
            for l in completed_lessons
        ],
    }
    
    return report