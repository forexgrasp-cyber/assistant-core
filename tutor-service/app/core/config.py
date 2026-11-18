"""
Configuration settings for Tutor Service
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict


class Settings(BaseSettings):
    """Application settings"""
    model_config = ConfigDict(extra='allow', env_file='.env', case_sensitive=True)
    
    # App
    APP_NAME: str = "Tutor Service"
    VERSION: str = "2026.11.3"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://tutor.yourdomain.com",
    ]
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./tutor.db"
    DATABASE_ECHO: bool = False
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Shared Canonical Services
    SHARED_CANONICAL_SERVICES_VERSION: str = "2026.11.3"
    
    # Tutor Specific
    SUPPORTED_LANGUAGES: List[str] = [
        "en", "es", "fr", "de", "it", "pt", "ja", "ko", "zh",
        "ru", "ar", "hi", "nl", "pl", "tr", "sv", "da", "no",
        "fi", "cs", "hu", "ro", "uk", "el", "he", "th", "vi",
        "id", "ms", "tl", "sw", "fa"
    ]
    
    CEFR_LEVELS: List[str] = ["A1", "A2", "B1", "B2", "C1", "C2"]
    
    FOCUS_AREAS: List[str] = [
        "conversation", "grammar", "vocabulary", "pronunciation",
        "writing", "reading", "listening", "culture"
    ]
    
    # AI/LLM - Paid providers (optional)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEFAULT_MODEL: str = "gpt-4-turbo-preview"
    
    # Free LLM providers from shared.llm (optional - enhance free tier)
    # Get free API keys from: https://openrouter.ai/keys, https://console.groq.com/keys, etc.
    OPENROUTER_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GOOGLE_AI_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    NVIDIA_NIM_API_KEY: str = ""
    COHERE_API_KEY: str = ""
    TOGETHER_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    CLOUDFLARE_AI_TOKEN: str = ""
    CLOUDFLARE_ACCOUNT_ID: str = ""
    CEREBRAS_API_KEY: str = ""
    
    # TTS
    ELEVENLABS_API_KEY: str = ""
    
    # YouTube
    YOUTUBE_API_KEY: str = ""
    
    # Speech
    SPEECH_RECOGNITION_LANGUAGE_MAP: dict = {
        "en": "en-US", "es": "es-ES", "fr": "fr-FR", "de": "de-DE",
        "it": "it-IT", "pt": "pt-BR", "ja": "ja-JP", "ko": "ko-KR",
        "zh": "zh-CN", "ru": "ru-RU", "ar": "ar-SA", "hi": "hi-IN",
        "nl": "nl-NL", "pl": "pl-PL", "tr": "tr-TR", "sv": "sv-SE",
        "da": "da-DK", "no": "nb-NO", "fi": "fi-FI", "cs": "cs-CZ",
        "hu": "hu-HU", "ro": "ro-RO", "uk": "uk-UA", "el": "el-GR",
        "he": "he-IL", "th": "th-TH", "vi": "vi-VN", "id": "id-ID",
        "ms": "ms-MY", "tl": "tl-PH", "sw": "sw-KE", "fa": "fa-IR",
    }
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_AUDIO_TYPES: List[str] = ["audio/webm", "audio/mp3", "audio/wav", "audio/ogg"]
    ALLOWED_VIDEO_TYPES: List[str] = ["video/mp4", "video/webm"]
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Feature Flags
    ENABLE_ANALYTICS: bool = True
    ENABLE_A_B_TESTING: bool = True
    ENABLE_GDPR_ERASURE: bool = True
    ENABLE_COMPLIANCE_REPORTS: bool = True
    
    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@tutor.yourdomain.com"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()