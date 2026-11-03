"""Canonical service base for the platform.

PRODUCTION_STANDARDS.md L1 requires platform services to build on the
canonical ``shared.base.base_service.BaseService`` instead of re-implementing
the service contract. This module provides the platform flavour of that base:

* inherits the canonical :class:`BaseService` (dry-run, tenant, cost
  tracking, event emission);
* registers actions into the platform :class:`ServiceRegistry` so workflows
  can invoke them;
* returns the canonical :class:`ServiceResponse` envelope.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from shared.base.base_service import BaseService, ServiceResponse

from retention_analytics_core.service_registry import ServiceAction, ServiceRegistry

logger = structlog.get_logger(__name__)

__all__ = [
    "BaseService",
    "CanonicalService",
    "ServiceResponse",
]


class CanonicalService(BaseService):
    """Base class for every platform service.

    Subclasses expose named actions through :meth:`register_action` and
    publish them to the platform registry with :meth:`register`.
    """

    SERVICE_NAME = "canonical_service"
    __version__ = "2026.10"

    def __init__(
        self,
        name: str,
        registry: ServiceRegistry | None = None,
        version: str = "0.1.0",
        *,
        tenant_id: str | None = None,
        dry_run: bool = False,
    ) -> None:
        super().__init__(tenant_id=tenant_id, dry_run=dry_run)
        self.name = name
        self.registry = registry
        self.version = version
        self._actions: dict[str, ServiceAction] = {}

    def register_action(self, action_name: str, action: ServiceAction) -> None:
        self._actions[action_name] = action

    def register(
        self,
        subscribes_to: list | None = None,
        metadata: dict[str, Any] | None = None,
        service_type: str = "platform",
    ) -> None:
        """Register this service and all its actions with the platform registry."""
        if self.registry is None:
            raise ValueError(f"Service '{self.name}' has no registry to register with")
        self.registry.register(
            name=self.name,
            version=self.version,
            subscribes_to=subscribes_to or [],
            metadata={"type": service_type, **(metadata or {})},
        )
        for action_name, action in self._actions.items():
            self.registry.register_action(self.name, action_name, action)
        logger.info("platform.service.registered", service=self.name, actions=list(self._actions))

    async def invoke(self, action_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.registry is None:
            raise ValueError(f"Service '{self.name}' has no registry to invoke through")
        return await self.registry.invoke(self.name, action_name, payload)

    @staticmethod
    def ok(data: Any = None, **metadata: Any) -> dict[str, Any]:
        """Build a successful canonical response as a plain dict.

        The registry contract is a JSON object, so the canonical
        ``ServiceResponse`` envelope is unwrapped here.
        """
        response = ServiceResponse.ok(data, **metadata)
        payload: dict[str, Any] = {"success": response.success}
        if response.data is not None:
            payload["data"] = response.data
        if response.message:
            payload["message"] = response.message
        if response.metadata:
            payload["metadata"] = response.metadata
        return payload

    @staticmethod
    def fail(error: str, **metadata: Any) -> dict[str, Any]:
        """Build a failed canonical response as a plain dict."""
        response = ServiceResponse.fail(error, **metadata)
        payload: dict[str, Any] = {"success": response.success, "error": response.error}
        if response.metadata:
            payload["metadata"] = response.metadata
        return payload

    async def emit(self, event: str, **data: Any) -> None:
        """Emit a platform event through the canonical event bus."""
        await self._emit(event, **data)

    async def call(
        self,
        action: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Invoke ``action`` with the canonical retry/circuit-breaker policy."""
        from retention_analytics_core.canonical import get_adapters

        return await get_adapters().retry.execute(
            action, *args, circuit_breaker_name=self.name, **kwargs
        )
