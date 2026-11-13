"""Assistant Factory - creates assistant instances from configuration."""

from __future__ import annotations

from typing import Any

from app.core.agent import create_assistant_agent, AssistantConfig as AgentConfig
from app.core.voice import create_voice_manager
from app.core.rag import create_rag_manager
from app.core.persona import create_persona_manager
from app.core.memory import create_memory_store
from app.core.tools import create_tool_registry
from app.connectors import get_connector, list_connectors
from .base import Assistant, AssistantConfig


async def create_assistant(
    config: AssistantConfig,
    ollama,
    rag_service,
    data_dir: str,
) -> Assistant:
    """Create an assistant instance from configuration."""

    # Create tool registry
    tool_registry = create_tool_registry(data_dir)

    # Create agent
    agent_config = AgentConfig(
        assistant_id=config.assistant_id,
        tenant_id=config.tenant_id,
        type=config.type,
        name=config.name,
        vertical=config.vertical,
        system_prompt=config.system_prompt,
        connectors=config.connectors,
        persona_name=config.persona_name,
        persona_style=config.persona_style,
        voice_enabled=config.voice_enabled,
    )
    agent = create_assistant_agent(agent_config, ollama, rag_service, create_tool_registry(data_dir))

    # Create voice manager
    voice_manager = create_voice_manager(
        elevenlabs_api_key=None,  # Would come from config/env
    )

    # Create RAG manager
    rag_manager = create_rag_manager(rag_service)

    # Create persona manager
    persona_manager = create_persona_manager(
        data_dir=data_dir,
        name=config.persona_name,
        style=config.persona_style,
    )

    # Create memory store
    memory_store = create_memory_store(data_dir, rag_service, config.tenant_id, config.assistant_id)

    # Create tool registry
    tool_registry = create_tool_registry(data_dir)

    # Initialize connectors
    connectors = {}
    for conn_name in config.connectors:
        conn = get_connector(conn_name)
        if conn and await conn.authenticate():
            connectors[conn_name] = conn

    return Assistant(
        config=config,
        agent=agent,
        voice_manager=voice_manager,
        rag_manager=rag_manager,
        persona_manager=persona_manager,
        memory_store=memory_store,
        tool_registry=tool_registry,
    )


def create_assistant_from_config(config_dict: dict, ollama, rag_service, data_dir: str) -> Assistant:
    """Create assistant from config dictionary."""
    config = AssistantConfig(**config_dict)
    return create_assistant(config, ollama, rag_service, data_dir)