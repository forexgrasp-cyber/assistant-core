"""
Vocabulary endpoints for Tutor Service
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.lesson import VocabularyItem
from app.models.user import User
from app.schemas.lesson import (
    VocabularyItemResponse, VocabularyItemCreate, VocabularyItemUpdate
)
from app.api.v1.endpoints.auth import get_current_active_user

router = APIRouter()


@router.get("", response_model=List[VocabularyItemResponse])
async def list_vocabulary(
    language: str = Query("es", description="Target language"),
    learned: Optional[bool] = Query(None, description="Filter by learned status"),
    due_for_review: Optional[bool] = Query(None, description="Filter items due for review"),
    search: Optional[str] = Query(None, description="Search in word or translation"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's vocabulary items"""
    query = select(VocabularyItem).where(
        VocabularyItem.user_id == current_user.id,
        VocabularyItem.language == language,
        VocabularyItem.is_archived == False
    )
    
    if learned is not None:
        query = query.where(VocabularyItem.is_learned == learned)
    
    if due_for_review:
        query = query.where(VocabularyItem.next_review <= datetime.utcnow())
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(
            or_(
                VocabularyItem.word.ilike(search_term),
                VocabularyItem.translation.ilike(search_term)
            )
        )
    
    query = query.order_by(VocabularyItem.next_review).offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/due-count")
async def get_due_count(
    language: str = Query("es", description="Target language"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get count of vocabulary items due for review"""
    result = await db.execute(
        select(func.count(VocabularyItem.id)).where(
            VocabularyItem.user_id == current_user.id,
            VocabularyItem.language == language,
            VocabularyItem.is_archived == False,
            VocabularyItem.next_review <= datetime.utcnow()
        )
    )
    count = result.scalar() or 0
    return {"due_count": count}


@router.get("/stats")
async def get_vocabulary_stats(
    language: str = Query("es", description="Target language"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get vocabulary statistics"""
    # Total words
    result = await db.execute(
        select(func.count(VocabularyItem.id)).where(
            VocabularyItem.user_id == current_user.id,
            VocabularyItem.language == language,
            VocabularyItem.is_archived == False
        )
    )
    total = result.scalar() or 0
    
    # Learned
    result = await db.execute(
        select(func.count(VocabularyItem.id)).where(
            VocabularyItem.user_id == current_user.id,
            VocabularyItem.language == language,
            VocabularyItem.is_archived == False,
            VocabularyItem.is_learned == True
        )
    )
    learned = result.scalar() or 0
    
    # Due for review
    result = await db.execute(
        select(func.count(VocabularyItem.id)).where(
            VocabularyItem.user_id == current_user.id,
            VocabularyItem.language == language,
            VocabularyItem.is_archived == False,
            VocabularyItem.next_review <= datetime.utcnow()
        )
    )
    due = result.scalar() or 0
    
    # By difficulty
    result = await db.execute(
        select(VocabularyItem.difficulty, func.count(VocabularyItem.id)).where(
            VocabularyItem.user_id == current_user.id,
            VocabularyItem.language == language,
            VocabularyItem.is_archived == False
        ).group_by(VocabularyItem.difficulty)
    )
    by_difficulty = {diff or "unknown": count for diff, count in result.all()}
    
    return {
        "total": total,
        "learned": learned,
        "learning": total - learned,
        "due_for_review": due,
        "by_difficulty": by_difficulty,
        "mastery_rate": round((learned / total * 100) if total > 0 else 0, 1),
    }


@router.post("", response_model=VocabularyItemResponse, status_code=201)
async def create_vocabulary_item(
    item_data: VocabularyItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Add new vocabulary item"""
    item = VocabularyItem(
        user_id=current_user.id,
        **item_data.model_dump()
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/{item_id}", response_model=VocabularyItemResponse)
async def get_vocabulary_item(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get vocabulary item by ID"""
    result = await db.execute(
        select(VocabularyItem).where(
            VocabularyItem.id == item_id,
            VocabularyItem.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Vocabulary item not found")
    
    return item


@router.put("/{item_id}", response_model=VocabularyItemResponse)
async def update_vocabulary_item(
    item_id: int,
    item_update: VocabularyItemUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update vocabulary item"""
    result = await db.execute(
        select(VocabularyItem).where(
            VocabularyItem.id == item_id,
            VocabularyItem.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Vocabulary item not found")
    
    update_data = item_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    item.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(item)
    return item


@router.post("/{item_id}/review")
async def review_vocabulary_item(
    item_id: int,
    quality: int = Query(..., ge=0, le=5, description="Recall quality (0-5)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Review vocabulary item using SM-2 algorithm"""
    result = await db.execute(
        select(VocabularyItem).where(
            VocabularyItem.id == item_id,
            VocabularyItem.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Vocabulary item not found")
    
    # SM-2 Algorithm
    if quality >= 3:
        if item.repetitions == 0:
            item.interval = 1
        elif item.repetitions == 1:
            item.interval = 6
        else:
            item.interval = round(item.interval * item.ease_factor)
        
        item.repetitions += 1
        item.ease_factor = max(1.3, item.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    else:
        item.repetitions = 0
        item.interval = 1
        item.ease_factor = max(1.3, item.ease_factor - 0.2)
    
    item.next_review = datetime.utcnow() + timedelta(days=item.interval)
    item.last_reviewed = datetime.utcnow()
    
    if item.repetitions >= 5 and item.interval >= 30:
        item.is_learned = True
    
    item.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(item)
    
    return {
        "item": item,
        "next_review_in_days": item.interval,
        "ease_factor": round(item.ease_factor, 2),
    }


@router.delete("/{item_id}")
async def delete_vocabulary_item(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Archive vocabulary item (soft delete)"""
    result = await db.execute(
        select(VocabularyItem).where(
            VocabularyItem.id == item_id,
            VocabularyItem.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Vocabulary item not found")
    
    item.is_archived = True
    item.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Vocabulary item archived"}


@router.post("/bulk-import")
async def bulk_import_vocabulary(
    items: List[VocabularyItemCreate],
    language: str = Query("es", description="Target language"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Bulk import vocabulary items"""
    created = 0
    skipped = 0
    
    for item_data in items:
        # Check if already exists
        result = await db.execute(
            select(VocabularyItem).where(
                VocabularyItem.user_id == current_user.id,
                VocabularyItem.language == language,
                VocabularyItem.word == item_data.word
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            skipped += 1
            continue
        
        item = VocabularyItem(
            user_id=current_user.id,
            language=language,
            **item_data.model_dump()
        )
        db.add(item)
        created += 1
    
    await db.commit()
    return {"created": created, "skipped": skipped}


@router.get("/export")
async def export_vocabulary(
    language: str = Query("es", description="Target language"),
    format: str = Query("json", description="Export format: json, csv"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Export vocabulary"""
    result = await db.execute(
        select(VocabularyItem).where(
            VocabularyItem.user_id == current_user.id,
            VocabularyItem.language == language,
            VocabularyItem.is_archived == False
        ).order_by(VocabularyItem.word)
    )
    items = result.scalars().all()
    
    if format == "csv":
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["word", "translation", "transliteration", "part_of_speech", "difficulty", "example", "tags", "learned", "next_review"])
        for item in items:
            writer.writerow([
                item.word, item.translation, item.transliteration or "",
                item.part_of_speech or "", item.difficulty or "",
                item.example_sentence or "", ",".join(item.tags),
                item.is_learned, item.next_review.isoformat()
            ])
        return {"format": "csv", "data": output.getvalue(), "count": len(items)}
    
    return {
        "format": "json",
        "items": [item.model_dump() for item in items],
        "count": len(items)
    }