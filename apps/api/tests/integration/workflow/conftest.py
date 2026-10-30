"""
Workflow tests conftest.py

Shares fixtures with the parent conftest.py in apps/api/tests/
"""

import pytest
import uuid
from httpx import AsyncClient

from app.main import app
from app.core.database import async_session_maker
from app.models import User, Agency, Client, Platform


@pytest.fixture
async def db_session():
    """Get a database session for testing."""
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def test_agency(db_session):
    """Create a test agency with unique slug."""
    unique_id = uuid.uuid4().hex[:8]
    
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