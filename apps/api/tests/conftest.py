"""
Test configuration and fixtures for integration tests.
"""

import pytest
import asyncio
import sys
import os

# Add project root to sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models import User, Agency, Client


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
async def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        first_name="Test",
        last_name="User",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user


@pytest.fixture
async def test_agency(db_session):
    """Create a test agency."""
    agency = Agency(
        name="Test Agency",
        slug="test-agency",
        is_active=True,
    )
    db_session.add(agency)
    await db_session.commit()
    await db_session.refresh(agency)
    yield agency


@pytest.fixture
async def test_client(db_session, test_agency):
    """Create a test client."""
    client = Client(
        agency_id=test_agency.id,
        name="Test Client",
        slug="test-client",
        is_active=True,
    )
    db_session.add(client)
    await db_session.commit()
    await db_session.refresh(client)
    yield client


@pytest.fixture
async def async_client_auth_header(async_client: AsyncClient):
    """Create an authenticated client with auth headers."""
    # Register a user
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "authclient@example.com",
            "password": "TestPassword123!",
            "first_name": "Auth",
            "last_name": "Client",
            "agency_name": "Auth Agency",
        },
    )
    # Login
    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "authclient@example.com", "password": "TestPassword123!"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return token