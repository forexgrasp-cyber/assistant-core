"""
Lesson Generation Service - Multi-source content pipeline for stunning, adaptive lessons
Supports: LLM generation (via unified TutorLLMService), YouTube, textbooks, APIs, multimedia content
"""
from __future__ import annotations

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
import structlog
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.lesson import (
    Lesson, LessonContent, ContentType, FocusArea, CEFRLevel, ExerciseType
)
from app.models.tutor_memory import TutorMemory
from shared.agent_runtime.tutor_memory import (
    LearnerProfile, StudyPlan, Milestone, WeekPlan, SessionPlan, ContentRec
)
from app.schemas.lesson import LessonCreate, LessonContentCreate
from shared.ai_assistant.persona import VERTICAL_PROMPTS, SUPPORTED_LANGUAGES
from app.services.tutor_llm_service import get_tutor_llm_service, LLMTaskType

log = structlog.get_logger(__name__)

TUTOR_SYSTEM_PROMPT = VERTICAL_PROMPTS.get("language-tutor", "")


class AgeGroup(str, Enum):
    CHILD = "child"           # 5-12 years
    TEEN = "teen"             # 13-17 years
    YOUNG_ADULT = "young_adult"  # 18-25 years
    ADULT = "adult"           # 26-55 years
    SENIOR = "senior"         # 55+ years


class ContentSource(str, Enum):
    LLM_GENERATED = "llm_generated"
    YOUTUBE = "youtube"
    TEXTBOOK = "textbook"
    API_CURRICULUM = "api_curriculum"
    USER_CREATED = "user_created"
    COMMUNITY = "community"
    AI_CURATED = "ai_curated"


class GamificationLevel(str, Enum):
    NONE = "none"
    LIGHT = "light"           # Progress bars, XP
    MEDIUM = "medium"         # Badges, streaks, leaderboards
    FULL = "full"             # Quests, avatar, virtual world, AR


@dataclass
class ContentAsset:
    """Represents a piece of multimedia content"""
    id: str
    type: ContentType
    source: ContentSource
    title: str
    description: str
    url: Optional[str] = None
    local_path: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    duration_seconds: int = 0
    difficulty: float = 0.5  # 0-1
    age_appropriate: list[AgeGroup] = field(default_factory=list)
    language: str = "en"
    tags: list[str] = field(default_factory=list)
    license: str = "unknown"
    attribution: str = ""


@dataclass
class LessonBlueprint:
    """Blueprint for generating a complete lesson"""
    id: str
    title: str
    description: str
    language: str
    level: CEFRLevel
    focus_area: FocusArea
    target_age_groups: list[AgeGroup]
    gamification_level: GamificationLevel
    duration_minutes: int
    xp_reward: int
    prerequisites: list[str] = field(default_factory=list)
    learning_objectives: list[str] = field(default_factory=list)
    content_assets: list[ContentAsset] = field(default_factory=list)
    vocabulary_targets: list[str] = field(default_factory=list)
    grammar_points: list[str] = field(default_factory=list)
    pronunciation_focus: list[str] = field(default_factory=list)
    cultural_notes: list[str] = field(default_factory=list)
    assessment_criteria: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


class ContentSourceAdapter(ABC):
    """Abstract base for content source adapters"""
    
    @abstractmethod
    async def search(self, query: ContentSearchQuery) -> list[ContentAsset]:
        pass
    
    @abstractmethod
    async def fetch(self, asset_id: str) -> ContentAsset:
        pass
    
    @abstractmethod
    def get_source_type(self) -> ContentSource:
        pass


@dataclass
class ContentSearchQuery:
    language: str
    level: CEFRLevel
    focus_area: FocusArea
    topic: str
    age_groups: list[AgeGroup]
    max_duration_minutes: int = 30
    max_results: int = 10
    gamification_level: GamificationLevel = GamificationLevel.MEDIUM
    content_types: list[ContentType] = field(default_factory=list)


