"""Voice Manager - handles TTS, STT, and voice routing."""

from __future__ import annotations

import base64
import asyncio
from typing import Any

# Shared packages
from shared.ai_voice import AIVoiceRouter, configure as configure_voice
from shared.tts import TTSService
from shared.whisper import WhisperService


class VoiceManager:
    """Manages voice I/O: TTS synthesis, STT transcription, and Twilio webhook handling."""

    def __init__(
        self,
        tts_service: TTSService | None = None,
        whisper_service: WhisperService | None = None,
        elevenlabs_api_key: str | None = None,
    ):
        self.tts = tts_service or (TTSService(api_key=elevenlabs_api_key) if elevenlabs_api_key else None)
        self.whisper = whisper_service
        self.elevenlabs_api_key = elevenlabs_api_key

        # Configure shared.ai_voice router if TTS available
        if self.tts:
            from shared.ai_voice import configure
            configure(tts=self.tts)

    async def synthesize(self, text: str) -> bytes:
        """Synthesize speech from text."""
        if not self.tts:
            return b""
        result = await self.tts.synthesize(text)
        return result.get("audio", b"") if isinstance(result, dict) else result

    async def synthesize_url(self, text: str) -> str | None:
        """Get URL for synthesized audio."""
        if self.tts and hasattr(self.tts, "synthesize_url"):
            return self.tts.synthesize_url(text)
        return None

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio using Whisper."""
        if not self.whisper:
            return ""
        try:
            result = await self.whisper.transcribe(audio_bytes)
            return result.get("text", "") if isinstance(result, dict) else str(result)
        except Exception:
            return ""

    async def handle_twilio_webhook(self, form_data: dict) -> dict:
        """Handle Twilio voice webhook - returns TwiML response."""
        from shared.ai_voice.router import router
        from fastapi import Request
        from fastapi.responses import Response

        # This would integrate with the shared.ai_voice router
        # For now, return basic TwiML
        from shared.ai_voice.twilio import twiml_say
        return Response(content=twiml_say("Hello, how can I help you?"), media_type="application/xml")

    async def handle_websocket_voice(self, websocket, session_id: str):
        """Handle real-time voice conversation over WebSocket."""
        await websocket.accept()

        try:
            while True:
                data = await websocket.receive_json()
                audio_b64 = data.get("audio")
                if not audio_b64:
                    continue

                # Decode audio
                import base64
                audio_bytes = base64.b64decode(audio_b64)

                # Simple VAD (energy-based)
                if not self._has_speech(audio_bytes):
                    continue

                # STT
                transcript = await self.transcribe(audio_bytes)
                if not transcript:
                    continue

                # Send transcript
                await websocket.send_json({"type": "transcript", "text": transcript})

                # Agent response would be generated here
                # For now, echo back
                response = f"I heard: {transcript}"
                audio = await self.synthesize(response)
                audio_b64 = base64.b64encode(audio).decode()

                await websocket.send_json({
                    "type": "response",
                    "text": response,
                    "audio": audio_b64,
                })
        except Exception:
            pass

    def _has_speech(self, audio_bytes: bytes) -> bool:
        """Simple energy-based VAD."""
        import numpy as np
        if len(audio_bytes) < 100:
            return False
        audio = np.frombuffer(audio_bytes, dtype=np.int16)
        energy = np.mean(np.abs(audio))
        return energy > 500


def create_voice_manager(
    elevenlabs_api_key: str | None = None,
    whisper_service: WhisperService | None = None,
) -> VoiceManager:
    """Factory to create voice manager."""
    tts = TTSService(api_key=elevenlabs_api_key) if elevenlabs_api_key else None
    return VoiceManager(tts_service=tts, whisper_service=whisper_service, elevenlabs_api_key=elevenlabs_api_key)