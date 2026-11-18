"""
Practice endpoints for Tutor Service
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.core.database import get_db
from app.models.lesson import Lesson, LessonContent, PronunciationExercise, WritingPrompt
from app.models.user import User, PracticeSession, UserProgress
from app.schemas.lesson import (
    ExerciseSubmission, ExerciseResult,
    PronunciationEvaluationRequest, PronunciationEvaluationResponse,
    WritingEvaluationRequest, WritingEvaluationResponse
)
from app.api.v1.endpoints.auth import get_current_active_user

router = APIRouter()


# Practice modes
PRACTICE_MODES = {
    "conversation": {"label": "Free Conversation", "description": "Chat naturally with AI tutor"},
    "pronunciation": {"label": "Pronunciation Drills", "description": "Practice specific sounds"},
    "vocabulary": {"label": "Vocabulary Builder", "description": "Flashcards and recall exercises"},
    "grammar": {"label": "Grammar Practice", "description": "Targeted grammar exercises"},
    "listening": {"label": "Listening Comprehension", "description": "Audio with transcripts"},
    "writing": {"label": "Writing Workshop", "description": "Guided writing with AI evaluation"},
    "roleplay": {"label": "Roleplay Scenarios", "description": "Real-life situations"},
    "shadowing": {"label": "Shadowing Practice", "description": "Repeat after native speakers"},
}


@router.get("/modes")
async def get_practice_modes():
    """Get available practice modes"""
    return {
        "modes": [
            {"id": k, "label": v["label"], "description": v["description"]}
            for k, v in PRACTICE_MODES.items()
        ]
    }


@router.get("/modes/{mode_id}/content")
async def get_practice_content(
    mode_id: str,
    language: str = Query("es", description="Target language"),
    level: Optional[str] = Query(None, description="CEFR level"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get practice content for a specific mode"""
    if mode_id not in PRACTICE_MODES:
        raise HTTPException(status_code=404, detail="Practice mode not found")
    
    # Map mode to content type
    mode_content_map = {
        "pronunciation": PronunciationExercise,
        "writing": WritingPrompt,
        "vocabulary": LessonContent,  # Flashcards
        "grammar": LessonContent,     # Exercises
        "listening": LessonContent,   # Audio
        "roleplay": LessonContent,    # Dialogue
        "shadowing": LessonContent,   # Audio
    }
    
    content_model = mode_content_map.get(mode_id)
    if not content_model:
        raise HTTPException(status_code=404, detail="Content not available for this mode")
    
    query = select(content_model).where(content_model.language == language)
    
    if level and hasattr(content_model, 'level'):
        query = query.where(content_model.level == level)
    
    if hasattr(content_model, 'is_active'):
        query = query.where(content_model.is_active == True)
    
    result = await db.execute(query.limit(50))
    content = result.scalars().all()
    
    return {"mode": mode_id, "content": content}


