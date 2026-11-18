"""
TTS Service with voice selection by language, age, gender
Supports multiple providers: Edge TTS (free), ElevenLabs, Azure, Google
"""
import asyncio
import hashlib
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import edge_tts
import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.tutor_memory import AvailableVoice, UserVoiceSettings

logger = structlog.get_logger()


@dataclass
class VoiceInfo:
    """Voice information"""
    voice_id: str
    name: str
    language: str
    provider: str
    gender: str  # male, female, neutral
    age_group: str  # child, teen, adult, senior
    accent: Optional[str] = None
    description: Optional[str] = None
    sample_url: Optional[str] = None
    supports_ssml: bool = False
    supports_emotion: bool = False
    max_length: int = 5000
    is_premium: bool = False


@dataclass
class TTSRequest:
    """TTS generation request"""
    text: str
    voice_id: str
    provider: str
    rate: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    ssml: bool = False


@dataclass
class TTSResult:
    """TTS generation result"""
    audio_data: bytes
    content_type: str
    duration: float  # estimated seconds
    voice_id: str
    provider: str


class TTSProvider(ABC):
    """Abstract TTS provider"""
    
    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> TTSResult:
        """Generate speech from text"""
        pass
    
    @abstractmethod
    async def get_available_voices(self, language: Optional[str] = None) -> List[VoiceInfo]:
        """Get available voices for a language"""
        pass
    
    @abstractmethod
    async def validate_voice(self, voice_id: str) -> bool:
        """Check if voice is available"""
        pass


