"""
Authentication API endpoints.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Cookie
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from ...core.config import get_settings
from ...core.database import get_db
from ...core import security as security_module

# Re-export security functions for backward compatibility
get_password_hash = security_module.get_password_hash
verify_password = security_module.verify_password
create_access_token = security_module.create_access_token
create_refresh_token = security_module.create_refresh_token
decode_access_token = security_module.decode_access_token
decode_refresh_token = security_module.decode_refresh_token
generate_totp_secret = security_module.generate_totp_secret
get_totp_uri = security_module.get_totp_uri
verify_totp = security_module.verify_totp
generate_qr_code = security_module.generate_qr_code
generate_challenge = security_module.generate_challenge
generate_password_reset_token = security_module.generate_password_reset_token
verify_password_reset_token = security_module.verify_password_reset_token
generate_email_verification_token = security_module.generate_email_verification_token
verify_email_verification_token = security_module.verify_email_verification_token
generate_api_key = security_module.generate_api_key
verify_api_key = security_module.verify_api_key
SessionManager = security_module.SessionManager
from ...core.database import get_db
from ...core.redis import get_redis
from ...core.security import SessionManager
from ...core.config import get_settings
from ...models import User, UserRole, Role, Permission, MFADevice, Passkey, Session, ApiKey, Platform, Client

logger = structlog.get_logger()
router = APIRouter()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

settings = get_settings()


# Pydantic models
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    sub: str
    scopes: List[str] = []


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False
    mfa_token: Optional[str] = None


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    first_name: str
    last_name: str
    agency_name: Optional[str] = None


class MFASetupResponse(BaseModel):
    secret: str
    qr_code: str
    uri: str


class MFAVerify(BaseModel):
    secret: str
    token: str


class MFAEnable(BaseModel):
    secret: str
    token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str = Field(min_length=12)


class EmailVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationConfirm(BaseModel):
    token: str


class APIKeyCreate(BaseModel):
    name: str
    scopes: List[str] = []


class APIKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    scopes: List[str]
    created_at: str
    expires_at: Optional[str]
    is_active: bool


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}
    
    id: str
    email: str
    first_name: str
    last_name: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    role: str = "user"
    is_active: bool
    mfa_enabled: bool
    avatar_url: Optional[str]
    timezone: str
    locale: str
    created_at: str
    last_login_at: Optional[str]
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_id(cls, v):
        return str(v)
    
    @field_validator('created_at', 'last_login_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)
    
    @field_validator('role', mode='before')
    @classmethod
    def convert_role(cls, v):
        if v is None:
            return "user"
        return str(v)


# Dependencies
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return current_user


async def get_redis_client():
    """Get Redis client."""
    return await get_redis()


# Routes
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user and agency."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
# Get or create default platform
    from ...models import Agency, Platform, Client
    from ...core.config import get_settings
    
    settings = get_settings()
    
    # Get or create default platform
    result = await db.execute(select(Platform).where(Platform.name == settings.name))
    platform = result.scalar_one_or_none()
    if not platform:
        platform = Platform(name=settings.name, slug=settings.name.lower().replace(" ", "-"))
        db.add(platform)
        await db.flush()
    
    # Create agency if provided
    agency = None
    client = None
    if user_data.agency_name:
        agency = Agency(
            name=user_data.agency_name,
            slug=user_data.agency_name.lower().replace(" ", "-"),
            owner_id=None,  # Will be set after user creation
            platform_id=platform.id,
        )
        db.add(agency)
        await db.flush()
        
        # Create default client for the agency
        client = Client(
            agency_id=agency.id,
            name=f"{user_data.agency_name} Client",
            slug=user_data.agency_name.lower().replace(" ", "-") + "-client",
        )
        db.add(client)
        await db.flush()
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        agency_id=agency.id if agency else None,
        client_id=client.id if client else None,
        platform_id=platform.id,
        is_active=True,
    )
    
    db.add(user)
    await db.flush()
    
    # Update agency owner if created
    if agency:
        agency.owner_id = user.id
    
    # Create default role assignment
    from ...models import Role, UserRole
    result = await db.execute(select(Role).where(Role.name == "owner"))
    owner_role = result.scalar_one_or_none()
    if owner_role:
        user_role = UserRole(user_id=user.id, role_id=owner_role.id)
        db.add(user_role)
    
    await db.commit()
    await db.refresh(user)
    
    # Send verification email
    # TODO: Send verification email
    
    return UserResponse.from_orm(user)


@router.post("/login", response_model=Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis_client),
):
    """Login with email and password."""
    # Find user
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not security_module.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    
    # Check MFA
    if user.mfa_enabled:
        # MFA required - return challenge
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA required",
            headers={"X-MFA-Required": "true"},
        )
    
    # Create tokens
    access_token = create_access_token(
        subject=str(user.id),
        scopes=["read", "write"],
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    
    # Create session
    redis_client = await get_redis()
    session_manager = SessionManager(redis_client)
    session_id = await session_manager.create_session(
        user_id=str(user.id),
        device_info={},
    )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 60,  # 30 minutes
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,  # 7 days
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    response: Response,
    refresh_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token."""
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token required")
    
    try:
        payload = decode_refresh_token(refresh_token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Verify user exists and is active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    # Create new tokens
    access_token = create_access_token(subject=str(user.id), scopes=["read", "write"])
    new_refresh_token = create_refresh_token(subject=str(user.id))
    
    # Set new cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
    )
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=30 * 60,
    )


