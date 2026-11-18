"""
Database seeder for available TTS voices
Populates the database with voices from Edge TTS and other providers
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, init_db
from app.models.tutor_memory import AvailableVoice


# Edge TTS voices catalog (matching tts_service.py)
EDGE_TTS_VOICES = [
    # Spanish
    {"voice_id": "es-ES-ElviraNeural", "language": "es", "name": "Elvira (Spain)", "gender": "female", "age_group": "adult", "accent": "Spain", "provider": "edge_tts"},
    {"voice_id": "es-ES-AlvaroNeural", "language": "es", "name": "Alvaro (Spain)", "gender": "male", "age_group": "adult", "accent": "Spain", "provider": "edge_tts"},
    {"voice_id": "es-MX-DaliaNeural", "language": "es", "name": "Dalia (Mexico)", "gender": "female", "age_group": "adult", "accent": "Mexico", "provider": "edge_tts"},
    {"voice_id": "es-MX-JorgeNeural", "language": "es", "name": "Jorge (Mexico)", "gender": "male", "age_group": "adult", "accent": "Mexico", "provider": "edge_tts"},
    # English
    {"voice_id": "en-US-AriaNeural", "language": "en", "name": "Aria (US)", "gender": "female", "age_group": "adult", "accent": "US", "provider": "edge_tts"},
    {"voice_id": "en-US-GuyNeural", "language": "en", "name": "Guy (US)", "gender": "male", "age_group": "adult", "accent": "US", "provider": "edge_tts"},
    {"voice_id": "en-US-JennyNeural", "language": "en", "name": "Jenny (US)", "gender": "female", "age_group": "young_adult", "accent": "US", "provider": "edge_tts"},
    {"voice_id": "en-US-DavisNeural", "language": "en", "name": "Davis (US)", "gender": "male", "age_group": "young_adult", "accent": "US", "provider": "edge_tts"},
    {"voice_id": "en-GB-LibbyNeural", "language": "en", "name": "Libby (UK)", "gender": "female", "age_group": "adult", "accent": "UK", "provider": "edge_tts"},
    {"voice_id": "en-GB-RyanNeural", "language": "en", "name": "Ryan (UK)", "gender": "male", "age_group": "adult", "accent": "UK", "provider": "edge_tts"},
    # French
    {"voice_id": "fr-FR-DeniseNeural", "language": "fr", "name": "Denise (France)", "gender": "female", "age_group": "adult", "accent": "France", "provider": "edge_tts"},
    {"voice_id": "fr-FR-HenriNeural", "language": "fr", "name": "Henri (France)", "gender": "male", "age_group": "adult", "accent": "France", "provider": "edge_tts"},
    {"voice_id": "fr-CA-SylvieNeural", "language": "fr", "name": "Sylvie (Canada)", "gender": "female", "age_group": "adult", "accent": "Canada", "provider": "edge_tts"},
    # German
    {"voice_id": "de-DE-KatjaNeural", "language": "de", "name": "Katja (Germany)", "gender": "female", "age_group": "adult", "accent": "Germany", "provider": "edge_tts"},
    {"voice_id": "de-DE-ConradNeural", "language": "de", "name": "Conrad (Germany)", "gender": "male", "age_group": "adult", "accent": "Germany", "provider": "edge_tts"},
    # Italian
    {"voice_id": "it-IT-ElsaNeural", "language": "it", "name": "Elsa (Italy)", "gender": "female", "age_group": "adult", "accent": "Italy", "provider": "edge_tts"},
    {"voice_id": "it-IT-DiegoNeural", "language": "it", "name": "Diego (Italy)", "gender": "male", "age_group": "adult", "accent": "Italy", "provider": "edge_tts"},
    # Portuguese
    {"voice_id": "pt-BR-FranciscaNeural", "language": "pt", "name": "Francisca (Brazil)", "gender": "female", "age_group": "adult", "accent": "Brazil", "provider": "edge_tts"},
    {"voice_id": "pt-BR-AntonioNeural", "language": "pt", "name": "Antonio (Brazil)", "gender": "male", "age_group": "adult", "accent": "Brazil", "provider": "edge_tts"},
    {"voice_id": "pt-PT-FernandaNeural", "language": "pt", "name": "Fernanda (Portugal)", "gender": "female", "age_group": "adult", "accent": "Portugal", "provider": "edge_tts"},
    # Japanese
    {"voice_id": "ja-JP-NanamiNeural", "language": "ja", "name": "Nanami (Japan)", "gender": "female", "age_group": "adult", "accent": "Japan", "provider": "edge_tts"},
    {"voice_id": "ja-JP-KeitaNeural", "language": "ja", "name": "Keita (Japan)", "gender": "male", "age_group": "adult", "accent": "Japan", "provider": "edge_tts"},
    # Korean
    {"voice_id": "ko-KR-SunHiNeural", "language": "ko", "name": "SunHi (Korea)", "gender": "female", "age_group": "adult", "accent": "Korea", "provider": "edge_tts"},
    {"voice_id": "ko-KR-InJoonNeural", "language": "ko", "name": "InJoon (Korea)", "gender": "male", "age_group": "adult", "accent": "Korea", "provider": "edge_tts"},
    # Chinese
    {"voice_id": "zh-CN-XiaoxiaoNeural", "language": "zh", "name": "Xiaoxiao (Mandarin)", "gender": "female", "age_group": "adult", "accent": "Mainland", "provider": "edge_tts"},
    {"voice_id": "zh-CN-YunxiNeural", "language": "zh", "name": "Yunxi (Mandarin)", "gender": "male", "age_group": "adult", "accent": "Mainland", "provider": "edge_tts"},
    {"voice_id": "zh-TW-HsiaoChenNeural", "language": "zh", "name": "HsiaoChen (Taiwan)", "gender": "female", "age_group": "adult", "accent": "Taiwan", "provider": "edge_tts"},
    # Russian
    {"voice_id": "ru-RU-SvetlanaNeural", "language": "ru", "name": "Svetlana (Russia)", "gender": "female", "age_group": "adult", "accent": "Russia", "provider": "edge_tts"},
    {"voice_id": "ru-RU-DmitryNeural", "language": "ru", "name": "Dmitry (Russia)", "gender": "male", "age_group": "adult", "accent": "Russia", "provider": "edge_tts"},
    # Arabic
    {"voice_id": "ar-SA-ZariyahNeural", "language": "ar", "name": "Zariyah (Saudi)", "gender": "female", "age_group": "adult", "accent": "Saudi", "provider": "edge_tts"},
    {"voice_id": "ar-SA-HamedNeural", "language": "ar", "name": "Hamed (Saudi)", "gender": "male", "age_group": "adult", "accent": "Saudi", "provider": "edge_tts"},
    # Hindi
    {"voice_id": "hi-IN-SwaraNeural", "language": "hi", "name": "Swara (India)", "gender": "female", "age_group": "adult", "accent": "India", "provider": "edge_tts"},
    {"voice_id": "hi-IN-MadhurNeural", "language": "hi", "name": "Madhur (India)", "gender": "male", "age_group": "adult", "accent": "India", "provider": "edge_tts"},
    # Dutch
    {"voice_id": "nl-NL-ColetteNeural", "language": "nl", "name": "Colette (Netherlands)", "gender": "female", "age_group": "adult", "accent": "Netherlands", "provider": "edge_tts"},
    {"voice_id": "nl-NL-FennaNeural", "language": "nl", "name": "Fenna (Netherlands)", "gender": "female", "age_group": "young_adult", "accent": "Netherlands", "provider": "edge_tts"},
    {"voice_id": "nl-NL-MaartenNeural", "language": "nl", "name": "Maarten (Netherlands)", "gender": "male", "age_group": "adult", "accent": "Netherlands", "provider": "edge_tts"},
    # Polish
    {"voice_id": "pl-PL-AgataNeural", "language": "pl", "name": "Agata (Poland)", "gender": "female", "age_group": "adult", "accent": "Poland", "provider": "edge_tts"},
    {"voice_id": "pl-PL-MarekNeural", "language": "pl", "name": "Marek (Poland)", "gender": "male", "age_group": "adult", "accent": "Poland", "provider": "edge_tts"},
    # Turkish
    {"voice_id": "tr-TR-EmelNeural", "language": "tr", "name": "Emel (Turkey)", "gender": "female", "age_group": "adult", "accent": "Turkey", "provider": "edge_tts"},
    {"voice_id": "tr-TR-AhmetNeural", "language": "tr", "name": "Ahmet (Turkey)", "gender": "male", "age_group": "adult", "accent": "Turkey", "provider": "edge_tts"},
    # Swedish
    {"voice_id": "sv-SE-SofieNeural", "language": "sv", "name": "Sofie (Sweden)", "gender": "female", "age_group": "adult", "accent": "Sweden", "provider": "edge_tts"},
    {"voice_id": "sv-SE-MattiasNeural", "language": "sv", "name": "Mattias (Sweden)", "gender": "male", "age_group": "adult", "accent": "Sweden", "provider": "edge_tts"},
    # Danish
    {"voice_id": "da-DK-ChristelNeural", "language": "da", "name": "Christel (Denmark)", "gender": "female", "age_group": "adult", "accent": "Denmark", "provider": "edge_tts"},
    {"voice_id": "da-DK-JeppeNeural", "language": "da", "name": "Jeppe (Denmark)", "gender": "male", "age_group": "adult", "accent": "Denmark", "provider": "edge_tts"},
    # Norwegian
    {"voice_id": "nb-NO-PernilleNeural", "language": "no", "name": "Pernille (Norway)", "gender": "female", "age_group": "adult", "accent": "Norway", "provider": "edge_tts"},
    {"voice_id": "nb-NO-FinnNeural", "language": "no", "name": "Finn (Norway)", "gender": "male", "age_group": "adult", "accent": "Norway", "provider": "edge_tts"},
    # Finnish
    {"voice_id": "fi-FI-NooraNeural", "language": "fi", "name": "Noora (Finland)", "gender": "female", "age_group": "adult", "accent": "Finland", "provider": "edge_tts"},
    {"voice_id": "fi-FI-HarriNeural", "language": "fi", "name": "Harri (Finland)", "gender": "male", "age_group": "adult", "accent": "Finland", "provider": "edge_tts"},
    # Czech
    {"voice_id": "cs-CZ-VlastaNeural", "language": "cs", "name": "Vlasta (Czech Republic)", "gender": "female", "age_group": "adult", "accent": "Czech Republic", "provider": "edge_tts"},
    {"voice_id": "cs-CZ-AntoninNeural", "language": "cs", "name": "Antonin (Czech Republic)", "gender": "male", "age_group": "adult", "accent": "Czech Republic", "provider": "edge_tts"},
    # Hungarian
    {"voice_id": "hu-HU-NoemiNeural", "language": "hu", "name": "Noemi (Hungary)", "gender": "female", "age_group": "adult", "accent": "Hungary", "provider": "edge_tts"},
    {"voice_id": "hu-HU-TamasNeural", "language": "hu", "name": "Tamas (Hungary)", "gender": "male", "age_group": "adult", "accent": "Hungary", "provider": "edge_tts"},
    # Romanian
    {"voice_id": "ro-RO-AlinaNeural", "language": "ro", "name": "Alina (Romania)", "gender": "female", "age_group": "adult", "accent": "Romania", "provider": "edge_tts"},
    {"voice_id": "ro-RO-AndreiNeural", "language": "ro", "name": "Andrei (Romania)", "gender": "male", "age_group": "adult", "accent": "Romania", "provider": "edge_tts"},
    # Bulgarian
    {"voice_id": "bg-BG-KalinaNeural", "language": "bg", "name": "Kalina (Bulgaria)", "gender": "female", "age_group": "adult", "accent": "Bulgaria", "provider": "edge_tts"},
    {"voice_id": "bg-BG-BorislavNeural", "language": "bg", "name": "Borislav (Bulgaria)", "gender": "male", "age_group": "adult", "accent": "Bulgaria", "provider": "edge_tts"},
    # Croatian
    {"voice_id": "hr-HR-GabrijelaNeural", "language": "hr", "name": "Gabrijela (Croatia)", "gender": "female", "age_group": "adult", "accent": "Croatia", "provider": "edge_tts"},
    {"voice_id": "hr-HR-SreckoNeural", "language": "hr", "name": "Srecko (Croatia)", "gender": "male", "age_group": "adult", "accent": "Croatia", "provider": "edge_tts"},
    # Serbian
    {"voice_id": "sr-RS-SophieNeural", "language": "sr", "name": "Sophie (Serbia)", "gender": "female", "age_group": "adult", "accent": "Serbia", "provider": "edge_tts"},
    {"voice_id": "sr-RS-NicholasNeural", "language": "sr", "name": "Nicholas (Serbia)", "gender": "male", "age_group": "adult", "accent": "Serbia", "provider": "edge_tts"},
    # Slovak
    {"voice_id": "sk-SK-ViktoriaNeural", "language": "sk", "name": "Viktoria (Slovakia)", "gender": "female", "age_group": "adult", "accent": "Slovakia", "provider": "edge_tts"},
    {"voice_id": "sk-SK-LukasNeural", "language": "sk", "name": "Lukas (Slovakia)", "gender": "male", "age_group": "adult", "accent": "Slovakia", "provider": "edge_tts"},
    # Slovenian
    {"voice_id": "sl-SI-PetraNeural", "language": "sl", "name": "Petra (Slovenia)", "gender": "female", "age_group": "adult", "accent": "Slovenia", "provider": "edge_tts"},
    {"voice_id": "sl-SI-RokNeural", "language": "sl", "name": "Rok (Slovenia)", "gender": "male", "age_group": "adult", "accent": "Slovenia", "provider": "edge_tts"},
    # Estonian
    {"voice_id": "et-EE-AnuNeural", "language": "et", "name": "Anu (Estonia)", "gender": "female", "age_group": "adult", "accent": "Estonia", "provider": "edge_tts"},
    {"voice_id": "et-EE-KertNeural", "language": "et", "name": "Kert (Estonia)", "gender": "male", "age_group": "adult", "accent": "Estonia", "provider": "edge_tts"},
    # Latvian
    {"voice_id": "lv-LV-EveritaNeural", "language": "lv", "name": "Everita (Latvia)", "gender": "female", "age_group": "adult", "accent": "Latvia", "provider": "edge_tts"},
    {"voice_id": "lv-LV-NilsNeural", "language": "lv", "name": "Nils (Latvia)", "gender": "male", "age_group": "adult", "accent": "Latvia", "provider": "edge_tts"},
    # Lithuanian
    {"voice_id": "lt-LT-OnaNeural", "language": "lt", "name": "Ona (Lithuania)", "gender": "female", "age_group": "adult", "accent": "Lithuania", "provider": "edge_tts"},
    {"voice_id": "lt-LT-LeonasNeural", "language": "lt", "name": "Leonas (Lithuania)", "gender": "male", "age_group": "adult", "accent": "Lithuania", "provider": "edge_tts"},
    # Ukrainian
    {"voice_id": "uk-UA-PolinaNeural", "language": "uk", "name": "Polina (Ukraine)", "gender": "female", "age_group": "adult", "accent": "Ukraine", "provider": "edge_tts"},
    {"voice_id": "uk-UA-OstapNeural", "language": "uk", "name": "Ostap (Ukraine)", "gender": "male", "age_group": "adult", "accent": "Ukraine", "provider": "edge_tts"},
    # Greek
    {"voice_id": "el-GR-AthinaNeural", "language": "el", "name": "Athina (Greece)", "gender": "female", "age_group": "adult", "accent": "Greece", "provider": "edge_tts"},
    {"voice_id": "el-GR-NestorasNeural", "language": "el", "name": "Nestoras (Greece)", "gender": "male", "age_group": "adult", "accent": "Greece", "provider": "edge_tts"},
    # Hebrew
    {"voice_id": "he-IL-HilaNeural", "language": "he", "name": "Hila (Israel)", "gender": "female", "age_group": "adult", "accent": "Israel", "provider": "edge_tts"},
    {"voice_id": "he-IL-AvriNeural", "language": "he", "name": "Avri (Israel)", "gender": "male", "age_group": "adult", "accent": "Israel", "provider": "edge_tts"},
    # Thai
    {"voice_id": "th-TH-AcharaNeural", "language": "th", "name": "Achara (Thailand)", "gender": "female", "age_group": "adult", "accent": "Thailand", "provider": "edge_tts"},
    {"voice_id": "th-TH-PremwadeeNeural", "language": "th", "name": "Premwadee (Thailand)", "gender": "female", "age_group": "young_adult", "accent": "Thailand", "provider": "edge_tts"},
    {"voice_id": "th-TH-NiwatNeural", "language": "th", "name": "Niwat (Thailand)", "gender": "male", "age_group": "adult", "accent": "Thailand", "provider": "edge_tts"},
    # Vietnamese
    {"voice_id": "vi-VN-HoaiMyNeural", "language": "vi", "name": "HoaiMy (Vietnam)", "gender": "female", "age_group": "adult", "accent": "Vietnam", "provider": "edge_tts"},
    {"voice_id": "vi-VN-NamMinhNeural", "language": "vi", "name": "NamMinh (Vietnam)", "gender": "male", "age_group": "adult", "accent": "Vietnam", "provider": "edge_tts"},
    # Indonesian
    {"voice_id": "id-ID-GadisNeural", "language": "id", "name": "Gadis (Indonesia)", "gender": "female", "age_group": "adult", "accent": "Indonesia", "provider": "edge_tts"},
    {"voice_id": "id-ID-ArdiNeural", "language": "id", "name": "Ardi (Indonesia)", "gender": "male", "age_group": "adult", "accent": "Indonesia", "provider": "edge_tts"},
    # Malay
    {"voice_id": "ms-MY-YasminNeural", "language": "ms", "name": "Yasmin (Malaysia)", "gender": "female", "age_group": "adult", "accent": "Malaysia", "provider": "edge_tts"},
    {"voice_id": "ms-MY-OsmanNeural", "language": "ms", "name": "Osman (Malaysia)", "gender": "male", "age_group": "adult", "accent": "Malaysia", "provider": "edge_tts"},
    # Filipino/Tagalog
    {"voice_id": "fil-PH-BlessicaNeural", "language": "tl", "name": "Blessica (Philippines)", "gender": "female", "age_group": "adult", "accent": "Philippines", "provider": "edge_tts"},
    {"voice_id": "fil-PH-AngeloNeural", "language": "tl", "name": "Angelo (Philippines)", "gender": "male", "age_group": "adult", "accent": "Philippines", "provider": "edge_tts"},
]


async def seed_voices(db: AsyncSession):
    """Seed available voices into the database"""
    print("Seeding available voices...")
    
    for voice_data in EDGE_TTS_VOICES:
        # Check if voice exists
        result = await db.execute(
            select(AvailableVoice).where(
                AvailableVoice.provider == voice_data["provider"],
                AvailableVoice.voice_id == voice_data["voice_id"],
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            for key, value in voice_data.items():
                if key != "provider" and key != "voice_id":
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
        else:
            print(f"  Creating voice {voice_data['voice_id']}...")
            voice = AvailableVoice(
                **voice_data,
                description=f'{voice_data["name"]} - {voice_data.get("accent", "")} accent',
                supports_ssml=True,
                supports_emotion=False,
                max_length=5000,
                is_premium=False,
                is_active=True,
            )
            db.add(voice)
    
    await db.commit()
    print("Voices seeded successfully!")


async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        await seed_voices(db)


if __name__ == "__main__":
    asyncio.run(main())