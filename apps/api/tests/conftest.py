"""
Test configuration and fixtures for integration tests.
"""

import pytest
import asyncio
import sys
import os
import uuid
import hashlib

# Add project root to sys.path for imports
# This project is at: C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform-clean
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import async_session_maker, engine
from app.models import User, Agency, Client
from app.models.base import Base

# Override database URL for tests to use SQLite
import app.core.database as database_module
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Create SQLite engine for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)
test_async_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Override the database module's engine and session maker
database_module.engine = test_engine
database_module.async_session_maker = test_async_session_maker

from app.main import app
from app.core.database import async_session_maker
from app.models import User, Agency, Client
from app.models.base import Base

# Use fakeredis for tests
import fakeredis.aioredis

# Create tables fixture
@pytest.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all database tables before tests run."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Use fakeredis for tests
import fakeredis.aioredis
import app.core.redis as redis_module
import redis.asyncio as redis

# Create a fakeredis instance for testing
_fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

async def get_fake_redis():
    return _fake_redis

# Override the Redis module's get_redis function
redis_module.get_redis = get_fake_redis

# Also patch the redis.from_url to return fakeredis
original_from_url = redis.from_url

def fake_from_url(url, **kwargs):
    return _fake_redis

redis.from_url = fake_from_url


# Simple password hash for tests (avoids bcrypt issues on Windows)
def test_password_hash(password: str) -> str:
    """Simple password hash for tests - not cryptographically secure, only for testing."""
    return f"test_hash_{hashlib.sha256(password.encode()).hexdigest()}"


def test_verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a test password hash."""
    expected = f"test_hash_{hashlib.sha256(plain_password.encode()).hexdigest()}"
    return hashed_password == expected


# Patch the security module for tests
import app.core.security as security_module
security_module.get_password_hash = test_password_hash
security_module.verify_password = test_verify_password

# Also patch the auth module's reference
import app.api.v1.auth as auth_module
auth_module.get_password_hash = test_password_hash
auth_module.verify_password = test_verify_password

# Now import after patching
from app.core.security import get_password_hash


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client():
    """Create an async HTTP client for testing API endpoints."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def db_session():
    """Get a database session for testing."""
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def test_user(db_session, test_client):
    """Create a test user with unique email."""
    unique_id = uuid.uuid4().hex[:8]
    
    # Get or create a default platform
    from app.models import Platform
    from sqlalchemy import select
    result = await db_session.execute(select(Platform).limit(1))
    platform = result.scalar_one_or_none()
    if not platform:
        platform = Platform(name="Test Platform", slug="test-platform")
        db_session.add(platform)
        await db_session.flush()
    
    user = User(
        email=f"test_{unique_id}@example.com",
        password_hash=test_password_hash("TestPass123!"),
        first_name="Test",
        last_name="User",
        is_active=True,
        client_id=test_client.id,
        agency_id=test_client.agency_id,
        platform_id=platform.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user


@pytest.fixture
async def test_agency(db_session):
    """Create a test agency with unique slug."""
    unique_id = uuid.uuid4().hex[:8]
    
    # Get or create a default platform
    from app.models import Platform
    from sqlalchemy import select
    result = await db_session.execute(select(Platform).limit(1))
    platform = result.scalar_one_or_none()
    if not platform:
        platform = Platform(name="Test Platform", slug="test-platform")
        db_session.add(platform)
        await db_session.flush()
    
    agency = Agency(
        name=f"Test Agency {unique_id}",
        slug=f"test-agency-{unique_id}",
        platform_id=platform.id,
    )
    db_session.add(agency)
    await db_session.commit()
    await db_session.refresh(agency)
    yield agency


@pytest.fixture
async def test_client(db_session, test_agency):
    """Create a test client with unique slug."""
    unique_id = uuid.uuid4().hex[:8]
    client = Client(
        agency_id=test_agency.id,
        name=f"Test Client {unique_id}",
        slug=f"test-client-{unique_id}",
        is_active=True,
    )
    db_session.add(client)
    await db_session.commit()
    await db_session.refresh(client)
    yield client


@pytest.fixture
async def async_client_auth_header(async_client: AsyncClient):
    """Create an authenticated client with auth headers."""
    unique_id = uuid.uuid4().hex[:8]
    password = "TestPass123!"
    # Register a user
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": f"authclient_{unique_id}@example.com",
            "password": password,
            "first_name": "Auth",
            "last_name": "Client",
            "agency_name": f"Auth Agency {unique_id}",
        },
    )
    # Login
    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": f"authclient_{unique_id}@example.com", "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return token