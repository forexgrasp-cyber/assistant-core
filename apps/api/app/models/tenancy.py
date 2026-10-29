"""
Multi-tenancy models: Platform, Agency, Client, ClientUser.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index, Enum as SQLEnum, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from .base import BaseModel, TenantModel


class Platform(BaseModel):
    """Platform (top-level tenant - the SaaS platform itself)."""
    __tablename__ = "platforms"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    agencies: Mapped[List["Agency"]] = relationship("Agency", back_populates="platform", cascade="all, delete-orphan")


class Agency(BaseModel):
    """Agency (mid-level tenant - the customer of the platform)."""
    __tablename__ = "agencies"
    
    platform_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("platforms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # White-label settings
    white_label_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    white_label_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    white_label_logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    white_label_favicon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # hex color
    secondary_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    custom_css: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Settings
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Billing
    billing_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subscription_status: Mapped[str] = mapped_column(String(50), default="trial", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Owner
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Relationships
    platform: Mapped["Platform"] = relationship("Platform", back_populates="agencies")
    users: Mapped[List["User"]] = relationship("User", back_populates="agency", foreign_keys="User.agency_id")
    clients: Mapped[List["Client"]] = relationship("Client", back_populates="agency", cascade="all, delete-orphan")
    owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[owner_id], back_populates="owned_agency")
    
    __table_args__ = (
        Index("ix_agencies_platform_slug", "platform_id", "slug", unique=True),
        Index("ix_agencies_white_label_domain", "white_label_domain", unique=True),
    )


class Client(BaseModel):
    """Client (sub-tenant - the agency's customer)."""
    __tablename__ = "clients"
    
    agency_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agencies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    shop_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Settings
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Attribution config
    attribution_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_onboarded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    onboarded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Attribution defaults
    attribution_click_window_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    attribution_open_window_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    attribution_model: Mapped[str] = mapped_column(String(50), default="last_click", nullable=False)
    
    # Relationships
    agency: Mapped["Agency"] = relationship("Agency", back_populates="clients")
    users: Mapped[List["ClientUser"]] = relationship("ClientUser", back_populates="client", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_clients_agency_slug", "agency_id", "slug", unique=True),
    )


class ClientUser(BaseModel):
    """User with access to a specific client (client-level staff)."""
    __tablename__ = "client_users"
    
    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(50), default="viewer", nullable=False)
    permissions: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    invited_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="users")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    invited_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[invited_by_id])
    
    __table_args__ = (
        Index("ix_client_users_client_user", "client_id", "user_id", unique=True),
    )
