"""
User endpoints for Tutor Service
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.user import User, UserProgress, LessonProgress, UserAchievement, PracticeSession
from app.schemas.user import (
    UserResponse, UserUpdate, UserProgressResponse, UserProgressUpdate,
    LessonProgressResponse, LessonProgressUpdate, UserAchievementResponse,
    PracticeSessionResponse, UserSettingsResponse, UserSettingsUpdate,
    UserWithProgress
)
from app.api.v1.endpoints.auth import get_current_active_user

router = APIRouter()


@router.get("/me/progress", response_model=UserProgressResponse)
async def get_my_progress(
    language: str = Query("es", description="Target language"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's progress for a language"""
    result = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == current_user.id,
            UserProgress.language == language
        )
    )
    progress = result.scalar_one_or_none()
    
    if not progress:
        # Create default progress
        progress = UserProgress(
            user_id=current_user.id,
            language=language,
        )
        db.add(progress)
        await db.commit()
        await db.refresh(progress)
    
    return progress


@router.put("/me/progress", response_model=UserProgressResponse)
async def update_my_progress(
    progress_update: UserProgressUpdate,
    language: str = Query("es", description="Target language"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's progress"""
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
    
    update_data = progress_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(progress, field, value)
    
    await db.commit()
    await db.refresh(progress)
    return progress


@router.get("/me/lessons/{lesson_id}/progress", response_model=LessonProgressResponse)
async def get_lesson_progress(
    lesson_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get progress for a specific lesson"""
    result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id == lesson_id
        )
    )
    progress = result.scalar_one_or_none()
    
    if not progress:
        # Return default progress
        return LessonProgressResponse(
            id=0,
            user_id=current_user.id,
            lesson_id=lesson_id,
            status="not_started",
            current_content_index=0,
            completed_content=[],
            score=None,
            mastery_level=0,
            attempts=0,
            time_spent=0,
            last_accessed=datetime.utcnow(),
        )
    
    return progress


@router.put("/me/lessons/{lesson_id}/progress", response_model=LessonProgressResponse)
async def update_lesson_progress(
    lesson_id: str,
    progress_update: LessonProgressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update lesson progress"""
    result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id == lesson_id
        )
    )
    progress = result.scalar_one_or_none()
    
    if not progress:
        progress = LessonProgress(user_id=current_user.id, lesson_id=lesson_id)
        db.add(progress)
    
    update_data = progress_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(progress, field, value)
    
    progress.last_accessed = datetime.utcnow()
    await db.commit()
    await db.refresh(progress)
    return progress


@router.get("/me/achievements", response_model=List[UserAchievementResponse])
async def get_my_achievements(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all achievements for current user"""
    result = await db.execute(
        select(UserAchievement).where(UserAchievement.user_id == current_user.id)
    )
    achievements = result.scalars().all()
    return achievements


@router.get("/me/practice-sessions", response_model=List[PracticeSessionResponse])
async def get_practice_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get practice session history"""
    result = await db.execute(
        select(PracticeSession)
        .where(PracticeSession.user_id == current_user.id)
        .order_by(PracticeSession.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    sessions = result.scalars().all()
    return sessions


@router.get("/me/settings", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_active_user)
):
    """Get user settings"""
    return UserSettingsResponse(
        daily_goal_minutes=current_user.daily_goal_minutes,
        auto_play_audio=current_user.auto_play_audio,
        show_translations=current_user.show_translations,
        enable_haptics=current_user.enable_haptics,
        playback_speed=current_user.playback_speed,
        native_language=current_user.native_language,
        target_language=current_user.target_language,
        cefr_level=current_user.cefr_level,
    )


@router.put("/me/settings", response_model=UserSettingsResponse)
async def update_settings(
    settings_update: UserSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user settings"""
    update_data = settings_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(current_user)
    
    return UserSettingsResponse(
        daily_goal_minutes=current_user.daily_goal_minutes,
        auto_play_audio=current_user.auto_play_audio,
        show_translations=current_user.show_translations,
        enable_haptics=current_user.enable_haptics,
        playback_speed=current_user.playback_speed,
        native_language=current_user.native_language,
        target_language=current_user.target_language,
        cefr_level=current_user.cefr_level,
    )


# Admin endpoints
@router.get("", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List users (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return users


@router.get("/{user_id}", response_model=UserWithProgress)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID (admin or self)"""
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.progress),
            selectinload(User.lesson_progress),
            selectinload(User.achievements),
        )
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user