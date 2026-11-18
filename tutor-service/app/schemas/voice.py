"""
Voice settings schemas for Tutor Service API
"""
from typing import Optional
from pydantic import BaseModel, Field, validator


class VoiceSettingsResponse(BaseModel):
    """User's voice settings for a language"""
    language: str
    voice_id: str
    provider: str
    gender: str
    age_group: str
    accent: Optional[str] = None
    rate: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=1.0, ge=0.5, le=2.0)
    volume: float = Field(default=1.0, ge=0.0, le=1.0)
    is_default: bool = False
    
    class Config:
        from_attributes = True


class VoiceSettingsUpdate(BaseModel):
    """Voice settings update request"""
    voice_id: str
    provider: str = "edge_tts"
    gender: str = "neutral"
    age_group: str = "adult"
    rate: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=1.0, ge=0.5, le=2.0)
    volume: float = Field(default=1.0, ge=0.0, le=1.0)
    
    @validator("gender")
    def validate_gender(cls, v):
        if v not in ["male", "female", "neutral"]:
            raise ValueError("Gender must be: male, female, or neutral")
        return v
    
    @validator("age_group")
    def validate_age_group(cls, v):
        if v not in ["child", "teen", "adult", "senior"]:
            raise ValueError("Age group must be: child, teen, adult, or senior")
        return v
    
    @validator("provider")
    def validate_provider(cls, v):
        if v not in ["edge_tts", "elevenlabs", "azure", "google"]:
            raise ValueError("Provider must be: edge_tts, elevenlabs, azure, or google")
        return v


class AvailableVoiceResponse(BaseModel):
    """Available voice information"""
    voice_id: str
    name: str
    language: str
    provider: str
    gender: str
    age_group: str
    accent: Optional[str] = None
    description: Optional[str] = None
    supports_ssml: bool = False
    supports_emotion: bool = False
    is_premium: bool = False
    
    class Config:
        from_attributes = True


class VoiceRecommendationResponse(BaseModel):
    """Recommended voice for user"""
    voice_id: str
    name: str
    language: str
    provider: str
    gender: str
    age_group: str
    accent: Optional[str] = None
    reason: str


class VoicePreviewRequest(BaseModel):
    """Voice preview generation request"""
    text: str = Field(default="Hello! I'm your language tutor. Let's practice together.", max_length=500)
    voice_id: str
    provider: str = "edge_tts"
    rate: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=1.0, ge=0.5, le=2.0)
    volume: float = Field(default=1.0, ge=0.0, le=1.0)


class VoicePreviewResponse(BaseModel):
    """Voice preview response with base64 audio"""
    audio_base64: str
    content_type: str
    voice_id: str
    provider: str