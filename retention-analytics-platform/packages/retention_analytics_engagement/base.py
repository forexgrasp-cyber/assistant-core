"""Base engagement service with self-registration into the ServiceRegistry.

Builds on the canonical ``shared.base.base_service.BaseService`` so platform
services share the canonical contract (dry-run, tenant scoping, cost
tracking) instead of re-implementing it.
"""

from __future__ import annotations

from typing import Any

import structlog
from retention_analytics_core.service_base import CanonicalService

logger = structlog.get_logger(__name__)


class EngagementService(CanonicalService):
    """Base class for engagement services.

    Subclasses call ``register`` with the platform ``ServiceRegistry`` at
    startup, exposing named actions that workflows can invoke.
    """

    def __init__(self, name: str, registry: Any, version: str = "0.1.0") -> None:
        super().__init__(name, registry, version)


__all__ = ["EngagementService"]