class YouTubeAdapter(ContentSourceAdapter):
    """Search and fetch educational YouTube content"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.YOUTUBE_API_KEY
        self.base_url = "https://www.googleapis.com/youtube/v3"
    
    def get_source_type(self) -> ContentSource:
        return ContentSource.YOUTUBE
    
    async def search(self, query: ContentSearchQuery) -> list[ContentAsset]:
        if not self.api_key:
            return []
        
        search_query = f"{query.topic} {query.language} {query.level.value} lesson"
        if AgeGroup.CHILD in query.age_groups:
            search_query += " kids children"
        
        params = {
            "part": "snippet",
            "q": search_query,
            "type": "video",
            "videoDuration": "short" if query.max_duration_minutes < 20 else "medium",
            "videoEmbeddable": "true",
            "videoSyndicated": "true",
            "maxResults": query.max_results,
            "key": self.api_key,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()
            data = response.json()
        
        assets = []
        for item in data.get("items", []):
            video_id = item["id"]["videoId"]
            snippet = item["snippet"]
            
            asset = ContentAsset(
                id=f"yt_{video_id}",
                type=ContentType.VIDEO,
                source=ContentSource.YOUTUBE,
                title=snippet["title"],
                description=snippet["description"][:500],
                url=f"https://www.youtube.com/watch?v={video_id}",
                metadata={
                    "channel": snippet["channelTitle"],
                    "published_at": snippet["publishedAt"],
                    "thumbnails": snippet["thumbnails"],
                    "video_id": video_id,
                },
                duration_seconds=0,  # Would need separate API call
                language=query.language,
                tags=[query.topic, query.level.value, query.focus_area.value],
                age_appropriate=query.age_groups,
            )
            assets.append(asset)
        
        return assets
    
    async def fetch(self, asset_id: str) -> ContentAsset:
        video_id = asset_id.replace("yt_", "")
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": video_id,
            "key": self.api_key,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/videos", params=params)
            response.raise_for_status()
            data = response.json()
        
        if not data.get("items"):
            raise ValueError(f"Video {video_id} not found")
        
        item = data["items"][0]
        snippet = item["snippet"]
        content_details = item["contentDetails"]
        
        # Parse ISO 8601 duration
        import isodate
        duration = isodate.parse_duration(content_details["duration"])
        duration_seconds = int(duration.total_seconds())
        
        return ContentAsset(
            id=asset_id,
            type=ContentType.VIDEO,
            source=ContentSource.YOUTUBE,
            title=snippet["title"],
            description=snippet["description"],
            url=f"https://www.youtube.com/watch?v={video_id}",
            metadata={
                "channel": snippet["channelTitle"],
                "published_at": snippet["publishedAt"],
                "view_count": item["statistics"].get("viewCount", 0),
                "like_count": item["statistics"].get("likeCount", 0),
            },
            duration_seconds=duration_seconds,
            language=snippet.get("defaultAudioLanguage", "en")[:2],
        )


class TextbookAdapter(ContentSourceAdapter):
    """Parse and extract content from textbook PDFs/EPUBs"""
    
    def __init__(self, textbook_dir: str = "./data/textbooks"):
        self.textbook_dir = Path(textbook_dir)
        self.textbook_dir.mkdir(parents=True, exist_ok=True)
    
    def get_source_type(self) -> ContentSource:
        return ContentSource.TEXTBOOK
    
    async def search(self, query: ContentSearchQuery) -> list[ContentAsset]:
        # Scan local textbooks for relevant content
        assets = []
        
        for textbook_file in self.textbook_dir.glob("*.json"):  # Pre-parsed JSON index
            try:
                with open(textbook_file) as f:
                    textbook = json.load(f)
                
                if textbook.get("language") != query.language:
                    continue
                
                for chapter in textbook.get("chapters", []):
                    if query.topic.lower() in chapter.get("title", "").lower():
                        assets.append(ContentAsset(
                            id=f"tb_{textbook_file.stem}_{chapter['id']}",
                            type=ContentType.TEXT,
                            source=ContentSource.TEXTBOOK,
                            title=chapter["title"],
                            description=chapter.get("summary", ""),
                            local_path=str(textbook_file),
                            metadata={
                                "textbook": textbook["title"],
                                "chapter": chapter["id"],
                                "pages": chapter.get("pages", []),
                                "exercises": chapter.get("exercises", []),
                            },
                            duration_seconds=chapter.get("estimated_minutes", 10) * 60,
                            language=query.language,
                            tags=[query.topic, query.level.value],
                            age_appropriate=query.age_groups,
                        ))
            except Exception:
                continue
        
        return assets[:query.max_results]
    
    async def fetch(self, asset_id: str) -> ContentAsset:
        # Parse asset_id: tb_{textbook}_{chapter}
        parts = asset_id.split("_", 2)
        if len(parts) < 3:
            raise ValueError(f"Invalid textbook asset ID: {asset_id}")
        
        textbook_name = parts[1]
        chapter_id = parts[2]
        
        textbook_file = self.textbook_dir / f"{textbook_name}.json"
        with open(textbook_file) as f:
            textbook = json.load(f)
        
        chapter = next((c for c in textbook["chapters"] if c["id"] == chapter_id), None)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        
        return ContentAsset(
            id=asset_id,
            type=ContentType.TEXT,
            source=ContentSource.TEXTBOOK,
            title=chapter["title"],
            description=chapter.get("summary", ""),
            local_path=str(textbook_file),
            metadata={
                "textbook": textbook["title"],
                "chapter": chapter_id,
                "full_content": chapter.get("content", ""),
                "exercises": chapter.get("exercises", []),
                "vocabulary": chapter.get("vocabulary", []),
                "grammar": chapter.get("grammar", []),
            },
            duration_seconds=chapter.get("estimated_minutes", 10) * 60,
            language=textbook.get("language", "en"),
        )


class LLMSourceAdapter(ContentSourceAdapter):
    """Generate lesson content using unified TutorLLMService with BYOK support"""
    
    def __init__(self):
        self.llm_service = get_tutor_llm_service()
    
    def get_source_type(self) -> ContentSource:
        return ContentSource.LLM_GENERATED
    
    async def generate_lesson_blueprint(
        self,
        learner_profile: LearnerProfile,
        study_plan: StudyPlan,
        target_focus: FocusArea,
        age_group: AgeGroup,
        gamification: GamificationLevel,
        user_id: int = 0,
    ) -> LessonBlueprint:
        """Generate a complete lesson blueprint tailored to the learner using unified LLM service"""
        
        # Build context from learner's gaps (using shared LearnerProfile fields)
        vocab_gaps = list(learner_profile.learning_vocabulary)[:10]
        grammar_gaps = list(learner_profile.error_patterns.keys())[:5]
        pronunciation_gaps = []  # Not tracked in shared profile yet
        
        # Map FocusArea to LLMTaskType
        task_type_map = {
            FocusArea.CONVERSATION: LLMTaskType.LESSON_GENERATION,
            FocusArea.GRAMMAR: LLMTaskType.GRAMMAR_EXPLANATION,
            FocusArea.VOCABULARY: LLMTaskType.VOCABULARY_EXPANSION,
            FocusArea.PRONUNCIATION: LLMTaskType.PRONUNCIATION_GUIDANCE,
            FocusArea.READING: LLMTaskType.CONTENT_CREATION,
            FocusArea.LISTENING: LLMTaskType.CONTENT_CREATION,
            FocusArea.WRITING: LLMTaskType.WRITING_CORRECTION,
            FocusArea.CULTURE: LLMTaskType.CULTURAL_CONTEXT,
        }
        task_type = task_type_map.get(target_focus, LLMTaskType.LESSON_GENERATION)
        
        # Build prompt
        prompt = self._build_prompt(learner_profile, study_plan, target_focus, age_group, gamification, vocab_gaps, grammar_gaps, pronunciation_gaps)
        
        # Try LLM via unified service (uses user's BYOK keys or service keys)
        try:
            result = await self.llm_service.call_json(
                user_id=user_id,
                prompt=prompt,
                task_type=task_type,
            )
            
            if result["success"] and result["data"]:
                # Parse the JSON response into LessonBlueprint
                data = result["data"]
                if isinstance(data, str):
                    data = json.loads(data)
                
                return LessonBlueprint(**data)
        except Exception as e:
            log.warning("llm_generation_failed_using_fallback", error=str(e))
        
        # Fallback: Generate template-based lesson without LLM
        return self._generate_fallback_blueprint(
            learner_profile, study_plan, target_focus, age_group, gamification, vocab_gaps, grammar_gaps
        )
    
    def _build_prompt(self, learner_profile, study_plan, target_focus, age_group, gamification, vocab_gaps, grammar_gaps, pronunciation_gaps) -> str:
        return f"""
{TUTOR_SYSTEM_PROMPT}