@router.post("/logout")
async def logout(
    response: Response,
    access_token: str = Cookie(None),
    refresh_token: str = Cookie(None),
    redis_client = Depends(get_redis_client),
):
    """Logout and revoke tokens."""
    # Revoke access token (add to blacklist)
    if access_token:
        try:
            payload = decode_access_token(access_token)
            user_id = payload.get("sub")
            # Add to blacklist with TTL matching token expiry
            redis_client = await get_redis()
            await redis.setex(f"blacklist:{access_token}", 1800, "revoked")
        except:
            pass
    
    # Revoke refresh token
    if refresh_token:
        try:
            payload = decode_refresh_token(refresh_token)
            user_id = payload.get("sub")
            redis_client = await get_redis()
            await redis_client.setex(f"blacklist:{refresh_token}", 7 * 24 * 3600, "revoked")
        except:
            pass
    
    # Clear cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user profile."""
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    user_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile."""
    allowed_fields = ["first_name", "last_name", "display_name", "avatar_url", "timezone", "locale", "notifications_enabled"]
    
    for field, value in user_data.items():
        if field in allowed_fields:
            setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse.from_orm(current_user)


@router.put("/me/password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Change user password."""
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    if len(new_password) < 12:
        raise HTTPException(status_code=400, detail="Password must be at least 12 characters")
    
    # Reload user in current session to ensure we're working with an attached instance
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()
    
    new_hash = get_password_hash(new_password)
    print(f"DEBUG: Setting password_hash to: {new_hash}")  # Debug
    setattr(user, 'password_hash', new_hash)
    setattr(user, 'password_changed_at', datetime.utcnow())
    
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)
    
    # Verify the password hash was saved
    print(f"DEBUG: After refresh, password_hash = {user.password_hash}")  # Debug
    
    return {"message": "Password changed successfully"}


# MFA endpoints
@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Setup MFA for user."""
    if current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA already enabled")
    
    # Generate secret
    secret = generate_totp_secret()
    
    # Create MFA device (unverified)
    from ...models import MFADevice
    mfa_device = MFADevice(
        user_id=current_user.id,
        type="totp",
        name="Authenticator App",
        secret_encrypted=current_user.encrypt_field(secret),  # Would need encryption
        is_verified=False,
    )
    db.add(mfa_device)
    await db.commit()
    
    # Generate QR code
    uri = get_totp_uri(secret, current_user.email)
    qr_code = generate_qr_code(uri)
    
    import base64
    qr_base64 = base64.b64encode(qr_code).decode()
    
    return MFASetupResponse(
        secret=secret,
        qr_code=qr_base64,
        uri=uri,
    )


@router.post("/mfa/verify")
async def verify_mfa(
    mfa_data: MFAVerify,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify MFA token during setup."""
    if not verify_totp(mfa_data.secret, mfa_data.token):
        raise HTTPException(status_code=400, detail="Invalid token")
    
    # Update MFA device as verified
    # TODO: Update MFA device
    
    return {"message": "MFA verified successfully"}


