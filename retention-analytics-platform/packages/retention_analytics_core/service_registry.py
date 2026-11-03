"""Service registry: the anti-silo integration point.

Services register themselves here with the actions they expose. The workflow
engine looks up registered services and invokes their actions as workflow
steps, so no service lives as a silo — every service is reachable from a
workflow or pipeline.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from retention_analytics_shared_types import EventType

ServiceAction = Callable[..., Awaitable[dict[str, Any]]]


@dataclass
class ServiceRegistration:
    name: str
    version: str
    actions: dict[str, ServiceAction] = field(default_factory=dict)
    subscribes_to: list[EventType] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ServiceRegistry:
    """Central registry of all platform services and their exposed actions.

    Services call ``register`` at import/startup time. Workflows and pipelines
    reference services by name and invoke actions through ``invoke``.
    """

    def __init__(self) -> None:
        self._services: dict[str, ServiceRegistration] = {}

    def register(
        self,
        name: str,
        version: str = "0.1.0",
        subscribes_to: list[EventType] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceRegistration:
        if name in self._services:
            raise ValueError(f"Service '{name}' already registered")
        reg = ServiceRegistration(
            name=name,
            version=version,
            subscribes_to=subscribes_to or [],
            metadata=metadata or {},
        )
        self._services[name] = reg
        return reg

    def register_action(self, service_name: str, action_name: str, action: ServiceAction) -> None:
        reg = self._services.get(service_name)
        if reg is None:
            raise KeyError(f"Service '{service_name}' not registered")
        reg.actions[action_name] = action

    def get(self, service_name: str) -> ServiceRegistration:
        reg = self._services.get(service_name)
        if reg is None:
            raise KeyError(f"Service '{service_name}' not registered")
        return reg

    def list_services(self) -> list[str]:
        return sorted(self._services.keys())

    async def invoke(
        self,
        service_name: str,
        action_name: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        reg = self.get(service_name)
        action = reg.actions.get(action_name)
        if action is None:
            raise KeyError(f"Action '{action_name}' not found on service '{service_name}'")
        return await action(payload)

    def subscribers_for(self, event_type: EventType) -> list[str]:
        """Return service names subscribed to the given event type."""
        return [
            name
            for name, reg in self._services.items()
            if event_type in reg.subscribes_to
        ]


__all__ = ["ServiceRegistry", "ServiceRegistration", "ServiceAction"]
