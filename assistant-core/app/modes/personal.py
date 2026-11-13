"""Personal Mode - JARVIS desktop assistant."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

from app.core.voice import VoiceManager

router = APIRouter(prefix="/personal", tags=["personal"])

# Desktop tray endpoint would be here
# WebSocket for chat
# Hotkey registration would be handled by desktop app


@router.get("/config")
async def get_personal_config():
    """Get personal mode configuration."""
    return {
        "mode": "personal",
        "features": {
            "desktop_tray": True,
            "hotkey": "ctrl+shift+j",
            "voice": True,
            "connectors": ["gmail", "calendar", "notion", "obsidian", "github", "slack"],
            "scheduler": True,
            "memory": True,
        },
        "persona": {
            "name": "JARVIS",
            "style": "professional, concise, proactive",
        },
    }


@router.websocket("/ws/chat/{session_id}")
async def personal_chat_ws(websocket: WebSocket, session_id: str):
    """WebSocket for personal chat."""
    await websocket.accept()
    # Would integrate with AssistantAgent
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            # Process with agent
            await websocket.send_json({"response": f"Personal: {message}"})
    except Exception:
        pass