"""Assistant Registry - manages assistant instances per tenant."""

from __future__ import annotations

from typing import Any

from .base import Assistant, AssistantConfig


class AssistantRegistry:
    """Registry for managing assistant instances per tenant."""

    def __init__(self):
        self._assistants: dict[str, dict[str, Assistant]] = {}  # tenant_id -> {assistant_id: Assistant}

    def register(self, assistant: Assistant) -> None:
        """Register an assistant instance."""
        tenant_id = assistant.config.tenant_id
        if tenant_id not in self._assistants:
            self._assistants[tenant_id] = {}
        self._assistants[tenant_id][assistant.config.assistant_id] = assistant

    def unregister(self, tenant_id: str, assistant_id: str) -> bool:
        """Unregister an assistant."""
        if tenant_id in self._assistants and assistant_id in self._assistants[tenant_id]:
            del self._assistants[tenant_id][assistant_id]
            return True
        return False

    def get(self, tenant_id: str, assistant_id: str) -> Assistant | None:
        """Get an assistant by tenant and ID."""
        return self._assistants.get(tenant_id, {}).get(assistant_id)

    def list_for_tenant(self, tenant_id: str) -> list[Assistant]:
        """List all assistants for a tenant."""
        return list(self._assistants.get(tenant_id, {}).values())

    def list_all(self) -> list[Assistant]:
        """List all assistants across all tenants."""
        all_assistants = []
        for tenant_assistants in self._assistants.values():
            all_assistants.extend(tenant_assistants.values())
        return all_assistants

    def get_by_type(self, tenant_id: str, type: str) -> list[Assistant]:
        """Get assistants of a specific type for a tenant."""
        return [
            a for a in self._assistants.get(tenant_id, {}).values()
            if a.config.type == type
        ]


# Global registry instance
_registry = AssistantRegistry()


def get_registry() -> AssistantRegistry:
    return _registry


__all__ = ["AssistantRegistry", "get_registry"]