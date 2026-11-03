"""Role-based access control for the platform.

Roles map to permissions on entities and workflow actions. Services and the
API gateway share this model so authorization is consistent end-to-end.
"""

from __future__ import annotations

from dataclasses import dataclass


class Role(str):
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


_PERMISSIONS: dict[str, set[str]] = {
    Role.ADMIN: {
        "entities.*",
        "workflows.*",
        "services.*",
        "billing.*",
        "reports.*",
        "settings.*",
    },
    Role.MANAGER: {
        "entities.read",
        "entities.write",
        "workflows.read",
        "workflows.write",
        "services.invoke",
        "reports.read",
        "reports.write",
    },
    Role.OPERATOR: {
        "entities.read",
        "workflows.read",
        "services.invoke",
        "reports.read",
    },
    Role.VIEWER: {
        "entities.read",
        "workflows.read",
        "reports.read",
    },
}


@dataclass
class PermissionService:
    """Checks whether a user role may perform an action on a resource."""

    def __init__(self, role: str, tenant_id: str) -> None:
        self.role = role
        self.tenant_id = tenant_id

    def allowed(self, action: str) -> bool:
        perms = _PERMISSIONS.get(self.role, set())
        if action in perms:
            return True
        # Support wildcard matching: "entities.read" matches "entities.*"
        prefix = action.rsplit(".", 1)[0] + ".*" if "." in action else ""
        return prefix in perms


__all__ = ["Role", "PermissionService"]
