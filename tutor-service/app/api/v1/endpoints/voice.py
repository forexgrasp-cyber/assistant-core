"""
Voice settings API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_active_user
from app.models.user import User
from app.models.tutor_memory import UserVoiceSettings, AvailableVoice
from app.schemas.voice import (
    VoiceSettingsResponse,
    VoiceSettingsUpdate,
    AvailableVoiceResponse,
    VoiceRecommendationResponse,
    VoicePreviewRequest,
    VoicePreviewResponse,
)
from app.services.tts_service import get_tts_manager, VoiceSettingsService

router = APIRouter()


@router.get("/settings", response_model=VoiceSettingsResponse)
async def get_voice_settings(
    language: str = Query(..., description="Target language code (e.g., 'es', 'fr')"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's voice settings for a language"""
    service = VoiceSettingsService(db)
    settings = await service.get_user_voice_settings(current_user.id, language)
    
    if not settings:
        # Return defaults
        recommended = await service.get_recommended_voice(current_user.id, language)
        return VoiceSettingsResponse(
            language=language,
            voice_id=recommended.voice_id,
            provider=recommended.provider,
            gender=recommended.gender,
            age_group=recommended.age_group,
            rate=1.0,
            pitch=1.0,
            volume=1.0,
            is_default=True,
        )
    
    return VoiceSettingsResponse(
        language=settings.language,
        voice_id=settings.voice_id,
        provider=settings.provider,
        gender=settings.gender,
        age_group=settings.age_group,
        accent=settings.accent,
        rate=settings.rate,
        pitch=settings.pitch,
        volume=settings.volume,
        is_default=False,
    )


@router.put("/settings", response_model=VoiceSettingsResponse)
async def update_voice_settings(
    language: str = Query(..., description="Target language code"),
    settings_update: VoiceSettingsUpdate = ...,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user's voice settings for a language"""
    service = VoiceSettingsService(db)
    
    try:
        settings = await service.set_user_voice(
            user_id=current_user.id,
            language=language,
            voice_id=settings_update.voice_id,
            provider=settings_update.provider,
            gender=settings_update.gender,
            age_group=settings_update.age_group,
            rate=settings_update.rate,
            pitch=settings_update.pitch,
            volume=settings_update.volume,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return VoiceSettingsResponse(
        language=settings.language,
        voice_id=settings.voice_id,
        provider=settings.provider,
        gender=settings.gender,
        age_group=settings.age_group,
        accent=settings.accent,
        rate=settings.rate,
        pitch=settings.pitch,
        volume=settings.volume,
        is_default=False,
    )


@router.get("/available", response_model=List[AvailableVoiceResponse])
async def get_available_voices(
    language: str = Query(..., description="Target language code"),
    gender: Optional[str] = Query(None, description="Filter by gender: male, female, neutral"),
    age_group: Optional[str] = Query(None, description="Filter by age: child, teen, adult, senior"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get available voices for a language with optional filters"""
    service = VoiceSettingsService(db)
    voices = await service.get_available_voices_for_user(
        current_user.id, language, gender, age_group
    )
    
    if provider:
        voices = [v for v in voices if v.provider == provider]
    
    return [
        AvailableVoiceResponse(
            voice_id=v.voice_id,
            name=v.name,
            language=v.language,
            provider=v.provider,
            gender=v.gender,
            age_group=v.age_group,
            accent=v.accent,
            description=v.description,
            supports_ssml=v.supports_ssml,
            supports_emotion=v.supports_emotion,
            is_premium=v.is_premium,
        )
        for v in voices
    ]


@router.get("/recommendation", response_model=VoiceRecommendationResponse)
async def get_voice_recommendation(
    language: str = Query(..., description="Target language code"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recommended voice for user based on profile"""
    service = VoiceSettingsService(db)
    voice = await service.get_recommended_voice(current_user.id, language)
    
    return VoiceRecommendationResponse(
        voice_id=voice.voice_id,
        name=voice.name,
        language=voice.language,
        provider=voice.provider,
        gender=voice.gender,
        age_group=voice.age_group,
        accent=voice.accent,
        reason="Recommended based on your profile and language",
    )


@router.post("/preview", response_model=VoicePreviewResponse)
async def preview_voice(
    request: VoicePreviewRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Generate a preview of a voice with sample text"""
    tts_manager = get_tts_manager()
    
    try:
        audio_data, content_type = await tts_manager.synthesize_with_cache(
            text=request.text,
            voice_id=request.voice_id,
            provider=request.provider,
            rate=request.rate,
            pitch=request.pitch,
            volume=request.volume,
        )
        
        import base64
        audio_base64 = base64.b64encode(audio_data).decode()
        
        return VoicePreviewResponse(
            audio_base64=audio_base64,
            content_type=content_type,
            voice_id=request.voice_id,
            provider=request.provider,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")


@router.get("/providers")
async def get_tts_providers():
    """Get list of available TTS providers"""
    return {
        "providers": [
            {
                "id": "edge_tts",
                "name": "Microsoft Edge TTS",
                "description": "Free, high-quality neural voices",
                "premium": False,
                "languages_supported": 70,
            },
            {
                "id": "elevenlabs",
                "name": "ElevenLabs",
                "description": "Premium, ultra-realistic voices with emotion",
                "premium": True,
                "languages_supported": 29,
            },
        ]
    }