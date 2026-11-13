"""Tenant model and manager."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


class Tenant(BaseModel):
    """Tenant model."""
    id: str
    name: str
    owner: str
    plan: str = "starter"  # starter, pro, enterprise
    enabled: bool = True
    settings: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class TenantManager:
    """Manages tenants and their assistants."""

    def __init__(self):
        self._tenants: dict[str, Tenant] = {}

    def create(self, tenant: Tenant) -> Tenant:
        self._tenants[tenant.id] = tenant
        return tenant

    def get(self, tenant_id: str) -> Tenant | None:
        return self._tenants.get(tenant_id)

    def update(self, tenant_id: str, **kwargs) -> Tenant | None:
        tenant = self._tenants.get(tenant_id)
        if tenant:
            for k, v in kwargs.items():
                setattr(tenant, k, v)
        return tenant

    def delete(self, tenant_id: str) -> bool:
        if tenant_id in self._tenants:
            del self._tenants[tenant_id]
            return True
        return False

    def list_all(self) -> list[Tenant]:
        return list(self._tenants.values())

    def get_by_owner(self, owner: str) -> list[Tenant]:
        return [t for t in self._tenants.values() if t.owner == owner]