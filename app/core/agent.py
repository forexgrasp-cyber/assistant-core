"""Assistant Agent - thin adapter over the UNIVERSAL agent service.

Refactored 2026-11-16: assistant-core no longer has its own agent wiring.
``AssistantAgent`` is an ``AssistantConfig`` translated into an
``AgentDefinition`` and built by ``shared.agent_runtime.universal.create_agent``
— the same factory callagent, the vertical receptionists and the tutor use.
Capabilities come from the config: personal assistants get
chat/rag_kb/memory/persona/connectors (+ sandbox tools), business assistants
get the vertical's receptionist capability set.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

# Shared packages
from shared.agent_runtime import LocalAIAgent, ToolRegistry, LocalAgentResult
from shared.agent_runtime.universal import AgentDefinition, UniversalAgent, create_agent
from shared.llm.ollama_adapter import OllamaAdapter
from shared.rag import RAGService


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


def _capabilities_for(config: AssistantConfig) -> tuple[str, ...]:
    """Map an AssistantConfig to universal capabilities."""
    caps = ["chat", "rag_kb"]
    if config.type == "personal":
        caps += ["memory", "persona", "sandbox_tools"]
        if config.connectors:
            caps.append("connectors")
    else:
        # business assistants are receptionists: voice + booking + missed calls
        caps += ["voice", "booking", "missed_call_recovery", "web_widget"]
    if config.voice_enabled and "voice" not in caps:
        caps.append("voice")
    return tuple(caps)


class AssistantAgent:
    """Wrapper around the universal agent with assistant-specific configuration."""

    def __init__(
        self,
        config: AssistantConfig,
        ollama: OllamaAdapter,
        rag: RAGService,
        tool_registry: ToolRegistry,
        data_dir: str = "./data",
    ):
        self.config = config
        self.ollama = ollama
        self.rag = rag
        self.tool_registry = tool_registry

        definition = AgentDefinition(
            slug=config.assistant_id,
            name=config.name,
            kind="assistant" if config.type == "personal" else "receptionist",
            prompt=config.system_prompt or "",
            persona_name=config.persona_name,
            persona_style=config.persona_style,
            capabilities=_capabilities_for(config),
            vertical=config.vertical,
        )
        self.definition = definition
        self._universal: UniversalAgent = create_agent(
            definition,
            data_dir=data_dir,
            tenant_id=config.tenant_id,
            assistant_id=config.assistant_id,
            business_name=config.name,
            llm=ollama,
            rag=rag,
            tool_registry=tool_registry,
        )
        self.agent: LocalAIAgent = self._universal.agent
        self._system_prompt = self._universal.system_prompt()

    def _build_system_prompt(self) -> str:
        """Kept for backwards compatibility — the universal agent composes it."""
        return self._system_prompt

    async def chat(
        self,
        message: str,
        session_id: str | None = None,
        use_rag: bool = True,
        use_tools: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LocalAgentResult:
        """Chat with the assistant (delegates to the universal agent)."""
        session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"

        return await self.agent.chat(
            message=message,
            session_id=session_id,
            use_rag=use_rag,
            use_tools=use_tools,
            system_prompt=self._system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def stream_chat(
        self,
        message: str,
        session_id: str | None = None,
        use_rag: bool = True,
        use_tools: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        """Stream chat response."""
        async for chunk in self.agent.stream_chat(
            message=message,
            session_id=session_id,
            use_rag=use_rag,
            use_tools=use_tools,
            system_prompt=self._system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk

    def get_tools(self) -> list[str]:
        """Get available tools."""
        return self.tool_registry.list_tools() if self.tool_registry else []


def create_assistant_agent(
    config: AssistantConfig,
    ollama: OllamaAdapter,
    rag: RAGService,
    tool_registry: ToolRegistry,
    data_dir: str = "./data",
) -> AssistantAgent:
    """Factory function to create an assistant agent (universal factory underneath)."""
    return AssistantAgent(config, ollama, rag, tool_registry, data_dir=data_dir)
