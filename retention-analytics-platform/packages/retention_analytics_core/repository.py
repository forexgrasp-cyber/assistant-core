"""Durable, tenant-isolated storage for platform services.

PRODUCTION_STANDARDS.md §5.2 forbids storing user data in module-level
dicts. This module wraps the canonical tenant-isolated repository
(``shared.database.persistence_service.TenantIsolatedRepository``) so every
platform service persists to disk, scoped to the tenant that owns the data.

The repository is created per ``(entity_name, tenant_id)`` pair, so one
service instance can serve many tenants without leaking data between them.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from retention_analytics_shared_config import get_settings
from shared.database.persistence_service import TenantIsolatedRepository

__all__ = [
    "data_root",
    "new_id",
    "repository_for",
]


def data_root() -> Path:
    """Return the platform data root, creating it when needed."""
    path = Path(get_settings().data_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def new_id(prefix: str) -> str:
    """Return a collision-resistant, human-readable identifier."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def repository_for(entity_name: str, tenant_id: str) -> TenantIsolatedRepository[dict[str, Any]]:
    """Return a tenant-isolated repository for ``entity_name``.

    Files are written under ``<data_dir>/<entity_name>/<tenant_id>/`` so a
    tenant can never read another tenant's records.
    """
    return TenantIsolatedRepository(
        entity_name=entity_name,
        data_dir=data_root() / entity_name,
        tenant_id=tenant_id,
    )
