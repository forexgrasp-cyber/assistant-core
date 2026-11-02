"""
Authentication — thin adapter over the canonical shared auth stack.

All credential hashing, JWT issuing/validation, refresh-token rotation,
and email verification logic lives in ``shared.auth.jwt_service``
(_shared-canonical-services_). This module re-exports that surface and
adds only marketplace-specific role/profile linkage.

Canonical pieces used:
    JWTAuthService      register/login/verify_email/refresh/logout
    get_auth_service()  singleton accessor
    get_current_user    FastAPI dependency (Bearer JWT -> user dict)
    require_license     FastAPI dependency for license-key gating
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from marketplace.database import db_session, get_session
from marketplace.database.repositories import UserRepository
from marketplace.models import UserRole, UserStatus
from shared.auth.jwt_service import (
    JWTAuthService,
    get_auth_service,
    get_current_license,
    get_current_user,
    require_license,
)

__all__ = [
    "JWTAuthService",
    "get_auth_service",
    "get_current_license",
    "get_current_user",
    "require_license",
    "ensure_platform_login_user",
    "get_current_user_with_role",
    "require_role",
    "require_admin",
]


async def ensure_platform_login_user(
    user_id: str,
    email: str,
    session: AsyncSession,
    role: UserRole = UserRole.CLIENT,
) -> None:
    """Create the marketplace-side User row for an auth user (idempotent)."""
    await UserRepository(session).ensure_platform_user(
        user_id=user_id, email=email, role=role
    )


async def get_current_user_with_role(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    """Canonical auth + marketplace role enrichment.

    Returns the auth user dict with ``role`` (admin/client/va). Registers
    the platform User row lazily on first authenticated request.
    """
    from marketplace.database.repositories import UserRepository

    repo = UserRepository(session)
    platform_user = await repo.get_by_id(user["user_id"])
    if platform_user is None:
        platform_user = await repo.ensure_platform_user(
            user_id=user["user_id"], email=user["email"]
        )
    if platform_user.status not in (UserStatus.ACTIVE, UserStatus.PENDING):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended",
        )
    role = UserRole(platform_user.role) if not isinstance(platform_user.role, UserRole) else platform_user.role
    return {**user, "role": role.value, "status": platform_user.status.value}


def require_role(*allowed: UserRole) -> Any:
    """Role-checking dependency factory on top of canonical auth."""

    async def _checker(
        user: dict = Depends(get_current_user_with_role),
    ) -> dict[str, Any]:
        user_role = user.get("role", UserRole.CLIENT.value)
        if user_role not in [r.value for r in allowed]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {[r.value for r in allowed]}",
            )
        return user

    return _checker


require_admin = require_role(UserRole.ADMIN)