class EdgeTTSProvider(TTSProvider):
    """Microsoft Edge TTS - Free, high quality"""
    
    # Voice mapping for common languages with age/gender characteristics
    VOICE_CATALOG = {
        # Spanish
        "es-ES-ElviraNeural": {"gender": "female", "age": "adult", "accent": "Spain", "name": "Elvira (Spain)"},
        "es-ES-AlvaroNeural": {"gender": "male", "age": "adult", "accent": "Spain", "name": "Alvaro (Spain)"},
        "es-MX-DaliaNeural": {"gender": "female", "age": "adult", "accent": "Mexico", "name": "Dalia (Mexico)"},
        "es-MX-JorgeNeural": {"gender": "male", "age": "adult", "accent": "Mexico", "name": "Jorge (Mexico)"},
        # English
        "en-US-AriaNeural": {"gender": "female", "age": "adult", "accent": "US", "name": "Aria (US)"},
        "en-US-GuyNeural": {"gender": "male", "age": "adult", "accent": "US", "name": "Guy (US)"},
        "en-US-JennyNeural": {"gender": "female", "age": "young_adult", "accent": "US", "name": "Jenny (US)"},
        "en-US-DavisNeural": {"gender": "male", "age": "young_adult", "accent": "US", "name": "Davis (US)"},
        "en-GB-LibbyNeural": {"gender": "female", "age": "adult", "accent": "UK", "name": "Libby (UK)"},
        "en-GB-RyanNeural": {"gender": "male", "age": "adult", "accent": "UK", "name": "Ryan (UK)"},
        # French
        "fr-FR-DeniseNeural": {"gender": "female", "age": "adult", "accent": "France", "name": "Denise (France)"},
        "fr-FR-HenriNeural": {"gender": "male", "age": "adult", "accent": "France", "name": "Henri (France)"},
        "fr-CA-SylvieNeural": {"gender": "female", "age": "adult", "accent": "Canada", "name": "Sylvie (Canada)"},
        # German
        "de-DE-KatjaNeural": {"gender": "female", "age": "adult", "accent": "Germany", "name": "Katja (Germany)"},
        "de-DE-ConradNeural": {"gender": "male", "age": "adult", "accent": "Germany", "name": "Conrad (Germany)"},
        # Italian
        "it-IT-ElsaNeural": {"gender": "female", "age": "adult", "accent": "Italy", "name": "Elsa (Italy)"},
        "it-IT-DiegoNeural": {"gender": "male", "age": "adult", "accent": "Italy", "name": "Diego (Italy)"},
        # Portuguese
        "pt-BR-FranciscaNeural": {"gender": "female", "age": "adult", "accent": "Brazil", "name": "Francisca (Brazil)"},
        "pt-BR-AntonioNeural": {"gender": "male", "age": "adult", "accent": "Brazil", "name": "Antonio (Brazil)"},
        "pt-PT-FernandaNeural": {"gender": "female", "age": "adult", "accent": "Portugal", "name": "Fernanda (Portugal)"},
        # Japanese
        "ja-JP-NanamiNeural": {"gender": "female", "age": "adult", "accent": "Japan", "name": "Nanami (Japan)"},
        "ja-JP-KeitaNeural": {"gender": "male", "age": "adult", "accent": "Japan", "name": "Keita (Japan)"},
        # Korean
        "ko-KR-SunHiNeural": {"gender": "female", "age": "adult", "accent": "Korea", "name": "SunHi (Korea)"},
        "ko-KR-InJoonNeural": {"gender": "male", "age": "adult", "accent": "Korea", "name": "InJoon (Korea)"},
        # Chinese
        "zh-CN-XiaoxiaoNeural": {"gender": "female", "age": "adult", "accent": "Mainland", "name": "Xiaoxiao (Mandarin)"},
        "zh-CN-YunxiNeural": {"gender": "male", "age": "adult", "accent": "Mainland", "name": "Yunxi (Mandarin)"},
        "zh-TW-HsiaoChenNeural": {"gender": "female", "age": "adult", "accent": "Taiwan", "name": "HsiaoChen (Taiwan)"},
        # Russian
        "ru-RU-SvetlanaNeural": {"gender": "female", "age": "adult", "accent": "Russia", "name": "Svetlana (Russia)"},
        "ru-RU-DmitryNeural": {"gender": "male", "age": "adult", "accent": "Russia", "name": "Dmitry (Russia)"},
        # Arabic
        "ar-SA-ZariyahNeural": {"gender": "female", "age": "adult", "accent": "Saudi", "name": "Zariyah (Saudi)"},
        "ar-SA-HamedNeural": {"gender": "male", "age": "adult", "accent": "Saudi", "name": "Hamed (Saudi)"},
        # Hindi
        "hi-IN-SwaraNeural": {"gender": "female", "age": "adult", "accent": "India", "name": "Swara (India)"},
        "hi-IN-MadhurNeural": {"gender": "male", "age": "adult", "accent": "India", "name": "Madhur (India)"},
    }
    
    LANGUAGE_CODE_MAP = {
        "es": ["es-ES", "es-MX"],
        "en": ["en-US", "en-GB"],
        "fr": ["fr-FR", "fr-CA"],
        "de": ["de-DE"],
        "it": ["it-IT"],
        "pt": ["pt-BR", "pt-PT"],
        "ja": ["ja-JP"],
        "ko": ["ko-KR"],
        "zh": ["zh-CN", "zh-TW"],
        "ru": ["ru-RU"],
        "ar": ["ar-SA"],
        "hi": ["hi-IN"],
        "nl": ["nl-NL"],
        "pl": ["pl-PL"],
        "tr": ["tr-TR"],
        "sv": ["sv-SE"],
        "da": ["da-DK"],
        "no": ["nb-NO"],
        "fi": ["fi-FI"],
        "cs": ["cs-CZ"],
        "hu": ["hu-HU"],
        "ro": ["ro-RO"],
        "bg": ["bg-BG"],
        "hr": ["hr-HR"],
        "sk": ["sk-SK"],
        "sl": ["sl-SI"],
        "et": ["et-EE"],
        "lv": ["lv-LV"],
        "lt": ["lt-LT"],
        "uk": ["uk-UA"],
        "el": ["el-GR"],
        "he": ["he-IL"],
        "th": ["th-TH"],
        "vi": ["vi-VN"],
        "id": ["id-ID"],
        "ms": ["ms-MY"],
    }
    
    async def synthesize(self, request: TTSRequest) -> TTSResult:
        """Generate speech using Edge TTS"""
        # Edge TTS expects rate/pitch/volume in format like "+20%" or "-10%"
        rate_pct = int((request.rate - 1) * 100)
        pitch_hz = int((request.pitch - 1) * 50)
        volume_pct = int((request.volume - 1) * 100)
        
        rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"
        pitch_str = f"+{pitch_hz}Hz" if pitch_hz >= 0 else f"{pitch_hz}Hz"
        volume_str = f"+{volume_pct}%" if volume_pct >= 0 else f"{volume_pct}%"
        
        communicate = edge_tts.Communicate(
            text=request.text,
            voice=request.voice_id,
            rate=rate_str,
            pitch=pitch_str,
            volume=volume_str,
        )
        
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        # Estimate duration (rough: ~150 words per minute)
        word_count = len(request.text.split())
        duration = (word_count / 150) * 60 / request.rate
        
        return TTSResult(
            audio_data=audio_data,
            content_type="audio/mpeg",
            duration=duration,
            voice_id=request.voice_id,
            provider="edge_tts",
        )
    
    async def get_available_voices(self, language: Optional[str] = None) -> List[VoiceInfo]:
        """Get available Edge TTS voices for a language"""
        voices = []
        
        lang_codes = self.LANGUAGE_CODE_MAP.get(language, []) if language else []
        
        for voice_id, info in self.VOICE_CATALOG.items():
            voice_lang = voice_id.split("-")[0]
            
            if language and voice_lang != language:
                continue
            
            # Check if voice matches language code
            if lang_codes and not any(voice_id.startswith(code) for code in lang_codes):
                continue
            
            voices.append(VoiceInfo(
                voice_id=voice_id,
                name=info["name"],
                language=voice_lang,
                provider="edge_tts",
                gender=info["gender"],
                age_group=info["age"],
                accent=info.get("accent"),
                description=f'{info["name"]} - {info.get("accent", "")} accent',
                supports_ssml=True,
                supports_emotion=False,
                max_length=5000,
                is_premium=False,
            ))
        
        return voices
    
    async def validate_voice(self, voice_id: str) -> bool:
        return voice_id in self.VOICE_CATALOG


