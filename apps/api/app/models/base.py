"""
Base model and mixins for all database models.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, func, UUID as SQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID


class Base(DeclarativeBase):
    """Base class for all models."""
    
    type_annotation_map = {
        dict: JSONB,
        list: JSONB,
    }
    
    @declared_attr.directive
    def __tablename__(cls) -> str:
        # Convert CamelCase to snake_case
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
        return name


class UUIDMixin:
    """Mixin for UUID primary key."""
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for soft delete support."""
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )


class MetadataMixin:
    """Mixin for flexible metadata storage."""
    meta: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )


class TenantMixin:
    """Mixin for multi-tenant models."""
    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    agency_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model with UUID and timestamps."""
    __abstract__ = True


class TenantModel(BaseModel, TenantMixin):
    """Base model for tenant-scoped entities."""
    __abstract__ = True


class SoftDeleteModel(TenantModel, SoftDeleteMixin):
    """Base model for tenant-scoped entities with soft delete."""
    __abstract__ = True
