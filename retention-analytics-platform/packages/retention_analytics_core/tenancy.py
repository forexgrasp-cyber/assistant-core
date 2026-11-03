"""Tenant scoping and cross-tenant prevention.

PRODUCTION_STANDARDS.md §5.1 makes tenant isolation a launch blocker: a
tenant must never read or write another tenant's data, and the tenant a
request acts on is derived from the *authenticated principal*, never from a
client-supplied body field or query parameter.

This module provides:

* :func:`resolve_tenant` — the single source of truth for the effective
  tenant of a request.
* :func:`assert_same_tenant` — rejects a cross-tenant access attempt.
* :func:`tenant_context` — a context manager that publishes the effective
  tenant to the canonical shared tenant context so canonical services
  (``shared.multitenancy``) see the same tenant as the platform.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from fastapi import HTTPException, status

from retention_analytics_core.middleware import get_tenant_id

__all__ = [
    "DEFAULT_TENANT",
    "assert_same_tenant",
    "resolve_tenant",
    "tenant_context",
]

# The seed tenant used by the demo/frontend before authentication is wired.
DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"


def resolve_tenant(
    principal_tenant_id: str | None,
    requested_tenant_id: str | None = None,
    header_tenant_id: str | None = None,
) -> str:
    """Return the tenant a request may act on.

    The authenticated principal's tenant always wins. A tenant supplied by
    the client (body, query string or ``X-Tenant-Id`` header) is only
    honoured when it matches the principal's tenant; otherwise the request
    is rejected with ``403``.

    In development mode (no configured secret, i.e. no real principal) the
    requested tenant is accepted so the platform can be exercised locally —
    production always fails closed.
    """
    from retention_analytics_shared_config import get_settings

    settings = get_settings()

    requested = (requested_tenant_id or "").strip()
    header = (header_tenant_id or "").strip()
    principal = (principal_tenant_id or "").strip()

    if not principal:
        # No authenticated principal: only dev mode may fall back.
        if settings.is_production:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authenticated tenant required",
            )
        return requested or header or DEFAULT_TENANT

    if requested and requested != principal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied",
        )
    if header and header != principal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied",
        )
    return principal


def assert_same_tenant(resource_tenant_id: str, principal_tenant_id: str) -> None:
    """Raise ``403`` when a resource belongs to a different tenant."""
    if resource_tenant_id != principal_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied",
        )


@contextmanager
def tenant_context(tenant_id: str, tenant_slug: str = "") -> Iterator[None]:
    """Publish the effective tenant to the canonical shared tenant context."""
    try:
        from shared.multitenancy.context import set_current_tenant

        set_current_tenant(tenant_id=tenant_id, tenant_slug=tenant_slug or tenant_id)
    except ImportError:  # pragma: no cover - canonical package always present
        pass
    try:
        yield
    finally:
        try:
            from shared.multitenancy.context import clear_current_tenant

            clear_current_tenant()
        except ImportError:  # pragma: no cover - canonical package always present
            pass


def current_tenant_id() -> str:
    """Return the tenant published by the tenant middleware, if any."""
    return get_tenant_id()


def tenant_scoped(payload: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    """Return ``payload`` with the tenant forced to ``tenant_id``.

    Used when forwarding a request payload to a service action so a
    downstream service can never be tricked into acting on another tenant.
    """
    scoped = dict(payload)
    scoped["tenant_id"] = tenant_id
    return scoped
