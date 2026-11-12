"""SQLAlchemy models for the dynamic entity system.

Stores entity schemas and records durably in PostgreSQL so data survives
restarts and can be queried across services, workers, and the frontend.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, TypeDecorator, func
from sqlalchemy.types import JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from retention_analytics_core.database import Base


class JSONBCompat(TypeDecorator):
    """JSONB on PostgreSQL, JSON on other dialects (e.g. SQLite for tests)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB

            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class EntitySchemaModel(Base):
    __tablename__ = "entity_schemas"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    fields: Mapped[list[dict[str, Any]]] = mapped_column(JSONBCompat, nullable=False, default=list)
    relationships: Mapped[list[dict[str, Any]]] = mapped_column(JSONBCompat, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    records: Mapped[list[EntityRecordModel]] = relationship(
        "EntityRecordModel", back_populates="schema", cascade="all, delete-orphan"
    )


class EntityRecordModel(Base):
    __tablename__ = "entity_records"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    schema_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("entity_schemas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONBCompat, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    schema: Mapped[EntitySchemaModel] = relationship("EntitySchemaModel", back_populates="records")


__all__ = ["EntitySchemaModel", "EntityRecordModel"]