class ElevenLabsProvider(TTSProvider):
    """ElevenLabs TTS - Premium, very high quality"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"
        self._voices_cache: Optional[List[VoiceInfo]] = None
    
    async def synthesize(self, request: TTSRequest) -> TTSResult:
        if not self.api_key:
            raise ValueError("ElevenLabs API key not configured")
        
        url = f"{self.base_url}/text-to-speech/{request.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        
        # Voice settings
        settings_data = {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        }
        
        payload = {
            "text": request.text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": settings_data,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            audio_data = response.content
        
        # Estimate duration
        word_count = len(request.text.split())
        duration = (word_count / 150) * 60 / request.rate
        
        return TTSResult(
            audio_data=audio_data,
            content_type="audio/mpeg",
            duration=duration,
            voice_id=request.voice_id,
            provider="elevenlabs",
        )
    
    async def get_available_voices(self, language: Optional[str] = None) -> List[VoiceInfo]:
        if self._voices_cache is None:
            await self._fetch_voices()
        
        voices = self._voices_cache or []
        
        if language:
            voices = [v for v in voices if v.language == language]
        
        return voices
    
    async def _fetch_voices(self):
        if not self.api_key:
            self._voices_cache = []
            return
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/voices",
                headers={"xi-api-key": self.api_key},
            )
            response.raise_for_status()
            data = response.json()
        
        voices = []
        for v in data.get("voices", []):
            # Parse labels for language, gender, age
            labels = v.get("labels", {})
            voices.append(VoiceInfo(
                voice_id=v["voice_id"],
                name=v["name"],
                language=labels.get("language", "en"),
                provider="elevenlabs",
                gender=labels.get("gender", "neutral"),
                age_group=labels.get("age", "adult"),
                accent=labels.get("accent"),
                description=v.get("description"),
                supports_ssml=False,
                supports_emotion=True,
                max_length=5000,
                is_premium=True,
            ))
        
        self._voices_cache = voices
    
    async def validate_voice(self, voice_id: str) -> bool:
        voices = await self.get_available_voices()
        return any(v.voice_id == voice_id for v in voices)


class TTSManager:
    """Manages multiple TTS providers and voice selection"""
    
    def __init__(self):
        self.providers: Dict[str, TTSProvider] = {
            "edge_tts": EdgeTTSProvider(),
        }
        
        # Add ElevenLabs if API key available
        if settings.ELEVENLABS_API_KEY:
            self.providers["elevenlabs"] = ElevenLabsProvider()
    
    def get_provider(self, provider: str) -> TTSProvider:
        if provider not in self.providers:
            raise ValueError(f"Unknown TTS provider: {provider}")
        return self.providers[provider]
    
    async def get_available_voices(
        self, 
        language: str, 
        provider: Optional[str] = None,
        gender: Optional[str] = None,
        age_group: Optional[str] = None,
    ) -> List[VoiceInfo]:
        """Get voices filtered by language, gender, age"""
        voices = []
        
        providers = [provider] if provider else list(self.providers.keys())
        
        for p_name in providers:
            provider_voices = await self.providers[p_name].get_available_voices(language)
            
            # Filter by gender
            if gender:
                provider_voices = [v for v in provider_voices if v.gender == gender]
            
            # Filter by age group
            if age_group:
                provider_voices = [v for v in provider_voices if v.age_group == age_group]
            
            voices.extend(provider_voices)
        
        return voices
    
    async def get_voice_by_characteristics(
        self,
        language: str,
        gender: str = "neutral",
        age_group: str = "adult",
        provider: str = "edge_tts",
    ) -> Optional[VoiceInfo]:
        """Find best matching voice for language/gender/age"""
        voices = await self.get_available_voices(language, provider, gender, age_group)
        
        if not voices:
            # Fallback: try without gender filter
            voices = await self.get_available_voices(language, provider, None, age_group)
        
        if not voices:
            # Fallback: try without age filter
            voices = await self.get_available_voices(language, provider, gender, None)
        
        if not voices:
            # Fallback: any voice for language
            voices = await self.get_available_voices(language, provider)
        
        return voices[0] if voices else None
    
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        provider: str = "edge_tts",
        rate: float = 1.0,
        pitch: float = 1.0,
        volume: float = 1.0,
    ) -> TTSResult:
        """Generate speech with specified voice"""
        tts_provider = self.get_provider(provider)
        request = TTSRequest(
            text=text,
            voice_id=voice_id,
            provider=provider,
            rate=rate,
            pitch=pitch,
            volume=volume,
        )
        return await tts_provider.synthesize(request)
    
    async def synthesize_with_cache(
        self,
        text: str,
        voice_id: str,
        provider: str = "edge_tts",
        rate: float = 1.0,
        pitch: float = 1.0,
        volume: float = 1.0,
        cache_dir: str = "./tts_cache",
    ) -> Tuple[bytes, str]:
        """Generate speech with file caching"""
        os.makedirs(cache_dir, exist_ok=True)
        
        # Create cache key
        cache_key = hashlib.md5(
            f"{text}:{voice_id}:{provider}:{rate}:{pitch}:{volume}".encode()
        ).hexdigest()
        cache_file = os.path.join(cache_dir, f"{cache_key}.mp3")
        
        # Check cache
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                return f.read(), "audio/mpeg"
        
        # Generate
        result = await self.synthesize(text, voice_id, provider, rate, pitch, volume)
        
        # Save to cache
        with open(cache_file, "wb") as f:
            f.write(result.audio_data)
        
        return result.audio_data, result.content_type


class VoiceSettingsService:
    """Manages user voice preferences"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tts_manager = TTSManager()
    
    async def get_user_voice_settings(
        self, 
        user_id: int, 
        language: str
    ) -> Optional[UserVoiceSettings]:
        """Get user's voice settings for a language"""
        result = await self.db.execute(
            select(UserVoiceSettings).where(
                UserVoiceSettings.user_id == user_id,
                UserVoiceSettings.language == language,
            )
        )
        return result.scalar_one_or_none()
    
    async def set_user_voice(
        self,
        user_id: int,
        language: str,
        voice_id: str,
        provider: str = "edge_tts",
        gender: str = "neutral",
        age_group: str = "adult",
        rate: float = 1.0,
        pitch: float = 1.0,
        volume: float = 1.0,
    ) -> UserVoiceSettings:
        """Set user's preferred voice for a language"""
        # Validate voice exists
        voice = await self.tts_manager.get_voice_by_characteristics(
            language, gender, age_group, provider
        )
        if not voice or voice.voice_id != voice_id:
            # Try direct validation
            provider_obj = self.tts_manager.get_provider(provider)
            if not await provider_obj.validate_voice(voice_id):
                raise ValueError(f"Voice {voice_id} not available for {provider}")
        
        # Get or create settings
        settings = await self.get_user_voice_settings(user_id, language)
        
        if settings is None:
            settings = UserVoiceSettings(
                user_id=user_id,
                language=language,
                voice_id=voice_id,
                provider=provider,
                gender=gender,
                age_group=age_group,
                rate=rate,
                pitch=pitch,
                volume=volume,
            )
            self.db.add(settings)
        else:
            settings.voice_id = voice_id
            settings.provider = provider
            settings.gender = gender
            settings.age_group = age_group
            settings.rate = rate
            settings.pitch = pitch
            settings.volume = volume
        
        await self.db.commit()
        await self.db.refresh(settings)
        return settings
    
    async def get_available_voices_for_user(
        self,
        user_id: int,
        language: str,
        gender: Optional[str] = None,
        age_group: Optional[str] = None,
    ) -> List[VoiceInfo]:
        """Get available voices for user's language with optional filters"""
        return await self.tts_manager.get_available_voices(
            language, gender=gender, age_group=age_group
        )
    
    async def get_recommended_voice(
        self,
        user_id: int,
        language: str,
    ) -> VoiceInfo:
        """Get recommended voice for user based on their profile"""
        # Get user's current settings or defaults
        settings = await self.get_user_voice_settings(user_id, language)
        
        if settings:
            # Use their preferred characteristics
            return await self.tts_manager.get_voice_by_characteristics(
                language,
                gender=settings.gender,
                age_group=settings.age_group,
                provider=settings.provider,
            ) or VoiceInfo(
                voice_id=settings.voice_id,
                name="Custom",
                language=language,
                provider=settings.provider,
                gender=settings.gender,
                age_group=settings.age_group,
            )
        
        # Default: adult female voice for the language
        return await self.tts_manager.get_voice_by_characteristics(
            language, gender="female", age_group="adult"
        ) or VoiceInfo(
            voice_id="default",
            name="Default",
            language=language,
            provider="edge_tts",
            gender="female",
            age_group="adult",
        )


# Singleton instance
_tts_manager: Optional[TTSManager] = None


def get_tts_manager() -> TTSManager:
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = TTSManager()
    return _tts_manager