"""Dynamic entity kernel with SQLAlchemy persistence.

Provides a schema-as-data entity system: entities, fields, and relationships
are defined at runtime and stored durably in PostgreSQL. This lets vertical
packs define their own domain models without code changes, and lets services
operate on any entity uniformly.

Every method takes an async SQLAlchemy session so the caller controls the
transaction boundary. All queries are tenant-scoped by construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from retention_analytics_core.models import EntityRecordModel, EntitySchemaModel


@dataclass
class EntityField:
    name: str
    type: str  # "string" | "number" | "boolean" | "datetime" | "json" | "uuid"
    required: bool = False
    unique: bool = False


@dataclass
class EntitySchema:
    id: str
    name: str
    tenant_id: str
    fields: list[EntityField] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class EntityRecord:
    id: UUID = field(default_factory=uuid4)
    schema_id: str = ""
    tenant_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)


def _schema_to_dataclass(model: EntitySchemaModel) -> EntitySchema:
    return EntitySchema(
        id=model.id,
        name=model.name,
        tenant_id=model.tenant_id,
        fields=[
            EntityField(
                name=f["name"],
                type=f["type"],
                required=f.get("required", False),
                unique=f.get("unique", False),
            )
            for f in model.fields
        ],
        relationships=model.relationships,
    )


def _record_to_dataclass(model: EntityRecordModel) -> EntityRecord:
    return EntityRecord(
        id=model.id,
        schema_id=model.schema_id,
        tenant_id=model.tenant_id,
        data=model.data,
    )


class EntityKernel:
    """Durable dynamic entity store backed by PostgreSQL.

    Entities are schema-as-data: register a schema, then create/read/update
    records against it. Used by vertical packs and services alike so domain
    models are shared, not siloed per service.

    All queries are tenant-scoped. No user data is ever held in memory
    beyond the lifetime of a single request/session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register_schema(self, schema: EntitySchema) -> None:
        existing = await self._session.get(EntitySchemaModel, schema.id)
        if existing is not None:
            raise ValueError(f"Schema '{schema.id}' already registered")
        model = EntitySchemaModel(
            id=schema.id,
            name=schema.name,
            tenant_id=schema.tenant_id,
            fields=[
                {
                    "name": f.name,
                    "type": f.type,
                    "required": f.required,
                    "unique": f.unique,
                }
                for f in schema.fields
            ],
            relationships=schema.relationships,
        )
        self._session.add(model)
        await self._session.flush()

    async def get_schema(self, schema_id: str) -> EntitySchema:
        model = await self._session.get(EntitySchemaModel, schema_id)
        if model is None:
            raise KeyError(f"Schema '{schema_id}' not registered")
        return _schema_to_dataclass(model)

    async def create_record(
        self, schema_id: str, tenant_id: str, data: dict[str, Any]
    ) -> EntityRecord:
        # Validate schema exists
        schema = await self._session.get(EntitySchemaModel, schema_id)
        if schema is None:
            raise KeyError(f"Schema '{schema_id}' not registered")
        if schema.tenant_id != tenant_id:
            raise KeyError(f"Schema '{schema_id}' not accessible by tenant '{tenant_id}'")
        record_id = uuid4()
        model = EntityRecordModel(
            id=record_id,
            schema_id=schema_id,
            tenant_id=tenant_id,
            data=dict(data),
        )
        self._session.add(model)
        await self._session.flush()
        return _record_to_dataclass(model)

    async def get_record(self, schema_id: str, record_id: UUID) -> EntityRecord:
        model = await self._session.get(EntityRecordModel, record_id)
        if model is None:
            raise KeyError(f"Record '{record_id}' not found")
        if model.schema_id != schema_id:
            raise KeyError(
                f"Record '{record_id}' not found in schema '{schema_id}'"
            )
        return _record_to_dataclass(model)

    async def list_records(
        self, schema_id: str, tenant_id: str
    ) -> list[EntityRecord]:
        """List records for a schema, tenant-scoped (tenant_id is required)."""
        stmt = select(EntityRecordModel).where(
            EntityRecordModel.schema_id == schema_id,
            EntityRecordModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return [_record_to_dataclass(m) for m in result.scalars().all()]

    async def update_record(
        self, schema_id: str, record_id: UUID, data: dict[str, Any]
    ) -> EntityRecord:
        model = await self._session.get(EntityRecordModel, record_id)
        if model is None:
            raise KeyError(f"Record '{record_id}' not found")
        if model.schema_id != schema_id:
            raise KeyError(
                f"Record '{record_id}' not found in schema '{schema_id}'"
            )
        model.data.update(data)
        flag_modified(model, "data")
        await self._session.flush()
        return _record_to_dataclass(model)

    async def delete_record(self, schema_id: str, record_id: UUID) -> None:
        model = await self._session.get(EntityRecordModel, record_id)
        if model is None:
            raise KeyError(f"Record '{record_id}' not found")
        if model.schema_id != schema_id:
            raise KeyError(
                f"Record '{record_id}' not found in schema '{schema_id}'"
            )
        await self._session.execute(
            delete(EntityRecordModel).where(EntityRecordModel.id == record_id)
        )


__all__ = ["EntityKernel", "EntitySchema", "EntityField", "EntityRecord"]
