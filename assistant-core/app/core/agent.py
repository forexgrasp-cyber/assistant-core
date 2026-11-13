"""Assistant Agent - wraps LocalAIAgent with assistant-specific logic."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

# Shared packages
from shared.agent_runtime import LocalAIAgent, ToolRegistry, LocalAgentResult
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


class AssistantAgent:
    """Wrapper around LocalAIAgent with assistant-specific configuration."""

    def __init__(self, config: AssistantConfig, ollama: OllamaAdapter, rag: RAGService, tool_registry: ToolRegistry):
        self.config = config
        self.ollama = ollama
        self.rag = rag
        self.tool_registry = tool_registry

        # Build system prompt
        system_prompt = self._build_system_prompt()

        self.agent = LocalAIAgent(
            llm_adapter=ollama,
            rag_service=rag,
            tool_registry=tool_registry,
        )

        self._system_prompt = system_prompt

    def _build_system_prompt(self) -> str:
        """Build the system prompt based on config."""
        base = f"You are {self.config.persona_name}, a {self.config.persona_style} AI assistant."

        if self.config.type == "personal":
            base += "\n\nYou help with personal productivity: email, calendar, notes, coding, research, tasks."
            base += "\nBe proactive: suggest next steps, summarize long content, anticipate needs."
        elif self.config.type == "business":
            base += f"\n\nYou are a {self.config.vertical or 'business'} receptionist."
            base += "\nHandle calls, book appointments, answer FAQs, recover missed leads."
            base += "\nBe warm, professional, and efficient. Never give advice outside your domain."

        if self.config.system_prompt:
            base += f"\n\nAdditional instructions: {self.config.system_prompt}"

        return base

    async def chat(
        self,
        message: str,
        session_id: str | None = None,
        use_rag: bool = True,
        use_tools: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LocalAgentResult:
        """Chat with the assistant."""
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
        session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"

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
) -> AssistantAgent:
    """Factory function to create an assistant agent."""
    return AssistantAgent(config, ollama, rag, tool_registry)