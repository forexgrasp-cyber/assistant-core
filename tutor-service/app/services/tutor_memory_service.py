"""
Tutor Memory Service - Persists tutor memory to database and syncs with shared TutorMemory
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tutor_memory import TutorMemory, TutorSessionContext
from app.models.user import User
from shared.agent_runtime.tutor_memory import (
    TutorMemory as SharedTutorMemory,
    LearnerProfile,
    StudyPlan,
    WeekPlan,
    SessionPlan,
    Milestone,
    ContentRec,
)


class TutorMemoryService:
    """Service for managing persistent tutor memory"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_memory(
        self, 
        user_id: int, 
        language: str,
        native_language: str = "en",
    ) -> TutorMemory:
        """Get existing tutor memory or create new one"""
        result = await self.db.execute(
            select(TutorMemory).where(
                TutorMemory.user_id == user_id,
                TutorMemory.language == language,
            )
        )
        memory = result.scalar_one_or_none()
        
        if memory is None:
            memory = TutorMemory(
                user_id=user_id,
                language=language,
                learner_profile={
                    "native_language": native_language,
                    "target_language": language,
                    "cefr_level": "A1",
                    "learning_goals": [],
                    "interests": [],
                    "preferred_topics": [],
                    "weak_areas": [],
                    "strong_areas": [],
                    "learning_style": "balanced",
                    "daily_goal_minutes": 15,
                    "preferred_session_length": 30,
                    "timezone": "UTC",
                },
            )
            self.db.add(memory)
            await self.db.commit()
            await self.db.refresh(memory)
        
        return memory
    
    async def load_shared_memory(
        self, 
        user_id: int, 
        language: str,
    ) -> SharedTutorMemory:
        """Load tutor memory from database into shared TutorMemory object"""
        memory = await self.get_or_create_memory(user_id, language)
        
        # Convert database model to shared TutorMemory
        shared_memory = SharedTutorMemory()
        
        # Load learner profile
        profile_data = memory.learner_profile
        shared_memory.profile = LearnerProfile(
            native_language=profile_data.get("native_language", "en"),
            target_language=profile_data.get("target_language", language),
            cefr_level=profile_data.get("cefr_level", "A1"),
            learning_goals=profile_data.get("learning_goals", []),
            interests=profile_data.get("interests", []),
            preferred_topics=profile_data.get("preferred_topics", []),
            weak_areas=profile_data.get("weak_areas", []),
            strong_areas=profile_data.get("strong_areas", []),
            learning_style=profile_data.get("learning_style", "balanced"),
            daily_goal_minutes=profile_data.get("daily_goal_minutes", 15),
            preferred_session_length=profile_data.get("preferred_session_length", 30),
            timezone=profile_data.get("timezone", "UTC"),
        )
        
        # Load study plan if exists
        if memory.study_plan:
            plan_data = memory.study_plan
            shared_memory.study_plan = StudyPlan(
                target_level=plan_data.get("target_level", "B1"),
                target_date=plan_data.get("target_date"),
                weeks=[
                    WeekPlan(**w) for w in plan_data.get("weeks", [])
                ],
                milestones=[
                    Milestone(**m) for m in plan_data.get("milestones", [])
                ],
                content_recommendations=[
                    ContentRec(**c) for c in plan_data.get("content_recommendations", [])
                ],
                created_at=plan_data.get("created_at"),
                updated_at=plan_data.get("updated_at"),
            )
        
        # Load session history summary
        shared_memory.total_sessions = memory.total_sessions
        shared_memory.total_messages = memory.total_messages
        shared_memory.last_session_at = memory.last_session_at
        
        # Load key memories
        shared_memory.key_memories = memory.key_memories
        
        # Load vocabulary
        shared_memory.vocabulary_mastered = memory.vocabulary_mastered
        shared_memory.vocabulary_struggling = memory.vocabulary_struggling
        
        # Load grammar
        shared_memory.grammar_mastered = memory.grammar_mastered
        shared_memory.grammar_struggling = memory.grammar_struggling
        
        # Load pronunciation
        shared_memory.pronunciation_issues = memory.pronunciation_issues
        shared_memory.pronunciation_improved = memory.pronunciation_improved
        
        # Load writing
        shared_memory.writing_errors = memory.writing_errors
        shared_memory.writing_improvements = memory.writing_improvements
        
        # Load cultural
        shared_memory.cultural_topics_covered = memory.cultural_topics_covered
        
        # Load preferences
        shared_memory.preferences = memory.preferences
        
        return shared_memory
    
    async def save_shared_memory(
        self, 
        user_id: int, 
        language: str,
        shared_memory: SharedTutorMemory,
    ) -> TutorMemory:
        """Save shared TutorMemory to database"""
        memory = await self.get_or_create_memory(user_id, language)
        
        # Update learner profile
        if shared_memory.profile:
            memory.learner_profile = {
                "native_language": shared_memory.profile.native_language,
                "target_language": shared_memory.profile.target_language,
                "cefr_level": shared_memory.profile.cefr_level,
                "learning_goals": shared_memory.profile.learning_goals,
                "interests": shared_memory.profile.interests,
                "preferred_topics": shared_memory.profile.preferred_topics,
                "weak_areas": shared_memory.profile.weak_areas,
                "strong_areas": shared_memory.profile.strong_areas,
                "learning_style": shared_memory.profile.learning_style,
                "daily_goal_minutes": shared_memory.profile.daily_goal_minutes,
                "preferred_session_length": shared_memory.profile.preferred_session_length,
                "timezone": shared_memory.profile.timezone,
            }
        
        # Update study plan
        if shared_memory.study_plan:
            memory.study_plan = {
                "target_level": shared_memory.study_plan.target_level,
                "target_date": shared_memory.study_plan.target_date,
                "weeks": [
                    {
                        "week_number": w.week_number,
                        "focus_areas": w.focus_areas,
                        "lessons_planned": w.lessons_planned,
                        "practice_sessions": w.practice_sessions,
                        "goals": w.goals,
                    }
                    for w in shared_memory.study_plan.weeks
                ],
                "milestones": [
                    {
                        "id": m.id,
                        "description": m.description,
                        "target_date": m.target_date.isoformat() if m.target_date else None,
                        "completed": m.completed,
                        "completed_at": m.completed_at.isoformat() if m.completed_at else None,
                    }
                    for m in shared_memory.study_plan.milestones
                ],
                "content_recommendations": [
                    {
                        "type": c.type,
                        "title": c.title,
                        "description": c.description,
                        "difficulty": c.difficulty,
                        "estimated_time": c.estimated_time,
                        "url": c.url,
                    }
                    for c in shared_memory.study_plan.content_recommendations
                ],
                "created_at": shared_memory.study_plan.created_at.isoformat() if shared_memory.study_plan.created_at else None,
                "updated_at": shared_memory.study_plan.updated_at.isoformat() if shared_memory.study_plan.updated_at else None,
            }
        
        # Update summary stats
        memory.total_sessions = shared_memory.total_sessions
        memory.total_messages = shared_memory.total_messages
        memory.last_session_at = shared_memory.last_session_at
        
        # Update memories
        memory.key_memories = shared_memory.key_memories
        memory.vocabulary_mastered = shared_memory.vocabulary_mastered
        memory.vocabulary_struggling = shared_memory.vocabulary_struggling
        memory.grammar_mastered = shared_memory.grammar_mastered
        memory.grammar_struggling = shared_memory.grammar_struggling
        memory.pronunciation_issues = shared_memory.pronunciation_issues
        memory.pronunciation_improved = shared_memory.pronunciation_improved
        memory.writing_errors = shared_memory.writing_errors
        memory.writing_improvements = shared_memory.writing_improvements
        memory.cultural_topics_covered = shared_memory.cultural_topics_covered
        memory.preferences = shared_memory.preferences
        
        memory.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(memory)
        
        return memory
    
    async def save_session_context(
        self,
        user_id: int,
        language: str,
        session_id: str,
        session_type: str,
        lesson_id: Optional[str],
        context_data: Dict[str, Any],
        summary: Optional[str] = None,
        key_takeaways: Optional[List[str]] = None,
        new_vocabulary: Optional[List[Dict[str, str]]] = None,
        corrections_made: Optional[List[Dict[str, Any]]] = None,
    ) -> TutorSessionContext:
        """Save session context for continuity"""
        context = TutorSessionContext(
            user_id=user_id,
            language=language,
            session_id=session_id,
            session_type=session_type,
            lesson_id=lesson_id,
            context_data=context_data,
            summary=summary,
            key_takeaways=key_takeaways or [],
            new_vocabulary=new_vocabulary or [],
            corrections_made=corrections_made or [],
        )
        
        self.db.add(context)
        await self.db.commit()
        await self.db.refresh(context)
        
        return context
    
    async def end_session_context(
        self,
        session_id: str,
        summary: Optional[str] = None,
        key_takeaways: Optional[List[str]] = None,
        new_vocabulary: Optional[List[Dict[str, str]]] = None,
        corrections_made: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[TutorSessionContext]:
        """End a session context"""
        result = await self.db.execute(
            select(TutorSessionContext).where(
                TutorSessionContext.session_id == session_id
            )
        )
        context = result.scalar_one_or_none()
        
        if context:
            context.ended_at = datetime.utcnow()
            if summary:
                context.summary = summary
            if key_takeaways:
                context.key_takeaways = key_takeaways
            if new_vocabulary:
                context.new_vocabulary = new_vocabulary
            if corrections_made:
                context.corrections_made = corrections_made
            
            await self.db.commit()
            await self.db.refresh(context)
        
        return context
    
    async def get_recent_contexts(
        self,
        user_id: int,
        language: str,
        limit: int = 5,
    ) -> List[TutorSessionContext]:
        """Get recent session contexts for continuity"""
        result = await self.db.execute(
            select(TutorSessionContext)
            .where(
                TutorSessionContext.user_id == user_id,
                TutorSessionContext.language == language,
            )
            .order_by(TutorSessionContext.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def update_learner_profile(
        self,
        user_id: int,
        language: str,
        profile_updates: Dict[str, Any],
    ) -> TutorMemory:
        """Update specific fields in learner profile"""
        memory = await self.get_or_create_memory(user_id, language)
        
        # Merge updates
        memory.learner_profile.update(profile_updates)
        memory.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(memory)
        
        return memory
    
    async def add_key_memory(
        self,
        user_id: int,
        language: str,
        memory_type: str,  # fact, preference, goal, correction
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TutorMemory:
        """Add a key memory about the learner"""
        memory = await self.get_or_create_memory(user_id, language)
        
        key_memory = {
            "type": memory_type,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        
        memory.key_memories.append(key_memory)
        # Keep only last 100 key memories
        if len(memory.key_memories) > 100:
            memory.key_memories = memory.key_memories[-100:]
        
        memory.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(memory)
        
        return memory
    
    async def record_vocabulary_result(
        self,
        user_id: int,
        language: str,
        word: str,
        correct: bool,
    ) -> TutorMemory:
        """Record vocabulary practice result"""
        memory = await self.get_or_create_memory(user_id, language)
        
        if correct:
            if word not in memory.vocabulary_mastered:
                memory.vocabulary_mastered.append(word)
            if word in memory.vocabulary_struggling:
                memory.vocabulary_struggling.remove(word)
        else:
            if word not in memory.vocabulary_struggling:
                memory.vocabulary_struggling.append(word)
            if word in memory.vocabulary_mastered:
                memory.vocabulary_mastered.remove(word)
        
        memory.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(memory)
        
        return memory
    
    async def record_grammar_result(
        self,
        user_id: int,
        language: str,
        pattern: str,
        correct: bool,
    ) -> TutorMemory:
        """Record grammar practice result"""
        memory = await self.get_or_create_memory(user_id, language)
        
        if correct:
            if pattern not in memory.grammar_mastered:
                memory.grammar_mastered.append(pattern)
            if pattern in memory.grammar_struggling:
                memory.grammar_struggling.remove(pattern)
        else:
            if pattern not in memory.grammar_struggling:
                memory.grammar_struggling.append(pattern)
            if pattern in memory.grammar_mastered:
                memory.grammar_mastered.remove(pattern)
        
        memory.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(memory)
        
        return memory
    
    async def record_pronunciation_issue(
        self,
        user_id: int,
        language: str,
        phoneme: str,
        word: str,
        severity: str = "medium",
    ) -> TutorMemory:
        """Record a pronunciation issue"""
        memory = await self.get_or_create_memory(user_id, language)
        
        issue = {
            "phoneme": phoneme,
            "word": word,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
            "count": 1,
        }
        
        # Check if similar issue exists
        for existing in memory.pronunciation_issues:
            if existing["phoneme"] == phoneme and existing["word"] == word:
                existing["count"] += 1
                existing["timestamp"] = datetime.utcnow().isoformat()
                break
        else:
            memory.pronunciation_issues.append(issue)
        
        memory.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(memory)
        
        return memory
    
    async def record_pronunciation_improvement(
        self,
        user_id: int,
        language: str,
        phoneme: str,
    ) -> TutorMemory:
        """Record pronunciation improvement"""
        memory = await self.get_or_create_memory(user_id, language)
        
        if phoneme not in memory.pronunciation_improved:
            memory.pronunciation_improved.append(phoneme)
        
        # Remove from issues if present
        memory.pronunciation_issues = [
            i for i in memory.pronunciation_issues 
            if i["phoneme"] != phoneme
        ]
        
        memory.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(memory)
        
        return memory
    
    async def record_writing_error(
        self,
        user_id: int,
        language: str,
        error_type: str,
        original: str,
        corrected: str,
        rule: Optional[str] = None,
    ) -> TutorMemory:
        """Record a writing error"""
        memory = await self.get_or_create_memory(user_id, language)
        
        error = {
            "error_type": error_type,
            "original": original,
            "corrected": corrected,
            "rule": rule,
            "timestamp": datetime.utcnow().isoformat(),
            "count": 1,
        }
        
        # Check if similar error exists
        for existing in memory.writing_errors:
            if (existing["error_type"] == error_type and 
                existing["original"] == original):
                existing["count"] += 1
                existing["timestamp"] = datetime.utcnow().isoformat()
                break
        else:
            memory.writing_errors.append(error)
        
        memory.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(memory)
        
        return memory
    
    async def record_writing_improvement(
        self,
        user_id: int,
        language: str,
        improvement: str,
    ) -> TutorMemory:
        """Record writing improvement"""
        memory = await self.get_or_create_memory(user_id, language)
        
        if improvement not in memory.writing_improvements:
            memory.writing_improvements.append(improvement)
        
        memory.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(memory)
        
        return memory
    
    async def add_cultural_topic(
        self,
        user_id: int,
        language: str,
        topic: str,
    ) -> TutorMemory:
        """Record a cultural topic covered"""
        memory = await self.get_or_create_memory(user_id, language)
        
        if topic not in memory.cultural_topics_covered:
            memory.cultural_topics_covered.append(topic)
        
        memory.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(memory)
        
        return memory
    
    async def update_preferences(
        self,
        user_id: int,
        language: str,
        preferences: Dict[str, Any],
    ) -> TutorMemory:
        """Update user preferences"""
        memory = await self.get_or_create_memory(user_id, language)
        
        memory.preferences.update(preferences)
        memory.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(memory)
        
        return memory
    
    async def increment_session_stats(
        self,
        user_id: int,
        language: str,
        message_count: int = 1,
    ) -> TutorMemory:
        """Increment session statistics"""
        memory = await self.get_or_create_memory(user_id, language)
        
        memory.total_sessions += 1
        memory.total_messages += message_count
        memory.last_session_at = datetime.utcnow()
        memory.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(memory)
        
        return memory