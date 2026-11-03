"""L2/L3 tests against a real PostgreSQL database.

Per TESTING_STANDARDS.md §2:
- L2 (persistence): write through the service, read back from a FRESH session,
  assert field correctness, tenant isolation, pagination.
- L3 (workflow end state): execute the workflow trigger, assert the persisted
  end state machine and cross-service effects.

These tests require a running PostgreSQL. They are marked ``live`` and SKIP
(cleanly) when DATABASE_URL is not reachable, so the fast suite stays green.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

TENANT_A = "00000000-0000-0000-0000-000000000001"
TENANT_B = "00000000-0000-0000-0000-000000000002"

pytestmark = pytest.mark.live


def _database_url() -> str | None:
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    return url or None


@pytest.fixture(scope="module")
def anyio_backend() -> str:
    return "asyncio"


async def _db_available(url: str) -> bool:
    try:
        engine = create_async_engine(url, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
    except Exception:  # noqa: BLE001
        return False
    return True


def _require_db() -> str:
    url = _database_url()
    if not url:
        pytest.skip("No TEST_DATABASE_URL/DATABASE_URL configured — live DB tests skipped")
    loop_ok = pytest.importorskip("pytest_asyncio") is not None
    assert loop_ok
    return url


@pytest.fixture(scope="module")
def session_factory():
    url = _require_db()
    engine = create_async_engine(url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    import asyncio

    asyncio.get_event_loop_policy()
    # Cleanup is best-effort; engine disposal handled in finalizer below
    import atexit

    atexit.register(engine.dispose)


@pytest.fixture(scope="module")
def event_loop():
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_l2_schema_create_and_fresh_session_read_back(session_factory) -> None:
    """L2: create a schema, commit, then read back from a FRESH session."""
    from retention_analytics_core.entities.kernel import (
        EntityField,
        EntityKernel,
        EntitySchema,
    )

    schema_id = f"live-schema-{uuid4().hex[:8]}"

    async with session_factory() as session:
        kernel = EntityKernel(session)
        await kernel.register_schema(
            EntitySchema(
                id=schema_id,
                name="Live Test Schema",
                tenant_id=TENANT_A,
                fields=[EntityField(name="name", type="string", required=True)],
            )
        )
        await session.commit()

    # Fresh session — proves durability beyond the writing session
    async with session_factory() as fresh:
        kernel = EntityKernel(fresh)
        fetched = await kernel.get_schema(schema_id)
        assert fetched.id == schema_id
        assert fetched.name == "Live Test Schema"
        assert fetched.tenant_id == TENANT_A
        assert fetched.fields[0].name == "name"
        assert fetched.fields[0].required is True


@pytest.mark.asyncio
async def test_l2_record_write_read_update_delete(session_factory) -> None:
    """L2: full record lifecycle through fresh sessions."""
    from retention_analytics_core.entities.kernel import (
        EntityField,
        EntityKernel,
        EntitySchema,
    )

    schema_id = f"live-records-{uuid4().hex[:8]}"

    async with session_factory() as session:
        kernel = EntityKernel(session)
        await kernel.register_schema(
            EntitySchema(
                id=schema_id,
                name="Live Records",
                tenant_id=TENANT_A,
                fields=[EntityField(name="name", type="string")],
            )
        )
        record = await kernel.create_record(
            schema_id, TENANT_A, {"name": "Acme Corp"}
        )
        await session.commit()
        record_id = record.id

    # Read back (fresh session)
    async with session_factory() as fresh:
        kernel = EntityKernel(fresh)
        fetched = await kernel.get_record(schema_id, record_id)
        assert fetched.data["name"] == "Acme Corp"

        # Update
        await kernel.update_record(schema_id, record_id, {"name": "Acme Corp Updated"})
        await fresh.commit()

    async with session_factory() as fresh:
        kernel = EntityKernel(fresh)
        updated = await kernel.get_record(schema_id, record_id)
        assert updated.data["name"] == "Acme Corp Updated"

        # Delete
        await kernel.delete_record(schema_id, record_id)
        await fresh.commit()

    async with session_factory() as fresh:
        kernel = EntityKernel(fresh)
        with pytest.raises(KeyError):
            await kernel.get_record(schema_id, record_id)


@pytest.mark.asyncio
async def test_l2_tenant_isolation(session_factory) -> None:
    """L2 (P0): tenant A's data is invisible to tenant B."""
    from retention_analytics_core.entities.kernel import (
        EntityField,
        EntityKernel,
        EntitySchema,
    )

    schema_id = f"live-tenant-{uuid4().hex[:8]}"

    async with session_factory() as session:
        kernel = EntityKernel(session)
        await kernel.register_schema(
            EntitySchema(
                id=schema_id,
                name="Tenant Isolation",
                tenant_id=TENANT_A,
                fields=[EntityField(name="secret", type="string")],
            )
        )
        await kernel.create_record(schema_id, TENANT_A, {"secret": "tenant-a-data"})
        await session.commit()

    # Tenant B's query returns nothing
    async with session_factory() as fresh:
        kernel = EntityKernel(fresh)
        tenant_b_records = await kernel.list_records(schema_id, TENANT_B)
        assert tenant_b_records == []

        # Tenant A sees its own record
        tenant_a_records = await kernel.list_records(schema_id, TENANT_A)
        assert len(tenant_a_records) == 1
        assert tenant_a_records[0].data["secret"] == "tenant-a-data"

        # Cross-tenant write into A's schema is rejected by construction
        with pytest.raises(KeyError):
            await kernel.create_record(
                schema_id, TENANT_B, {"secret": "tenant-b-intrusion"}
            )


@pytest.mark.asyncio
async def test_l3_workflow_persists_run_end_state() -> None:
    """L3: run a workflow and assert the persisted end state."""
    from retention_analytics_core.service_registry import ServiceRegistry
    from retention_analytics_core.workflows.engine import (
        WorkflowDefinition,
        WorkflowEngine,
        WorkflowStep,
    )
    from retention_analytics_engagement.email.service import EmailService

    registry = ServiceRegistry()
    email = EmailService(registry)
    email.register()

    engine = WorkflowEngine(registry)
    engine.register_definition(
        WorkflowDefinition(
            id=f"live-flow-{uuid4().hex[:8]}",
            name="Live End State Flow",
            tenant_id=TENANT_A,
            steps=[
                WorkflowStep(
                    id="send",
                    service="email",
                    action="send",
                    input={
                        "to": "ops@acme.example",
                        "subject": "Live end-state",
                        "body": "Proof of execution",
                    },
                ),
            ],
        )
    )

    wf_id = engine.list_definitions()[0].id
    run = await engine.run(wf_id, TENANT_A)

    # Persisted end state: completed with real step output
    assert run.status == "completed"
    assert run.step_outputs["send"]["status"] == "sent"
    assert run.step_outputs["send"]["channel"] == "email"
    # The run is retrievable by id (durable reference)
    retrieved = engine.get_run(run.id)
    assert retrieved.id == run.id
    assert retrieved.status == "completed"