@router.post("/exercise/submit", response_model=ExerciseResult)
async def submit_exercise(
    submission: ExerciseSubmission,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit exercise answer for evaluation"""
    # Get lesson content
    result = await db.execute(
        select(LessonContent).where(
            LessonContent.lesson_id == submission.lesson_id,
            LessonContent.content_id == submission.content_id
        )
    )
    content = result.scalar_one_or_none()
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    # Evaluate based on content type
    correct = False
    score = 0
    feedback = ""
    corrections = []
    xp_earned = 0
    
    if content.type == "exercise":
        data = content.data
        correct_answer = data.get("correctAnswer")
        user_answer = submission.answer
        
        if isinstance(correct_answer, list):
            correct = set(user_answer) == set(correct_answer) if isinstance(user_answer, list) else False
        else:
            correct = str(user_answer).strip().lower() == str(correct_answer).strip().lower()
        
        score = 100 if correct else 0
        feedback = data.get("explanation", "Correct!" if correct else "Try again.")
        xp_earned = content.xp_reward if correct else 0
    
    elif content.type == "quiz":
        # Similar to exercise but with multiple questions
        correct = True  # Simplified
        score = 85
        feedback = "Good job!"
        xp_earned = content.xp_reward
    
    # Create practice session record
    session = PracticeSession(
        user_id=current_user.id,
        mode="exercise",
        content_id=submission.content_id,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        duration=submission.time_spent,
        score=score,
        xp_earned=xp_earned,
        metadata_json={"lesson_id": submission.lesson_id, "content_type": content.type},
    )
    db.add(session)
    
    # Update user progress
    await _update_user_progress(current_user.id, xp_earned, submission.time_spent, db)
    
    await db.commit()
    
    return ExerciseResult(
        correct=correct,
        score=score,
        feedback=feedback,
        corrections=corrections,
        xp_earned=xp_earned,
        next_content_id=None,
    )


@router.post("/pronunciation/evaluate", response_model=PronunciationEvaluationResponse)
async def evaluate_pronunciation(
    request: PronunciationEvaluationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Evaluate pronunciation from audio"""
    # Get exercise
    result = await db.execute(
        select(PronunciationExercise).where(PronunciationExercise.id == request.exercise_id)
    )
    exercise = result.scalar_one_or_none()
    
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # In production, this would call a pronunciation evaluation service
    # For now, simulate evaluation
    import random
    
    phoneme_scores = []
    for phoneme in exercise.phonemes:
        phoneme_scores.append({
            "phoneme": phoneme.get("symbol", ""),
            "score": random.randint(60, 100),
            "expected": phoneme.get("symbol", ""),
            "actual": phoneme.get("symbol", ""),
        })
    
    overall_score = sum(p["score"] for p in phoneme_scores) / len(phoneme_scores) if phoneme_scores else 70
    fluency_score = random.randint(65, 95)
    intonation_score = random.randint(65, 95)
    
    feedback = _generate_pronunciation_feedback(overall_score, fluency_score, intonation_score)
    xp_earned = exercise.duration * 10 if overall_score >= 70 else 0
    
    # Create practice session
    session = PracticeSession(
        user_id=current_user.id,
        mode="pronunciation",
        content_id=str(exercise.id),
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        duration=60,
        score=overall_score,
        xp_earned=int(xp_earned),
        metadata_json={"exercise_id": exercise.id},
    )
    db.add(session)
    
    await _update_user_progress(current_user.id, int(xp_earned), 60, db)
    await db.commit()
    
    return PronunciationEvaluationResponse(
        overall_score=overall_score,
        phoneme_scores=phoneme_scores,
        fluency_score=fluency_score,
        intonation_score=intonation_score,
        feedback=feedback,
        xp_earned=int(xp_earned),
    )


@router.post("/writing/evaluate", response_model=WritingEvaluationResponse)
async def evaluate_writing(
    request: WritingEvaluationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Evaluate writing submission"""
    # Get prompt
    result = await db.execute(
        select(WritingPrompt).where(WritingPrompt.id == request.prompt_id)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Writing prompt not found")
    
    # In production, this would call a writing evaluation service
    # For now, simulate evaluation
    import random
    
    criteria_scores = {}
    for criterion in prompt.criteria:
        criteria_scores[criterion["name"]] = random.randint(70, 95)
    
    overall_score = sum(criteria_scores.values()) / len(criteria_scores) if criteria_scores else 80
    
    # Generate mock corrections
    corrections = _generate_writing_corrections(request.text)
    feedback = _generate_writing_feedback(overall_score, len(corrections))
    xp_earned = int(prompt.max_words * 0.5) if overall_score >= 70 else 0
    
    session = PracticeSession(
        user_id=current_user.id,
        mode="writing",
        content_id=str(prompt.id),
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        duration=300,
        score=overall_score,
        xp_earned=xp_earned,
        corrections_count=len(corrections),
        metadata_json={"prompt_id": prompt.id, "word_count": len(request.text.split())},
    )
    db.add(session)
    
    await _update_user_progress(current_user.id, xp_earned, 300, db)
    await db.commit()
    
    return WritingEvaluationResponse(
        overall_score=overall_score,
        criteria_scores=criteria_scores,
        corrections=corrections,
        feedback=feedback,
        xp_earned=xp_earned,
    )


async def _update_user_progress(user_id: int, xp: int, time_spent: int, db: AsyncSession):
    """Update user progress after practice"""
    result = await db.execute(
        select(UserProgress).where(UserProgress.user_id == user_id)
    )
    progress = result.scalar_one_or_none()
    
    if progress:
        progress.xp += xp
        progress.total_time_spent += time_spent
        progress.lessons_completed += 1 if xp > 0 else 0
        # Update level progress
        # Simple XP curve: level n requires n^2 * 100 XP
        level = 1
        total_xp = 0
        next_level_xp = 100
        while total_xp + next_level_xp <= progress.xp:
            total_xp += next_level_xp
            level += 1
            next_level_xp = level * level * 100
        progress.level_progress = ((progress.xp - total_xp) / next_level_xp) * 100


def _generate_pronunciation_feedback(overall: float, fluency: float, intonation: float) -> str:
    if overall >= 90:
        return "Excellent pronunciation! Your speech sounds very natural."
    elif overall >= 80:
        return "Great job! Minor improvements on specific sounds will make it perfect."
    elif overall >= 70:
        return "Good effort! Focus on the highlighted phonemes below."
    else:
        return "Keep practicing! Listen carefully to the native speaker and try again."


def _generate_writing_corrections(text: str) -> List[dict]:
    # Mock corrections
    return [
        {
            "original": "I am go to store",
            "corrected": "I am going to the store",
            "type": "grammar",
            "explanation": "Use present continuous for actions happening now",
            "position": {"start": 5, "end": 8},
            "severity": "major"
        }
    ]


def _generate_writing_feedback(score: float, correction_count: int) -> str:
    if score >= 95:
        return "Outstanding writing! Your text is clear, accurate, and well-structured."
    elif score >= 85:
        return "Excellent work! Minor improvements will make it perfect."
    elif score >= 75:
        return "Good effort! Review the corrections below to improve."
    else:
        return "Keep practicing! Focus on the highlighted areas."