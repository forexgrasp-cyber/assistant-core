"""Assistant base class and configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AssistantConfig:
    """Configuration for an assistant instance."""
    assistant_id: str
    tenant_id: str
    type: str  # "personal" or "business"
    name: str
    vertical: str | None = None
    system_prompt: str | None = None
    connectors: list[str] = field(default_factory=list)
    persona_name: str = "JARVIS"
    persona_style: str = "professional, concise, proactive"
    voice_enabled: bool = True
    language: str = "en"
    # Business-specific
    phone: str | None = None
    widget_embed: bool = False
    billing_tier: str = "starter"
    vertical_prompt: str | None = None
    calendar_sync: bool = False
    whatsapp_enabled: bool = False
    business_hours: dict = field(default_factory=dict)
    # Personal-specific
    hotkey: str = "ctrl+shift+j"
    tray_enabled: bool = True
    scheduler_enabled: bool = True


class Assistant:
    """Base assistant class - wraps all core components."""

    def __init__(
        self,
        config: AssistantConfig,
        agent,
        voice_manager,
        rag_manager,
        persona_manager,
        memory_store,
        tool_registry,
    ):
        self.config = config
        self.agent = agent
        self.voice = voice_manager
        self.rag = rag_manager
        self.persona = persona_manager
        self.memory = memory_store
        self.tools = tool_registry

    async def chat(
        self,
        message: str,
        session_id: str | None = None,
        use_rag: bool = True,
        use_tools: bool = True,
    ):
        """Chat with the assistant."""
        return await self.agent.chat(
            message=message,
            session_id=session_id,
            use_rag=use_rag,
            use_tools=use_tools,
        )

    async def stream_chat(
        self,
        message: str,
        session_id: str | None = None,
        use_rag: bool = True,
        use_tools: bool = True,
    ):
        """Stream chat response."""
        async for chunk in self.agent.stream_chat(
            message=message,
            session_id=session_id,
            use_rag=use_rag,
            use_tools=use_tools,
        ):
            yield chunk

    async def handle_voice(self, audio_bytes: bytes) -> dict:
        """Handle voice input."""
        transcript = await self.voice.transcribe(audio_bytes)
        if not transcript:
            return {"error": "No speech detected"}

        response = await self.chat(transcript)
        audio = await self.voice.synthesize(response.get("response", ""))

        return {
            "transcript": transcript,
            "response": response.get("response", ""),
            "audio": audio,
        }

    def get_config(self) -> dict:
        """Get assistant configuration as dict."""
        return {
            "assistant_id": self.config.assistant_id,
            "tenant_id": self.config.tenant_id,
            "type": self.config.type,
            "name": self.config.name,
            "vertical": self.config.vertical,
            "voice_enabled": self.config.voice_enabled,
        }