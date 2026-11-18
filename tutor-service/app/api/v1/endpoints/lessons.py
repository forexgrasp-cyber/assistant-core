"""
Lesson endpoints for Tutor Service
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.lesson import Lesson, LessonContent, VocabularyItem, PronunciationExercise, WritingPrompt
from app.models.user import User, UserProgress, LessonProgress
from app.schemas.lesson import (
    LessonResponse, LessonListItem, LessonCreate, LessonUpdate,
    LessonWithProgress, LessonContentResponse, CurriculumResponse, CurriculumLevelResponse
)
from app.api.v1.endpoints.auth import get_current_active_user

router = APIRouter()


@router.get("/curriculum", response_model=CurriculumResponse)
async def get_curriculum(
    language: str = Query("es", description="Target language"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get full curriculum with progress for a language"""
    # Get user progress
    result = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == current_user.id,
            UserProgress.language == language
        )
    )
    user_progress = result.scalar_one_or_none()
    
    # Get all lessons for language
    result = await db.execute(
        select(Lesson)
        .where(Lesson.language == language, Lesson.is_active == True)
        .order_by(Lesson.level, Lesson.order)
    )
    lessons = result.scalars().all()
    
    # Get lesson progress
    lesson_ids = [l.id for l in lessons]
    result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id.in_(lesson_ids)
        )
    )
    progress_map = {p.lesson_id: p for p in result.scalars().all()}
    
    # Group by level
    from app.models.lesson import CEFRLevel
    levels = list(CEFRLevel)
    level_responses = []
    
    for level in levels:
        level_lessons = [l for l in lessons if l.level == level]
        if not level_lessons:
            continue
        
        completed = sum(1 for l in level_lessons if progress_map.get(l.id) and progress_map[l.id].status in ["completed", "mastered"])
        mastered = sum(1 for l in level_lessons if progress_map.get(l.id) and progress_map[l.id].status == "mastered")
        total_duration = sum(l.duration for l in level_lessons)
        total_xp = sum(l.xp_reward for l in level_lessons)
        
        progress_percent = int((completed / len(level_lessons)) * 100) if level_lessons else 0
        
        level_responses.append(CurriculumLevelResponse(
            level=level,
            label=level.value,
            total_lessons=len(level_lessons),
            completed_lessons=completed,
            mastered_lessons=mastered,
            total_duration=total_duration,
            total_xp=total_xp,
            progress_percent=progress_percent,
        ))
    
    # Determine current level
    current_level = user_progress.current_level if user_progress else CEFRLevel.A1
    
    return CurriculumResponse(
        levels=level_responses,
        total_lessons=len(lessons),
        total_duration=sum(l.duration for l in lessons),
        total_xp=sum(l.xp_reward for l in lessons),
        current_level=current_level,
    )


@router.get("", response_model=List[LessonListItem])
async def list_lessons(
    language: str = Query("es", description="Target language"),
    level: Optional[str] = Query(None, description="CEFR level filter"),
    focus_area: Optional[str] = Query(None, description="Focus area filter"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List lessons with optional filters"""
    query = select(Lesson).where(Lesson.language == language, Lesson.is_active == True)
    
    if level:
        query = query.where(Lesson.level == level)
    if focus_area:
        query = query.where(Lesson.focus_area == focus_area)
    
    query = query.order_by(Lesson.level, Lesson.order)
    
    result = await db.execute(query)
    lessons = result.scalars().all()
    
    # Get progress for these lessons
    lesson_ids = [l.id for l in lessons]
    result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id.in_(lesson_ids)
        )
    )
    progress_map = {p.lesson_id: p for p in result.scalars().all()}
    
    # Build response with progress
    response = []
    for lesson in lessons:
        progress = progress_map.get(lesson.id)
        item = LessonListItem.model_validate(lesson)
        # Add progress info if needed
        response.append(item)
    
    return response


@router.get("/{lesson_id}", response_model=LessonWithProgress)
async def get_lesson(
    lesson_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get lesson with progress"""
    result = await db.execute(
        select(Lesson)
        .options(selectinload(Lesson.content_items))
        .where(Lesson.id == lesson_id)
    )
    lesson = result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Get progress
    result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id == lesson_id
        )
    )
    progress = result.scalar_one_or_none()
    
    # Check if unlocked (prerequisites met)
    is_unlocked = True
    if lesson.prerequisites:
        completed_lessons = set(p.lesson_id for p in progress_map.values() if p.status in ["completed", "mastered"])
        is_unlocked = all(prereq in completed_lessons for prereq in lesson.prerequisites)
    
    response = LessonWithProgress.model_validate(lesson)
    response.progress = progress
    response.is_unlocked = is_unlocked
    
    return response


@router.get("/{lesson_id}/content/{content_id}", response_model=LessonContentResponse)
async def get_lesson_content(
    lesson_id: str,
    content_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific lesson content"""
    result = await db.execute(
        select(LessonContent).where(
            LessonContent.lesson_id == lesson_id,
            LessonContent.content_id == content_id
        )
    )
    content = result.scalar_one_or_none()
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return content


# Admin endpoints
@router.post("", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    lesson_data: LessonCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new lesson (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    lesson = Lesson(**lesson_data.model_dump(exclude={"content"}))
    db.add(lesson)
    await db.flush()
    
    for content_data in lesson_data.content:
        content = LessonContent(lesson_id=lesson.id, **content_data.model_dump())
        db.add(content)
    
    await db.commit()
    await db.refresh(lesson)
    return lesson


@router.put("/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: str,
    lesson_update: LessonUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update lesson (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    update_data = lesson_update.model_dump(exclude_unset=True, exclude={"content"})
    for field, value in update_data.items():
        setattr(lesson, field, value)
    
    if lesson_update.content is not None:
        # Delete existing content and add new
        await db.execute(
            LessonContent.__table__.delete().where(LessonContent.lesson_id == lesson_id)
        )
        for content_data in lesson_update.content:
            content = LessonContent(lesson_id=lesson.id, **content_data.model_dump())
            db.add(content)
    
    await db.commit()
    await db.refresh(lesson)
    return lesson


@router.delete("/{lesson_id}")
async def delete_lesson(
    lesson_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete lesson (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    await db.delete(lesson)
    await db.commit()
    return {"message": "Lesson deleted"}