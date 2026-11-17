"""Authentication and RBAC helpers for the platform.

Resolves the current principal from a bearer token and enforces role-based
permissions at the API boundary.

Production behaviour (PRODUCTION_STANDARDS.md L6):

* the signing secret is resolved through the canonical secret manager, never
  hardcoded — there is no default secret anywhere in this module;
* tokens are validated (signature, expiry, subject) and rejected when they
  do not carry a tenant;
* when no secret is configured the platform refuses to authenticate outside
  development, so a misconfigured deployment fails closed instead of
  accepting any token.

Development mode (no secret configured, ``ENVIRONMENT != production``) keeps
a demo principal so the frontend can be exercised locally.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from retention_analytics_shared_config import PlatformSettings

from retention_analytics_core.permissions import PermissionService
from retention_analytics_core.tenancy import DEFAULT_TENANT

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """Resolved current request principal."""

    def __init__(self, user_id: str, tenant_id: str, role: str) -> None:
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role

    def can(self, action: str) -> bool:
        return PermissionService(self.role, self.tenant_id).allowed(action)


def _settings() -> PlatformSettings:
    from retention_analytics_shared_config import get_settings

    settings: PlatformSettings = get_settings()
    return settings


def _secret() -> str | None:
    """Resolve the JWT signing secret through the canonical secret manager."""
    from retention_analytics_shared_config import get_settings

    settings = get_settings()
    if settings.jwt_secret:
        return settings.jwt_secret
    try:
        from shared.production.secrets import get_secret

        return get_secret("JWT_SECRET")
    except ImportError:  # pragma: no cover - canonical package always present
        return None


def resolve_jwt_secret() -> str | None:
    """Return the configured JWT signing secret, or ``None`` when unset."""
    return _secret()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentUser:
    """Resolve the current user from credentials.

    When a JWT secret (or WorkOS JWKS) is configured, the bearer token is
    validated. When no secret is configured, only a non-production
    environment falls back to a demo principal — production raises 503
    because a deployment without credentials is not safe to serve.
    """
    settings = _settings()

    if credentials is None:
        if settings.is_production:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return CurrentUser(
            user_id="demo-user",
            tenant_id=DEFAULT_TENANT,
            role="admin",
        )

    token = credentials.credentials

    secret = _secret()
    if secret:
        return _validate_jwt(token, secret, str(settings.jwt_algorithm))

    if settings.workos_client_id and settings.workos_api_key:
        return await _validate_workos_jwt(token, settings)

    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )

    # Dev mode: no secret configured -> accept any token as demo admin
    return CurrentUser(
        user_id="demo-user",
        tenant_id=DEFAULT_TENANT,
        role="admin",
    )


def _validate_jwt(token: str, secret: str, algorithm: str) -> CurrentUser:
    """Validate an HS/RS JWT and build the principal.

    Uses the canonical token format shared across the fleet:
    ``{"sub": user_id, "tenant_id": ..., "role": ..., "exp": ...}``.
    """
    try:
        import jwt as pyjwt
    except ImportError as exc:  # pragma: no cover - dependency always present
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT validation unavailable",
        ) from exc

    try:
        payload = pyjwt.decode(token, secret, algorithms=[algorithm])
    except pyjwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = str(payload.get("sub") or "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tenant_id = str(payload.get("tenant_id") or "")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing tenant",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = str(payload.get("role") or "viewer")
    return CurrentUser(user_id=user_id, tenant_id=tenant_id, role=role)


async def _validate_workos_jwt(token: str, settings: PlatformSettings) -> CurrentUser:
    """Validate a WorkOS-issued JWT using JWKS."""
    import httpx

    try:
        import jwt as pyjwt
    except ImportError as exc:  # pragma: no cover - dependency always present
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT validation unavailable",
        ) from exc

    jwks_url = f"https://api.workos.com/sso/jwks/{settings.workos_client_id}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            jwks = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity provider unavailable",
        ) from exc

    unverified = pyjwt.get_unverified_header(token)
    kid = unverified.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing kid",
        )

    key = None
    for candidate in jwks.get("keys", []):
        if candidate.get("kid") == kid:
            key = candidate
            break
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: key not found",
        )

    from jwt import PyJWK

    public_key = PyJWK(key, algorithm="RS256").key

    try:
        payload = pyjwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.workos_client_id,
        )
    except pyjwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        ) from exc

    user_id = str(payload.get("sub") or "")
    tenant_id = str(payload.get("tenant_id") or "")
    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject or tenant",
        )

    role = str(payload.get("role") or "viewer")
    return CurrentUser(user_id=user_id, tenant_id=tenant_id, role=role)


def require_permission(action: str):
    """Dependency factory: requires the current user to be allowed ``action``."""

    def _checker(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if not user.can(action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {action}",
            )
        return user

    return _checker


__all__ = [
    "CurrentUser",
    "bearer_scheme",
    "get_current_user",
    "require_permission",
]
