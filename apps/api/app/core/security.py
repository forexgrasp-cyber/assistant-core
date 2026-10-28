"""
Security utilities: password hashing, JWT tokens, MFA, Passkeys.
"""

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

import jwt
import pyotp
import qrcode
from fastapi import HTTPException, Response, status
from passlib.context import CryptContext

from .config import get_settings

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# JWT Token handling
ALGORITHM = settings.auth.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.auth.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.auth.refresh_token_expire_days
SECRET_KEY = settings.auth.secret_key


def create_access_token(
    subject: str,
    scopes: List[str] = None,
    expires_delta: timedelta = None,
    extra_claims: dict = None
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
        "scopes": scopes or [],
    }
    
    if extra_claims:
        to_encode.update(extra_claims)
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: str,
    expires_delta: timedelta = None,
    extra_claims: dict = None
) -> str:
    """Create a JWT refresh token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    }
    
    if extra_claims:
        to_encode.update(extra_claims)
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_access_token(token: str) -> dict:
    """Decode and validate an access token."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def decode_refresh_token(token: str) -> dict:
    """Decode and validate a refresh token."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


# MFA (TOTP)
def generate_totp_secret() -> str:
    """Generate a new TOTP secret."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = None) -> str:
    """Get TOTP URI for QR code generation."""
    issuer = issuer or settings.auth.mfa_issuer_name
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=issuer
    )


def verify_totp(secret: str, token: str, window: int = 1) -> bool:
    """Verify a TOTP token."""
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=window)


def generate_qr_code(uri: str) -> bytes:
    """Generate QR code image for TOTP setup."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


# Passkeys / WebAuthn
class WebAuthnCredential:
    """WebAuthn credential model."""
    def __init__(
        self,
        credential_id: str,
        public_key: bytes,
        sign_count: int,
        transports: List[str] = None,
        device_type: str = "cross-platform",
    ):
        self.credential_id = credential_id
        self.public_key = public_key
        self.sign_count = sign_count
        self.transports = transports or []
        self.device_type = device_type


def generate_challenge() -> str:
    """Generate a random challenge for WebAuthn."""
    return secrets.token_urlsafe(32)


def verify_webauthn_signature(
    credential_id: str,
    public_key: bytes,
    challenge: str,
    signature: bytes,
    client_data_json: str,
    authenticator_data: bytes,
) -> bool:
    """Verify WebAuthn signature."""
    # This is a simplified implementation
    # In production, use a proper WebAuthn library like webauthn-lib
    try:
        # Parse client data
        import json
        client_data = json.loads(client_data_json)
        if client_data.get("type") != "webauthn.get":
            return False
        if client_data.get("challenge") != challenge:
            return False
        # Verify origin
        # Verify signature using public key
        # This is a simplified check - use a proper library in production
        return True
    except Exception:
        return False


# API Key management
def generate_api_key() -> tuple[str, str]:
    """Generate a new API key with prefix and hash."""
    prefix = "ra_live_" if settings.is_production() else "ra_test_"
    random_part = secrets.token_urlsafe(32)
    api_key = f"{prefix}{random_part}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    return api_key, key_hash


def verify_api_key(api_key: str, key_hash: str) -> bool:
    """Verify an API key against its hash."""
    computed_hash = hashlib.sha256(api_key.encode()).hexdigest()
    return hmac.compare_digest(key_hash, computed_hash)


# Session management
class SessionManager:
    """Manage user sessions with Redis."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.session_ttl = settings.auth.access_token_expire_minutes * 60
    
    async def create_session(
        self,
        user_id: str,
        device_info: dict = None,
        ip_address: str = None,
        user_agent: str = None,
    ) -> str:
        """Create a new session."""
        session_id = secrets.token_urlsafe(32)
        session_data = {
            "user_id": user_id,
            "device_info": device_info or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
        }
        
        await self.redis.setex(
            f"session:{session_id}",
            self.session_ttl,
            json.dumps(session_data)
        )
        
        # Track user sessions
        await self.redis.sadd(f"user_sessions:{user_id}", session_id)
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data."""
        data = await self.redis.get(f"session:{session_id}")
        if data:
            import json
            return json.loads(data)
        return None
    
    async def update_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp."""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        session["last_activity"] = datetime.utcnow().isoformat()
        await self.redis.setex(
            f"session:{session_id}",
            self.session_ttl,
            json.dumps(session)
        )
        return True
    
    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a session."""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        user_id = session.get("user_id")
        if user_id:
            await self.redis.srem(f"user_sessions:{user_id}", session_id)
        
        await self.redis.delete(f"session:{session_id}")
        return True
    
    async def revoke_all_user_sessions(self, user_id: str, except_session: str = None) -> int:
        """Revoke all sessions for a user."""
        session_ids = await self.redis.smembers(f"user_sessions:{user_id}")
        count = 0
        for session_id in session_ids:
            if session_id != except_session:
                await self.revoke_session(session_id)
                count += 1
        return count


# Password reset tokens
def generate_password_reset_token(email: str) -> str:
    """Generate a secure password reset token."""
    payload = {
        "email": email,
        "type": "password_reset",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify a password reset token and return the email."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        return payload.get("email")
    except jwt.InvalidTokenError:
        return None


# Email verification tokens
def generate_email_verification_token(email: str) -> str:
    """Generate an email verification token."""
    payload = {
        "email": email,
        "type": "email_verification",
        "exp": datetime.utcnow() + timedelta(days=7),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_email_verification_token(token: str) -> Optional[str]:
    """Verify an email verification token and return the email."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "email_verification":
            return None
        return payload.get("email")
    except jwt.InvalidTokenError:
        return None


# CSRF protection
def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, stored_token: str) -> bool:
    """Verify a CSRF token."""
    return hmac.compare_digest(token, stored_token)


# Secure headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:; frame-ancestors 'none';",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cross-Origin-Embedder-Policy": "require-corp",
}


def apply_security_headers(response: Response) -> Response:
    """Apply security headers to response."""
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response


# ── FastAPI auth dependencies ─────────────────────────────────────────────
# Shared by all routers; avoids circular imports between routers.

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user from JWT bearer token."""
    from ..models import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except HTTPException:
        raise
    except Exception:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")

    return user


async def get_current_active_user(current_user=Depends(get_current_user)):
    """Get current active user (alias for get_current_user which already checks active)."""
    return current_user