@router.post("/mfa/enable")
async def enable_mfa(
    mfa_data: MFAEnable,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable MFA after verification."""
    if not verify_totp(mfa_data.secret, mfa_data.token):
        raise HTTPException(status_code=400, detail="Invalid token")
    
    # Update user MFA settings
    current_user.mfa_enabled = True
    current_user.mfa_secret = current_user.encrypt_field(mfa_data.secret)  # Would need encryption
    
    await db.commit()
    
    return {"message": "MFA enabled successfully"}


@router.post("/mfa/disable")
async def disable_mfa(
    password: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable MFA."""
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA not enabled")
    
    if not verify_password(password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    
    # Revoke MFA devices
    # TODO: Revoke MFA devices
    
    await db.commit()
    
    return {"message": "MFA disabled successfully"}


# Password reset
@router.post("/password/reset/request")
async def request_password_reset(
    request_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request password reset."""
    result = await db.execute(select(User).where(User.email == request_data.email))
    user = result.scalar_one_or_none()
    
    # Always return success to prevent email enumeration
    if user:
        token = generate_password_reset_token(request_data.email)
        # TODO: Send reset email
        logger.info("Password reset requested", email=request_data.email)
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password/reset/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Confirm password reset."""
    email = verify_password_reset_token(reset_data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    
    user.hashed_password = get_password_hash(reset_data.password)
    user.password_changed_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Password reset successfully"}


# Email verification
@router.post("/email/verify/request")
async def request_email_verification(
    request_data: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request email verification."""
    result = await db.execute(select(User).where(User.email == request_data.email))
    user = result.scalar_one_or_none()
    
    if user and not user.email_verified:
        token = generate_email_verification_token(request_data.email)
        # TODO: Send verification email
        logger.info("Email verification requested", email=request_data.email)
    
    return {"message": "If the email exists and is not verified, a verification link has been sent"}


@router.post("/email/verify/confirm")
async def confirm_email_verification(
    verification_data: EmailVerificationConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Confirm email verification."""
    email = verify_email_verification_token(verification_data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    
    user.email_verified = True
    user.email_verified_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Email verified successfully"}


# API Key management
@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key."""
    api_key, key_hash = generate_api_key()
    
    api_key_obj = ApiKey(
        user_id=current_user.id,
        name=api_key_data.name,
        prefix=api_key[:8],
        key_hash=key_hash,
        scopes=api_key_data.scopes,
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    return APIKeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        prefix=api_key.prefix,
        scopes=api_key.scopes,
        created_at=api_key.created_at.isoformat(),
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
        is_active=api_key.is_active,
    )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's API keys."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == current_user.id)
    )
    api_keys = result.scalars().all()
    
    return [
        APIKeyResponse(
            id=str(k.id),
            name=k.name,
            prefix=k.prefix,
            scopes=k.scopes,
            created_at=k.created_at.isoformat(),
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
            is_active=k.is_active,
        )
        for k in api_keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == current_user.id
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key.is_active = False
    api_key.revoked_at = datetime.utcnow()
    api_key.revoked_reason = "revoked_by_user"
    
    await db.commit()
    
    return {"message": "API key revoked successfully"}


# Sessions
@router.get("/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_active_user),
    redis_client = Depends(get_redis_client),
):
    """List active sessions for current user."""
    session_manager = SessionManager(await get_redis())
    session_ids = await redis_client.smembers(f"user_sessions:{current_user.id}")
    
    sessions = []
    for session_id in session_ids:
        session = await SessionManager(await get_redis()).get_session(session_id)
        if session:
            sessions.append({
                "id": session_id,
                "device_info": session.get("device_info"),
                "ip_address": session.get("ip_address"),
                "user_agent": session.get("user_agent"),
                "created_at": session.get("created_at"),
                "last_activity": session.get("last_activity"),
            })
    
    return {"sessions": sessions}


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Revoke a specific session."""
    session_manager = SessionManager(await get_redis())
    success = await session_manager.revoke_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session revoked"}


@router.delete("/sessions")
async def revoke_all_sessions(
    current_user: User = Depends(get_current_active_user),
):
    """Revoke all sessions except current."""
    # TODO: Implement revoke all except current
    return {"message": "All other sessions revoked"}


# Passkeys/WebAuthn
@router.post("/passkeys/register/begin")
async def passkey_register_begin(
    current_user: User = Depends(get_current_active_user),
):
    """Begin passkey registration."""
    challenge = generate_challenge()
    # TODO: Store challenge in session
    return {
        "challenge": challenge,
        "rp": {
            "name": settings.auth.rp_name,
            "id": settings.auth.rp_id,
        },
        "user": {
            "id": str(current_user.id),
            "name": current_user.email,
            "displayName": current_user.display_name or current_user.email,
        },
        "pubKeyCredParams": [
            {"type": "public-key", "alg": -7},  # ES256
            {"type": "public-key", "alg": -257},  # RS256
        ],
        "timeout": 60000,
        "attestation": "direct",
    }


@router.post("/passkeys/register/complete")
async def passkey_register_complete(
    credential: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Complete passkey registration."""
    # TODO: Verify attestation and store credential
    from ...models import Passkey
    
    passkey = Passkey(
        user_id=current_user.id,
        credential_id=credential["id"],
        public_key=credential["response"]["publicKey"],
        sign_count=0,
        transports=credential["response"].get("transports", []),
    )
    
    db.add(passkey)
    await db.commit()
    
    return {"message": "Passkey registered successfully"}


@router.post("/passkeys/authenticate/begin")
async def passkey_authenticate_begin(
    current_user: User = Depends(get_current_active_user),
):
    """Begin passkey authentication."""
    challenge = generate_challenge()
    # TODO: Store challenge
    return {
        "challenge": challenge,
        "timeout": 60000,
        "rpId": settings.auth.rp_id,
        "allowCredentials": [],  # Would include user's registered credentials
        "userVerification": "preferred",
    }


@router.post("/passkeys/authenticate/complete")
async def passkey_authenticate_complete(
    credential: dict,
    db: AsyncSession = Depends(get_db),
):
    """Complete passkey authentication."""
    # TODO: Verify assertion and authenticate user
    # Would verify the assertion and return tokens
    return {"message": "Passkey authentication not fully implemented"}


# Device management
@router.get("/devices")
async def list_devices(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's MFA devices and passkeys."""
    from ...models import MFADevice, Passkey
    
    mfa_devices = await db.execute(
        select(MFADevice).where(MFADevice.user_id == current_user.id)
    )
    mfa_devices = mfa_devices.scalars().all()
    
    passkeys = await db.execute(
        select(Passkey).where(Passkey.user_id == current_user.id)
    )
    passkeys = passkeys.scalars().all()
    
    return {
        "mfa_devices": [
            {
                "id": str(d.id),
                "type": d.type,
                "name": d.name,
                "is_verified": d.is_verified,
                "last_used_at": d.last_used_at.isoformat() if d.last_used_at else None,
            }
            for d in mfa_devices
        ],
        "passkeys": [
            {
                "id": str(p.id),
                "name": p.name,
                "device_type": p.device_type,
                "last_used_at": p.last_used_at.isoformat() if p.last_used_at else None,
            }
            for p in passkeys
        ],
    }


@router.delete("/devices/{device_id}")
async def remove_device(
    device_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an MFA device or passkey."""
    # Try MFA device
    from ...models import MFADevice, Passkey
    
    result = await db.execute(
        select(MFADevice).where(
            MFADevice.id == device_id,
            MFADevice.user_id == current_user.id
        )
    )
    device = result.scalar_one_or_none()
    
    if device:
        await db.delete(device)
        await db.commit()
        return {"message": "Device removed"}
    
    # Try passkey
    result = await db.execute(
        select(Passkey).where(
            Passkey.id == device_id,
            Passkey.user_id == current_user.id
        )
    )
    passkey = result.scalar_one_or_none()
    
    if passkey:
        await db.delete(passkey)
        await db.commit()
        return {"message": "Passkey removed"}
    
    raise HTTPException(status_code=404, detail="Device not found")