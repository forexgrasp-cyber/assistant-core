"""
Lesson Generation API - Multi-source content pipeline endpoints
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_active_user
from app.models.user import User
from app.models.lesson import Lesson, CEFRLevel, FocusArea
from app.services.lesson_generator import (
    LessonGenerationService, LessonBlueprint, AgeGroup, GamificationLevel,
    ContentSource, ContentSearchQuery, get_lesson_generator,
)
from app.services.tutor_memory_service import TutorMemoryService


router = APIRouter()


# Request/Response models
class GenerateLessonRequest(BaseModel):
    focus_area: Optional[FocusArea] = None
    age_group: AgeGroup = AgeGroup.ADULT
    gamification: GamificationLevel = GamificationLevel.MEDIUM
    duration_minutes: Optional[int] = Field(None, ge=5, le=120)
    use_sources: List[ContentSource] = Field(default_factory=list)
    language: str = Field("es", min_length=2, max_length=10)


class GenerateLessonResponse(BaseModel):
    blueprint: dict
    lesson_id: Optional[str] = None
    status: str  # "generated", "saved", "error"
    message: str


class SearchContentRequest(BaseModel):
    language: str
    level: CEFRLevel
    focus_area: FocusArea
    topic: str
    age_groups: List[AgeGroup] = Field(default_factory=list)
    max_duration_minutes: int = Field(30, ge=1, le=120)
    max_results: int = Field(10, ge=1, le=50)
    gamification: GamificationLevel = GamificationLevel.MEDIUM
    content_types: List[str] = Field(default_factory=list)
    sources: List[ContentSource] = Field(default_factory=list)


class SearchContentResponse(BaseModel):
    assets: List[dict]
    total: int
    sources_searched: List[str]


class GenerateCurriculumRequest(BaseModel):
    language: str
    age_group: AgeGroup = AgeGroup.ADULT
    gamification: GamificationLevel = GamificationLevel.MEDIUM
    levels: List[CEFRLevel] = Field(default_factory=list)
    focus_areas: List[FocusArea] = Field(default_factory=list)


class GenerateCurriculumResponse(BaseModel):
    total_lessons: int
    lessons: List[dict]
    estimated_hours: float


@router.post("/lesson", response_model=GenerateLessonResponse)
async def generate_personalized_lesson(
    request: GenerateLessonRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a personalized lesson based on learner's gaps and preferences"""
    
    generator = get_lesson_generator()
    
    try:
        blueprint = await generator.generate_personalized_lesson(
            user_id=current_user.id,
            focus_area=request.focus_area,
            age_group=request.age_group,
            gamification=request.gamification,
            duration_minutes=request.duration_minutes,
            language=request.language,
        )
        
        # Save to database in background
        lesson = await generator.create_lesson_from_blueprint(blueprint, db)
        
        return GenerateLessonResponse(
            blueprint=blueprint.__dict__,
            lesson_id=lesson.id,
            status="saved",
            message="Lesson generated and saved successfully",
        )
    except Exception as e:
        return GenerateLessonResponse(
            blueprint={},
            lesson_id=None,
            status="error",
            message=f"Generation failed: {str(e)}",
        )


@router.post("/lesson/preview", response_model=GenerateLessonResponse)
async def preview_generated_lesson(
    request: GenerateLessonRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Preview a generated lesson without saving"""
    
    generator = get_lesson_generator()
    
    try:
        blueprint = await generator.generate_personalized_lesson(
            user_id=current_user.id,
            focus_area=request.focus_area,
            age_group=request.age_group,
            gamification=request.gamification,
            duration_minutes=request.duration_minutes,
            language=request.language,
        )
        
        return GenerateLessonResponse(
            blueprint=blueprint.__dict__,
            lesson_id=None,
            status="generated",
            message="Lesson preview generated (not saved)",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/content/search", response_model=SearchContentResponse)
async def search_content(
    request: SearchContentRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Search for content assets across multiple sources"""
    
    generator = get_lesson_generator()
    all_assets = []
    sources_searched = []
    
    sources_to_search = request.sources or [
        ContentSource.YOUTUBE,
        ContentSource.TEXTBOOK,
        ContentSource.API_CURRICULUM,
    ]
    
    for source in sources_to_search:
        adapter = generator.adapters.get(source)
        if adapter:
            try:
                query = ContentSearchQuery(
                    language=request.language,
                    level=request.level,
                    focus_area=request.focus_area,
                    topic=request.topic,
                    age_groups=request.age_groups or [AgeGroup.ADULT],
                    max_duration_minutes=request.max_duration_minutes,
                    max_results=request.max_results,
                    gamification=request.gamification,
                )
                assets = await adapter.search(query)
                all_assets.extend([asset.__dict__ for asset in assets])
                sources_searched.append(source.value)
            except Exception as e:
                # Log error but continue with other sources
                pass
    
    return SearchContentResponse(
        assets=all_assets[:request.max_results],
        total=len(all_assets),
        sources_searched=sources_searched,
    )


@router.post("/curriculum/generate", response_model=GenerateCurriculumResponse)
async def generate_full_curriculum(
    request: GenerateCurriculumRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a complete curriculum for a language"""
    
    generator = get_lesson_generator()
    
    try:
        blueprints = await generator.generate_curriculum_for_language(
            language=request.language,
            age_group=request.age_group,
            gamification=request.gamification,
            levels=request.levels or None,
            user_id=current_user.id,
        )
        
        # Save all lessons in background
        saved_count = 0
        for blueprint in blueprints:
            try:
                await generator.create_lesson_from_blueprint(blueprint, db)
                saved_count += 1
            except Exception:
                continue
        
        total_minutes = sum(b.duration_minutes for b in blueprints)
        
        return GenerateCurriculumResponse(
            total_lessons=saved_count,
            lessons=[b.__dict__ for b in blueprints],
            estimated_hours=total_minutes / 60,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Curriculum generation failed: {str(e)}")


@router.get("/sources")
async def list_available_sources(
    current_user: User = Depends(get_current_active_user),
):
    """List available content sources and their capabilities"""
    
    generator = get_lesson_generator()
    
    sources_info = {}
    for source_type, adapter in generator.adapters.items():
        sources_info[source_type.value] = {
            "name": source_type.value.replace("_", " ").title(),
            "type": source_type.value,
            "capabilities": ["search", "fetch"] if source_type != ContentSource.LLM_GENERATED else ["generate"],
            "requires_api_key": source_type in [ContentSource.YOUTUBE, ContentSource.API_CURRICULUM],
            "configured": True,  # Could check actual config
        }
    
    return {
        "sources": sources_info,
        "age_groups": [ag.value for ag in AgeGroup],
        "gamification_levels": [gl.value for gl in GamificationLevel],
        "content_types": [ct.value for ct in ContentType],
    }


@router.post("/content/fetch/{source}/{asset_id}")
async def fetch_content_asset(
    source: ContentSource,
    asset_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Fetch a specific content asset by ID"""
    
    generator = get_lesson_generator()
    adapter = generator.adapters.get(source)
    
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Source {source} not available")
    
    try:
        asset = await adapter.fetch(asset_id)
        return asset.__dict__
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Asset not found: {str(e)}")


# Import ContentType for the sources endpoint
from app.models.lesson import ContentType