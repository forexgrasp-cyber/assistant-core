"""Voice Router - handles voice calls via Twilio and WebSocket."""

from __future__ import annotations

import base64
import structlog
from typing import Any

from fastapi import APIRouter, Form, Header, Request
from fastapi.responses import Response

from shared.ai_voice import AIVoiceRouter, configure as configure_voice_router
from shared.ai_voice.twilio import twiml_say, twiml_play_say, validate_twilio_signature
from shared.ai_voice.config import settings as voice_settings

log = structlog.get_logger()

router = APIRouter(prefix="/voice", tags=["voice"])

# Configure shared.ai_voice router with TTS
# This would be done at startup with actual TTS service
# configure_voice_router(tts=tts_service)


@router.post("/webhook")
async def voice_webhook(
    request: Request,
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    SpeechResult: str | None = Form(None),
    x_twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
) -> Response:
    """Handle Twilio voice webhook."""
    identifier = From or CallSid or "unknown"

    # Verify Twilio signature
    if voice_settings.enable_signature_validation:
        form = await request.form()
        params = {k: v for k, v in form.items() if k != "X-Twilio-Signature"}
        url = str(request.url)
        if not validate_twilio_signature(url, params, x_twilio_signature or "", voice_settings.twilio_auth_token):
            return Response(content="Invalid signature", status_code=403)

    # Get or create AI voice router for this call
    ai_voice = AIVoiceRouter()

    # Handle speech result
    if SpeechResult:
        # Process with agent (would integrate with assistant)
        response_text = f"You said: {SpeechResult}. How can I help?"
    else:
        response_text = "Hello! How can I help you today?"

    # Use TTS if available
    if ai_voice._tts:
        try:
            audio_url = ai_voice._tts.synthesize_url(response_text)
            if audio_url:
                return Response(content=twiml_play_say(audio_url, response_text), media_type="application/xml")
        except Exception as exc:
            log.error("tts_failed", error=str(exc))

    return Response(content=twiml_say(response_text), media_type="application/xml")


@router.websocket("/ws/{session_id}")
async def websocket_voice(websocket, session_id: str):
    """WebSocket for real-time voice conversation."""
    from shared.ai_voice import AIVoiceRouter
    from shared.tts import TTSService
    from shared.whisper import WhisperService

    await websocket.accept()

    ai_voice = AIVoiceRouter()
    tts = TTSService()
    whisper = WhisperService()

    try:
        while True:
            data = await websocket.receive_json()
            audio_b64 = data.get("audio")
            if not audio_b64:
                continue

            # Decode audio
            import base64
            audio_bytes = base64.b64decode(audio_b64)

            # Simple VAD
            if not _has_speech(audio_bytes):
                continue

            # STT
            transcript = await whisper.transcribe(audio_bytes)
            if not transcript:
                continue

            await websocket.send_json({"type": "transcript", "text": transcript})

            # Agent response would go here
            response = f"I heard: {transcript}"
            audio = await tts.synthesize(response)
            audio_b64 = base64.b64encode(audio).decode()

            await websocket.send_json({
                "type": "response",
                "text": response,
                "audio": audio_b64,
            })
    except Exception:
        pass


def _has_speech(audio_bytes: bytes) -> bool:
    """Simple energy-based VAD."""
    import numpy as np
    if len(audio_bytes) < 100:
        return False
    audio = np.frombuffer(audio_bytes, dtype=np.int16)
    energy = np.mean(np.abs(audio))
    return energy > 500