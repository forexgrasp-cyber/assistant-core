"""
Vertical pack models: Packs, Versions, Entities, Workflows, Reports, Marketplace.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index, Enum as SQLEnum, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from .base import SoftDeleteModel


class PackCategory(SoftDeleteModel):
    """Vertical pack category."""
    __tablename__ = "pack_categories"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    packs: Mapped[List["VerticalPack"]] = relationship("VerticalPack", back_populates="category")


class VerticalPack(SoftDeleteModel):
    """Vertical pack definition."""
    __tablename__ = "vertical_packs"
    
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pack_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    long_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Versioning
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    min_platform_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    max_platform_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Author
    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    author_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author_website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # License
    license: Mapped[str] = mapped_column(String(50), default="proprietary", nullable=False)  # proprietary, MIT, Apache-2.0, GPL-3.0
    license_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Pricing
    price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    pricing_model: Mapped[str] = mapped_column(String(50), default="one_time", nullable=False)  # one_time, subscription, usage, freemium
    subscription_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    subscription_interval: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Content
    entities: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    workflows: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    reports: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    dashboards: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    templates: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    widgets: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    segments: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    integrations: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    custom_roles: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    permissions: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Dependencies
    dependencies: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    # [{"pack_slug": "marketing-core", "version": ">=1.0.0", "required": true}]
    
    # Compatibility
    compatible_platforms: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)  # ["self-hosted", "cloud"]
    min_resources: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)  # {"cpu": "2", "memory": "4GB"}
    
    # Media
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    banner_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    screenshots: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    documentation_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    changelog_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Installation
    install_script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uninstall_script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    post_install_steps: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    config_schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    default_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Marketplace
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Stats
    downloads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_installations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0.0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Support
    support_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    support_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sla_response_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)  # draft, review, published, deprecated, archived
    moderation_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, approved, rejected
    moderation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Tags
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Relationships
    category: Mapped[Optional["PackCategory"]] = relationship("PackCategory", back_populates="packs")
    author: Mapped[Optional["User"]] = relationship("User", foreign_keys=[author_id])
    versions: Mapped[List["PackVersion"]] = relationship("PackVersion", back_populates="pack", cascade="all, delete-orphan")
    installations: Mapped[List["PackInstallation"]] = relationship("PackInstallation", back_populates="pack", cascade="all, delete-orphan")
    reviews: Mapped[List["PackReview"]] = relationship("PackReview", back_populates="pack", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_vertical_packs_client_slug", "client_id", "slug", unique=True),
        Index("ix_vertical_packs_category_status", "category_id", "status"),
    )


class PackVersion(SoftDeleteModel):
    """Pack version for updates/rollback."""
    __tablename__ = "pack_versions"
    
    pack_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vertical_packs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Snapshot of pack content
    entities: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    workflows: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    reports: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    dashboards: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    templates: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    widgets: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    segments: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    integrations: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    custom_roles: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    permissions: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    dependencies: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    config_schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    default_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    install_script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uninstall_script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    post_install_steps: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Changelog
    changelog: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    breaking_changes: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    migration_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Release
    release_type: Mapped[str] = mapped_column(String(20), default="patch", nullable=False)  # major, minor, patch, hotfix
    is_prerelease: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    release_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    pack: Mapped["VerticalPack"] = relationship("VerticalPack", back_populates="versions")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    
    __table_args__ = (
        Index("ix_pack_versions_pack_version", "pack_id", "version", unique=True),
    )


class PackInstallation(SoftDeleteModel):
    """Pack installation in a client."""
    __tablename__ = "pack_installations"
    
    pack_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vertical_packs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pack_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Configuration
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    enabled_features: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    disabled_features: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    custom_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="installing", nullable=False, index=True)  # installing, installed, updating, failed, uninstalled, deprecated
    health_status: Mapped[str] = mapped_column(String(20), default="healthy", nullable=False)  # healthy, degraded, critical, unknown
    last_health_check: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Installation details
    installed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Version tracking
    installed_version: Mapped[str] = mapped_column(String(50), nullable=False)
    previous_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    auto_update: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    update_channel: Mapped[str] = mapped_column(String(20), default="stable", nullable=False)  # stable, beta, alpha
    
    # Health
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_successful_update: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Usage
    usage_stats: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Relationships
    pack: Mapped["VerticalPack"] = relationship("VerticalPack", back_populates="installations")
    version: Mapped[Optional["PackVersion"]] = relationship("PackVersion", foreign_keys=[version_id])
    installed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[installed_by_id])
    
    __table_args__ = (
        Index("ix_pack_installations_client_pack", "client_id", "pack_id", unique=True),
    )


class PackReview(SoftDeleteModel):
    """Pack review/rating."""
    __tablename__ = "pack_reviews"
    
    pack_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vertical_packs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    installation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pack_installations.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Pros/Cons
    pros: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    cons: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Verification
    is_verified_purchase: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified_installation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Moderation
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    moderated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Helpful
    helpful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unhelpful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    pack: Mapped["VerticalPack"] = relationship("VerticalPack", back_populates="reviews")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    installation: Mapped[Optional["PackInstallation"]] = relationship("PackInstallation", foreign_keys=[installation_id])
    moderated_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[moderated_by_id])
    
    __table_args__ = (
        Index("ix_pack_reviews_pack_user", "pack_id", "user_id", unique=True),
    )


# Pack Entity Definitions (for dynamic entity registration)
class PackEntity(SoftDeleteModel):
    """Entity definition from a pack."""
    __tablename__ = "pack_entities"
    
    pack_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vertical_packs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Entity definition
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Schema
    fields: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    indexes: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    relationships: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # UI
    list_fields: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    detail_fields: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    create_fields: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    edit_fields: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    filter_fields: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    sort_fields: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Permissions
    permissions: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # UI
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Registration
    is_registered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    registered_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relationships
    pack: Mapped["VerticalPack"] = relationship("VerticalPack")
    
    __table_args__ = (
        Index("ix_pack_entities_pack_slug", "pack_id", "slug", unique=True),
    )
