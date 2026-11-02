"""
Test fixtures — env isolation BEFORE any marketplace/canonical import.

- App tables:   PostgreSQL  (VA_TEST_DATABASE_URL, default va_matching_test)
- Auth tables:  SQLite file (canonical sync engine; keeps test hermetic)
- SalesLedger:  SQLite file via PAYMENT_LEDGER_DB
- SMTP disabled
"""

from __future__ import annotations

import os
import pathlib
import tempfile
import base64
from cryptography.fernet import Fernet

_TEST_DB = os.environ.get(
    "VA_TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/va_matching_test",
)
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="va_tests_"))

os.environ["DATABASE_URL"] = _TEST_DB
os.environ["AUTH_DATABASE_URL"] = f"sqlite:///{(_TMP / 'auth_test.db').as_posix()}"
os.environ["PAYMENT_LEDGER_DB"] = str(_TMP / "sales_ledger.db")
os.environ.setdefault("DB_ECHO", "0")
os.environ.setdefault("SMTP_HOST", "")
os.environ.setdefault("SMTP_USER", "")
os.environ.setdefault("SMTP_PASSWORD", "")
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("VA_MATCHING_ENV", "test")

# Stripe test mode (dry-run) - set test keys to avoid RuntimeError
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_doesnotmatter")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_testdoesnotmatter")
os.environ.setdefault("STRIPE_PUBLIC_KEY", "pk_test_doesnotmatter")
os.environ.setdefault("VA_MATCHING_ENV", "test")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402


@pytest.fixture(scope="session")
async def app_lifespan():
    """Run the real app lifespan (init_db + services + task queue) once."""
    import main

    async with main.lifespan(main.app):
        yield main.app


@pytest_asyncio.fixture(autouse=True)
async def _clean_db(app_lifespan):
    """Truncate all app tables before each test."""
    from marketplace.database import Base, async_session_maker

    tables = [t.name for t in reversed(Base.metadata.sorted_tables)]
    async with async_session_maker() as session:
        for name in tables:
            await session.execute(text(f'TRUNCATE TABLE "{name}" CASCADE'))  # noqa: S608
        await session.commit()
    yield


@pytest_asyncio.fixture
async def db(app_lifespan):
    """Raw AsyncSession for direct repository work."""
    from marketplace.database import async_session_maker

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(app_lifespan):
    """httpx client against the live app (lifespan already entered)."""
    transport = ASGITransport(app=app_lifespan)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client):
    """Register + login a user; return Bearer headers."""
    payload = {
        "email": "client-user@va-matching.dev",
        "password": "StrongPass123",
        "name": "Test Client",
    }
    reg = await client.post("/api/auth/register", json=payload)
    assert reg.status_code == 200, reg.text
    login = await client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