Generate a complete lesson blueprint for a {learner_profile.target_language} learner.

LEARNER PROFILE:
- Native language: {learner_profile.native_language}
- Target language: {learner_profile.target_language}
- CEFR Level: {learner_profile.cefr_level}
- Age group: {age_group.value}
- Primary goal: {learner_profile.primary_goal}
- Focus areas: {', '.join(learner_profile.focus_areas)}
- Interests: {', '.join(learner_profile.interests)}
- Daily goal: {learner_profile.time_per_day_minutes} minutes

CURRENT GAPS:
- Vocabulary to reinforce: {', '.join(vocab_gaps) if vocab_gaps else 'None identified'}
- Grammar to practice: {', '.join(grammar_gaps) if grammar_gaps else 'None identified'}
- Pronunciation to improve: {', '.join(pronunciation_gaps) if pronunciation_gaps else 'None identified'}

REQUIREMENTS:
- Focus area: {target_focus.value}
- Gamification level: {gamification.value}
- Duration: ~{learner_profile.time_per_day_minutes} minutes
- Must be engaging, age-appropriate for {age_group.value}
- Include multimedia elements (video, audio, interactive)
- Cultural context for {learner_profile.target_language}

Return as JSON with this structure:
{{
    "id": "unique_id",
    "title": "Engaging lesson title",
    "description": "Brief description",
    "language": "{learner_profile.target_language}",
    "level": "{learner_profile.cefr_level}",
    "focus_area": "{target_focus.value}",
    "target_age_groups": ["{age_group.value}"],
    "gamification_level": "{gamification.value}",
    "duration_minutes": {learner_profile.time_per_day_minutes},
    "xp_reward": 100,
    "learning_objectives": ["objective1", "objective2"],
    "vocabulary_targets": ["word1", "word2"],
    "grammar_points": ["point1", "point2"],
    "pronunciation_focus": ["sound1", "sound2"],
    "cultural_notes": ["note1", "note2"],
    "content_assets": [
        {{
            "type": "dialogue|exercise|video|audio|flashcard|quiz|pronunciation|writing|reading",
            "title": "Asset title",
            "description": "What this asset covers",
            "estimated_minutes": 5,
            "data": {{}},
            "xp_reward": 20
        }}
    ],
    "assessment_criteria": {{}}
}}
"""
    
    def _generate_fallback_blueprint(
        self,
        learner_profile: LearnerProfile,
        study_plan: StudyPlan,
        target_focus: FocusArea,
        age_group: AgeGroup,
        gamification: GamificationLevel,
        vocab_gaps: list,
        grammar_gaps: list,
    ) -> LessonBlueprint:
        """Generate a lesson blueprint without LLM (template-based)"""
        
        import uuid
        
        # Age-appropriate content templates
        age_templates = {
            AgeGroup.CHILD: {
                "tone": "playful and encouraging",
                "examples": ["games", "songs", "stories", "cartoon characters"],
                "duration_factor": 0.7,
            },
            AgeGroup.TEEN: {
                "tone": "relatable and cool",
                "examples": ["social media", "music", "gaming", "friends"],
                "duration_factor": 1.0,
            },
            AgeGroup.YOUNG_ADULT: {
                "tone": "practical and engaging",
                "examples": ["travel", "career", "dating", "university"],
                "duration_factor": 1.0,
            },
            AgeGroup.ADULT: {
                "tone": "professional and practical",
                "examples": ["work", "travel", "business", "daily life"],
                "duration_factor": 1.0,
            },
            AgeGroup.SENIOR: {
                "tone": "patient and clear",
                "examples": ["travel", "family", "hobbies", "health"],
                "duration_factor": 1.2,
            },
        }
        
        template = age_templates.get(age_group, age_templates[AgeGroup.ADULT])
        duration = int(learner_profile.time_per_day_minutes * template["duration_factor"])
        
        # Focus-specific templates
        focus_templates = {
            FocusArea.CONVERSATION: {
                "title": f"Real-Life Conversations: {target_focus.value.title()}",
                "objectives": [
                    f"Master essential {target_focus.value} phrases",
                    f"Practice natural dialogue flow",
                    f"Build confidence in speaking",
                ],
                "vocab": ["hello", "goodbye", "please", "thank you", "excuse me", "how are you"],
                "grammar": ["present tense", "question formation"],
                "pronunciation": ["vowel sounds", "intonation"],
                "cultural": ["greeting customs", "personal space"],
                "assets": [
                    {"type": ContentType.DIALOGUE, "title": "Meeting New People", "minutes": 5},
                    {"type": ContentType.EXERCISE, "title": "Role-Play Practice", "minutes": 5},
                    {"type": ContentType.PRONUNCIATION, "title": "Key Sounds", "minutes": 5},
                    {"type": ContentType.FLASHCARD, "title": "Essential Phrases", "minutes": 5},
                ],
            },
            FocusArea.GRAMMAR: {
                "title": f"Grammar Foundations: {target_focus.value.title()}",
                "objectives": [
                    f"Understand {target_focus.value} rules",
                    f"Apply patterns in sentences",
                    f"Recognize common errors",
                ],
                "vocab": ["verb", "noun", "adjective", "tense", "subject", "object"],
                "grammar": ["present tense", "sentence structure"],
                "pronunciation": [],
                "cultural": [],
                "assets": [
                    {"type": ContentType.EXERCISE, "title": "Pattern Recognition", "minutes": 7},
                    {"type": ContentType.EXERCISE, "title": "Fill in the Blanks", "minutes": 5},
                    {"type": ContentType.QUIZ, "title": "Grammar Check", "minutes": 5},
                ],
            },
            FocusArea.VOCABULARY: {
                "title": f"Vocabulary Builder: {target_focus.value.title()}",
                "objectives": [
                    f"Learn 20+ new {target_focus.value} words",
                    f"Practice with spaced repetition",
                    f"Use words in context",
                ],
                "vocab": ["common", "useful", "essential", "everyday", "important", "frequent"],
                "grammar": [],
                "pronunciation": ["word stress"],
                "cultural": ["idioms", "expressions"],
                "assets": [
                    {"type": ContentType.FLASHCARD, "title": "New Words", "minutes": 5},
                    {"type": ContentType.EXERCISE, "title": "Match & Learn", "minutes": 5},
                    {"type": ContentType.EXERCISE, "title": "Vocabulary Race", "minutes": 5},
                    {"type": ContentType.READING, "title": "Words in Context", "minutes": 5},
                ],
            },
            FocusArea.PRONUNCIATION: {
                "title": f"Perfect Pronunciation: {target_focus.value.title()}",
                "objectives": [
                    f"Master difficult {target_focus.value} sounds",
                    f"Improve rhythm and intonation",
                    f"Sound more natural",
                ],
                "vocab": [],
                "grammar": [],
                "pronunciation": ["vowels", "consonants", "stress", "intonation"],
                "cultural": [],
                "assets": [
                    {"type": ContentType.PRONUNCIATION, "title": "Sound Drills", "minutes": 7},
                    {"type": ContentType.AUDIO, "title": "Listen & Repeat", "minutes": 5},
                    {"type": ContentType.EXERCISE, "title": "Minimal Pairs", "minutes": 5},
                ],
            },
            FocusArea.READING: {
                "title": f"Reading Practice: {target_focus.value.title()}",
                "objectives": [
                    f"Improve reading comprehension",
                    f"Expand vocabulary through context",
                    f"Enjoy {target_focus.value} texts",
                ],
                "vocab": ["story", "article", "text", "paragraph", "sentence"],
                "grammar": [],
                "pronunciation": [],
                "cultural": ["literature", "news"],
                "assets": [
                    {"type": ContentType.READING, "title": "Short Story", "minutes": 7},
                    {"type": ContentType.EXERCISE, "title": "Comprehension Check", "minutes": 5},
                    {"type": ContentType.FLASHCARD, "title": "New Words from Text", "minutes": 5},
                ],
            },
            FocusArea.LISTENING: {
                "title": f"Listening Skills: {target_focus.value.title()}",
                "objectives": [
                    f"Understand native speakers",
                    f"Catch key information",
                    f"Follow conversations",
                ],
                "vocab": ["listen", "hear", "understand", "speaker", "conversation"],
                "grammar": [],
                "pronunciation": ["connected speech"],
                "cultural": [],
                "assets": [
                    {"type": ContentType.AUDIO, "title": "Dialogue Listening", "minutes": 7},
                    {"type": ContentType.EXERCISE, "title": "Fill What You Hear", "minutes": 5},
                    {"type": ContentType.QUIZ, "title": "Listening Quiz", "minutes": 5},
                ],
            },
            FocusArea.WRITING: {
                "title": f"Writing Practice: {target_focus.value.title()}",
                "objectives": [
                    f"Write clear {target_focus.value} texts",
                    f"Use correct grammar and spelling",
                    f"Express ideas effectively",
                ],
                "vocab": ["write", "sentence", "paragraph", "email", "message"],
                "grammar": ["sentence structure", "connectors"],
                "pronunciation": [],
                "cultural": ["formal vs informal"],
                "assets": [
                    {"type": ContentType.WRITING, "title": "Guided Writing", "minutes": 7},
                    {"type": ContentType.EXERCISE, "title": "Sentence Building", "minutes": 5},
                    {"type": ContentType.FLASHCARD, "title": "Useful Phrases", "minutes": 5},
                ],
            },
            FocusArea.CULTURE: {
                "title": f"Cultural Insights: {target_focus.value.title()}",
                "objectives": [
                    f"Understand {target_focus.value} customs",
                    f"Learn cultural dos and don'ts",
                    f"Connect language to culture",
                ],
                "vocab": ["custom", "tradition", "holiday", "etiquette", "gesture"],
                "grammar": [],
                "pronunciation": [],
                "cultural": ["greetings", "dining", "celebrations", "values"],
                "assets": [
                    {"type": ContentType.VIDEO, "title": "Cultural Tour", "minutes": 7},
                    {"type": ContentType.READING, "title": "Customs Explained", "minutes": 5},
                    {"type": ContentType.QUIZ, "title": "Culture Quiz", "minutes": 5},
                ],
            },
        }
        
        focus_template = focus_templates.get(target_focus, focus_templates[FocusArea.CONVERSATION])
        
        # Build content assets
        content_assets = []
        for i, asset_template in enumerate(focus_template["assets"]):
            content_assets.append(ContentAsset(
                id=f"asset_{uuid.uuid4().hex[:8]}",
                type=asset_template["type"],
                source=ContentSource.LLM_GENERATED,
                title=asset_template["title"],
                description=f"Practice {target_focus.value} through {asset_template['title'].lower()}",
                metadata={
                    "estimated_minutes": asset_template["minutes"],
                    "xp_reward": 20,
                    "gamification": gamification.value,
                },
                duration_seconds=asset_template["minutes"] * 60,
                difficulty=0.5,
                age_appropriate=[age_group],
                language=learner_profile.target_language,
                tags=[target_focus.value, age_group.value],
            ))
        
        return LessonBlueprint(
            id=f"lesson_{uuid.uuid4().hex[:12]}",
            title=focus_template["title"],
            description=f"A {template['tone']} lesson for {age_group.value} learners focusing on {target_focus.value}. Uses {', '.join(template['examples'])} as context.",
            language=learner_profile.target_language,
            level=CEFRLevel(learner_profile.cefr_level),
            focus_area=target_focus,
            target_age_groups=[age_group],
            gamification_level=gamification,
            duration_minutes=duration,
            xp_reward=100,
            learning_objectives=focus_template["objectives"],
            vocabulary_targets=focus_template["vocab"],
            grammar_points=focus_template["grammar"],
            pronunciation_focus=focus_template["pronunciation"],
            cultural_notes=focus_template["cultural"],
            content_assets=content_assets,
            assessment_criteria={
                "completion": "Finish all activities",
                "accuracy": "80%+ on exercises",
                "participation": "Attempt all content types",
            },
        )
    
    async def _call_openai(self, prompt: str) -> LessonBlueprint:
        import openai
        client = openai.AsyncOpenAI(api_key=self.openai_key)
        
        response = await client.chat.completions.create(
            model=self.default_model,
            messages=[
                {"role": "system", "content": "You are an expert curriculum designer. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        
        data = json.loads(response.choices[0].message.content)
        return LessonBlueprint(**data)
    
    async def _call_anthropic(self, prompt: str) -> LessonBlueprint:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self.anthropic_key)
        
        response = await client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4000,
            system="You are an expert curriculum designer. Return only valid JSON.",
            messages=[{"role": "user", "content": prompt}],
        )
        
        data = json.loads(response.content[0].text)
        return LessonBlueprint(**data)
    
    async def search(self, query: ContentSearchQuery) -> list[ContentAsset]:
        return []
    
    async def fetch(self, asset_id: str) -> ContentAsset:
        raise NotImplementedError("LLM generates, doesn't fetch")
    
    async def _call_openai(self, prompt: str) -> LessonBlueprint:
        import openai
        client = openai.AsyncOpenAI(api_key=self.openai_key)
        
        response = await client.chat.completions.create(
            model=self.default_model,
            messages=[
                {"role": "system", "content": "You are an expert curriculum designer. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        
        data = json.loads(response.choices[0].message.content)
        return LessonBlueprint(**data)
    
    async def _call_anthropic(self, prompt: str) -> LessonBlueprint:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self.anthropic_key)
        
        response = await client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4000,
            system="You are an expert curriculum designer. Return only valid JSON.",
            messages=[{"role": "user", "content": prompt}],
        )
        
        data = json.loads(response.content[0].text)
        return LessonBlueprint(**data)
    
    async def search(self, query: ContentSearchQuery) -> list[ContentAsset]:
        # LLM doesn't "search" - it generates
        return []
    
    async def fetch(self, asset_id: str) -> ContentAsset:
        raise NotImplementedError("LLM generates, doesn't fetch")


class APICurriculumAdapter(ContentSourceAdapter):
    """Fetch from structured curriculum APIs (CEFR-aligned)"""
    
    def __init__(self):
        self.sources = {
            "language_transfer": "https://api.languagetransfer.org",
            "fsí": "https://fsi-language-courses.org/api",
            "duolingo": "https://api.duolingo.com",  # hypothetical
        }
    
    def get_source_type(self) -> ContentSource:
        return ContentSource.API_CURRICULUM
    
    async def search(self, query: ContentSearchQuery) -> list[ContentAsset]:
        # Would integrate with actual curriculum APIs
        return []
    
    async def fetch(self, asset_id: str) -> ContentAsset:
        raise NotImplementedError


class LessonGenerationService:
    """Main service orchestrating multi-source lesson generation"""
    
    def __init__(self):
        self.adapters: dict[ContentSource, ContentSourceAdapter] = {
            ContentSource.YOUTUBE: YouTubeAdapter(),
            ContentSource.TEXTBOOK: TextbookAdapter(),
            ContentSource.LLM_GENERATED: LLMSourceAdapter(),
            ContentSource.API_CURRICULUM: APICurriculumAdapter(),
        }
        self.llm_adapter = self.adapters[ContentSource.LLM_GENERATED]
    
    def register_adapter(self, adapter: ContentSourceAdapter):
        self.adapters[adapter.get_source_type()] = adapter
    
    async def generate_personalized_lesson(
        self,
        user_id: int,
        focus_area: Optional[FocusArea] = None,
        age_group: Optional[AgeGroup] = None,
        gamification: GamificationLevel = GamificationLevel.MEDIUM,
        duration_minutes: Optional[int] = None,
        language: str = "es",
    ) -> LessonBlueprint:
        """Generate a lesson tailored to the user's current gaps and preferences"""
        
        async with AsyncSessionLocal() as db:
            # Get learner's memory
            from app.services.tutor_memory_service import TutorMemoryService
            memory_service = TutorMemoryService(db)
            tutor_memory = await memory_service.get_or_create_memory(user_id, language=language)
            
            # Convert JSON profile to LearnerProfile object
            profile_data = tutor_memory.learner_profile
            profile = LearnerProfile(
                user_id=str(user_id),
                native_language=profile_data.get("native_language", "en"),
                target_language=profile_data.get("target_language", "es"),
                cefr_level=profile_data.get("cefr_level", "A1"),
                primary_goal=profile_data.get("primary_goal", "fun"),
                focus_areas=profile_data.get("focus_areas", ["conversation", "grammar", "vocabulary"]),
                interests=profile_data.get("interests", []),
                age_group=profile_data.get("age_group", "adult"),
                time_per_day_minutes=profile_data.get("daily_goal_minutes", 15),
                preferred_session_length=profile_data.get("preferred_session_length", 30),
                known_vocabulary=set(profile_data.get("known_vocabulary", [])),
                learning_vocabulary=set(profile_data.get("learning_vocabulary", [])),
                error_patterns=profile_data.get("error_patterns", {}),
                completed_topics=profile_data.get("completed_topics", []),
                preferred_content_types=profile_data.get("preferred_content_types", ["dialogues", "videos", "articles"]),
                content_difficulty_preference=profile_data.get("content_difficulty_preference", "slightly_above"),
            )
            
            # Convert JSON study plan to StudyPlan object
            study_plan = None
            if tutor_memory.study_plan:
                sp_data = tutor_memory.study_plan
                # Create minimal StudyPlan with required fields
                study_plan = StudyPlan(
                    plan_id=sp_data.get("plan_id", str(uuid.uuid4())),
                    user_id=str(user_id),
                    target_language=sp_data.get("target_language", "es"),
                    current_level=sp_data.get("current_level", "A1"),
                    target_level=sp_data.get("target_level", "B2"),
                    estimated_weeks=sp_data.get("estimated_weeks", 12),
                    weeks=[],
                    focus_distribution=sp_data.get("focus_distribution", {}),
                    milestones=[],
                )
            else:
                # Create default study plan
                study_plan = StudyPlan(
                    plan_id=str(uuid.uuid4()),
                    user_id=str(user_id),
                    target_language=language,
                    current_level=profile_data.get("cefr_level", "A1"),
                    target_level="B2",
                    estimated_weeks=12,
                    weeks=[],
                    focus_distribution={},
                    milestones=[],
                )
            
            # Determine age group from profile or default
            if age_group is None:
                # Could infer from voice settings or default to adult
                age_group = AgeGroup.ADULT
            
            # Determine focus area from study plan or gaps
            if focus_area is None and study_plan:
                focus_area = FocusArea(study_plan.current_focus)
            elif focus_area is None:
                focus_area = FocusArea.CONVERSATION
            
            # Determine duration
            if duration_minutes is None:
                duration_minutes = profile.time_per_day_minutes
            
            # Generate using LLM (pass user_id for BYOK key lookup)
            blueprint = await self.llm_adapter.generate_lesson_blueprint(
                learner_profile=profile,
                study_plan=study_plan,
                target_focus=focus_area,
                age_group=age_group,
                gamification=gamification,
                user_id=user_id,
            )
            
            # Enhance with multimedia from other sources
            await self._enrich_with_multimedia(blueprint, tutor_memory)
            
            return blueprint
    
    async def _enrich_with_multimedia(
        self,
        blueprint: LessonBlueprint,
        tutor_memory: TutorMemory,
    ):
        """Add video, audio, interactive content from external sources"""
        
        profile_data = tutor_memory.learner_profile
        target_language = profile_data.get("target_language", "es")
        cefr_level = profile_data.get("cefr_level", "A1")
        
        # Search YouTube for relevant videos
        youtube_adapter = self.adapters.get(ContentSource.YOUTUBE)
        if youtube_adapter:
            for objective in blueprint.learning_objectives[:3]:
                query = ContentSearchQuery(
                    language=target_language,
                    level=cefr_level,
                    focus_area=blueprint.focus_area,
                    topic=objective,
                    age_groups=blueprint.target_age_groups,
                    max_duration_minutes=10,
                    max_results=2,
                )
                videos = await youtube_adapter.search(query)
                blueprint.content_assets.extend(videos)
        
        # Search textbooks
        textbook_adapter = self.adapters.get(ContentSource.TEXTBOOK)
        if textbook_adapter:
            profile_data = tutor_memory.learner_profile
            query = ContentSearchQuery(
                language=profile_data.get("target_language", "es"),
                level=profile_data.get("cefr_level", "A1"),
                focus_area=blueprint.focus_area,
                topic=blueprint.title,
                age_groups=blueprint.target_age_groups,
                max_results=3,
            )
            textbook_content = await textbook_adapter.search(query)
            blueprint.content_assets.extend(textbook_content)
    
    async def create_lesson_from_blueprint(
        self,
        blueprint: LessonBlueprint,
        db: AsyncSession,
    ) -> Lesson:
        """Persist a lesson blueprint to the database"""
        
        # Get primary age group (first in list)
        target_age_group = blueprint.target_age_groups[0].value if blueprint.target_age_groups else "adult"
        
        lesson = Lesson(
            id=blueprint.id,
            title=blueprint.title,
            description=blueprint.description,
            language=blueprint.language,
            level=blueprint.level,
            focus_area=blueprint.focus_area,
            target_age_group=target_age_group,
            gamification_level=blueprint.gamification_level.value,
            duration=blueprint.duration_minutes,
            xp_reward=blueprint.xp_reward,
            prerequisites=blueprint.prerequisites,
            order=0,  # Will be set based on curriculum position
            tags=blueprint.metadata.get("tags", []),
            metadata_json=blueprint.metadata,
            is_active=True,
            is_premium=False,
        )
        
        db.add(lesson)
        await db.flush()
        
        # Create content items
        for i, asset in enumerate(blueprint.content_assets):
            content = LessonContent(
                lesson_id=lesson.id,
                content_id=asset.id,
                type=asset.type,
                title=asset.title,
                order=i,
                estimated_time=asset.duration_seconds // 60 or 5,
                required=True,
                data={
                    "source": asset.source.value,
                    "url": asset.url,
                    "local_path": asset.local_path,
                    "metadata": asset.metadata,
                    "description": asset.description,
                    "tags": asset.tags,
                },
                xp_reward=blueprint.xp_reward // len(blueprint.content_assets) if blueprint.content_assets else 0,
            )
            db.add(content)
        
        await db.commit()
        await db.refresh(lesson)
        
        return lesson
    
    async def generate_curriculum_for_language(
        self,
        language: str,
        age_group: AgeGroup,
        gamification: GamificationLevel,
        levels: list[CEFRLevel] = None,
        user_id: int = 0,
    ) -> list[LessonBlueprint]:
        """Generate a full curriculum for a language"""
        
        if levels is None:
            levels = [CEFRLevel.A1, CEFRLevel.A2, CEFRLevel.B1, CEFRLevel.B2, CEFRLevel.C1, CEFRLevel.C2]
        
        focus_areas = [
            FocusArea.CONVERSATION,
            FocusArea.GRAMMAR,
            FocusArea.VOCABULARY,
            FocusArea.PRONUNCIATION,
            FocusArea.READING,
            FocusArea.LISTENING,
            FocusArea.WRITING,
            FocusArea.CULTURE,
        ]
        
        blueprints = []
        
        for level in levels:
            for focus in focus_areas:
                # Create a mock profile for generation
                mock_profile = LearnerProfile(
                    user_id=str(user_id),
                    native_language="en",
                    target_language=language,
                    cefr_level=level.value,
                    primary_goal="fun",
                    focus_areas=[focus.value],
                    interests=["culture", "travel", "technology"],
                    age_group=age_group.value,
                    time_per_day_minutes=20,
                    preferred_session_length=30,
                )
                
                mock_plan = StudyPlan(
                    plan_id=str(uuid.uuid4()),
                    user_id=str(user_id),
                    target_language=language,
                    current_level=level.value,
                    target_level=CEFRLevel.C2.value,
                    estimated_weeks=12,
                    weeks=[],
                    focus_distribution={focus.value: 1.0},
                    milestones=[],
                )
                
                blueprint = await self.llm_adapter.generate_lesson_blueprint(
                    learner_profile=mock_profile,
                    study_plan=mock_plan,
                    target_focus=focus,
                    age_group=age_group,
                    gamification=gamification,
                    user_id=user_id,
                )
                blueprints.append(blueprint)
        
        return blueprints


# Singleton instance
_lesson_generator: Optional[LessonGenerationService] = None


def get_lesson_generator() -> LessonGenerationService:
    global _lesson_generator
    if _lesson_generator is None:
        _lesson_generator = LessonGenerationService()
    return _lesson_generator