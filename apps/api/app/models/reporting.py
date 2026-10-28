"""
Reporting models: Reports, Templates, Schedules, Exports, Widgets.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index, Enum as SQLEnum, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from .base import SoftDeleteModel


class ReportTemplate(SoftDeleteModel):
    """Report template definition."""
    __tablename__ = "report_templates"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    vertical: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    # Structure
    sections: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Defaults
    default_filters: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    default_formats: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)  # pdf, html, csv, json, xlsx
    default_schedule: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # cron
    
    # Visual
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    preview_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Settings
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_permissions: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    changelog: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Tags
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Relationships
    reports: Mapped[List["ReportDefinition"]] = relationship("ReportDefinition", back_populates="template")
    schedules: Mapped[List["ReportSchedule"]] = relationship("ReportSchedule", back_populates="template")
    
    __table_args__ = (
        Index("ix_report_templates_client_slug", "client_id", "slug", unique=True),
    )


class ReportDefinition(SoftDeleteModel):
    """Report definition (instance of a template)."""
    __tablename__ = "report_definitions"
    
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("report_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Structure (overrides template)
    sections: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Filters
    filters: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    date_range: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Scheduling
    schedule: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # cron
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    
    # Export
    formats: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)  # pdf, html, csv, json, xlsx
    export_options: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Distribution
    recipients: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)  # emails
    slack_channels: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    webhook_urls: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Access control
    client_ids: Mapped[List[uuid.UUID]] = mapped_column(JSONB, default=list, nullable=False)  # empty = all
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    required_permissions: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)  # draft, active, paused, archived
    
    # Run tracking
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Metadata
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    vertical: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Relationships
    template: Mapped[Optional["ReportTemplate"]] = relationship("ReportTemplate", back_populates="reports")
    runs: Mapped[List["ReportRun"]] = relationship("ReportRun", back_populates="report", cascade="all, delete-orphan")
    schedules: Mapped[List["ReportSchedule"]] = relationship("ReportSchedule", back_populates="report", cascade="all, delete-orphan")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    
    __table_args__ = (
        Index("ix_report_definitions_client_status", "client_id", "status"),
        Index("ix_report_definitions_next_run", "next_run_at"),
    )


class ReportRun(SoftDeleteModel):
    """Report generation run."""
    __tablename__ = "report_runs"
    
    report_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("report_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Trigger
    triggered_by: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)  # schedule, manual, api, webhook
    triggered_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Parameters
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    filters_applied: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    date_range: Mapped[Optional[Dict[str, str]]] = mapped_column(JSONB, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)  # pending, queued, running, completed, failed, cancelled
    progress: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0, nullable=False)
    current_step: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Output
    output_files: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    # [{format, filename, url, size_bytes, checksum, expires_at}]
    
    # Stats
    widgets_rendered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    widgets_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    data_rows_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    render_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Errors
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    queued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Delivery tracking
    delivery_status: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # {email: {sent, failed}, slack: {sent, failed}, webhook: {sent, failed}}
    
    # Relationships
    report: Mapped["ReportDefinition"] = relationship("ReportDefinition", back_populates="runs")
    client: Mapped["Client"] = relationship("Client")
    triggered_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[triggered_by_user_id])
    
    __table_args__ = (
        Index("ix_report_runs_report_status", "report_id", "status"),
        Index("ix_report_runs_client_status", "client_id", "status"),
    )


class ReportSchedule(SoftDeleteModel):
    """Scheduled report."""
    __tablename__ = "report_schedules"
    
    report_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("report_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("report_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    
    # Window
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Parameters
    default_parameters: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Override distribution
    recipients: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    slack_channels: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    webhook_urls: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Metadata
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Relationships
    report: Mapped["ReportDefinition"] = relationship("ReportDefinition", back_populates="schedules")
    template: Mapped[Optional["ReportTemplate"]] = relationship("ReportTemplate", back_populates="schedules")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    
    __table_args__ = (
        Index("ix_report_schedules_next_run", "next_run_at", "is_active"),
    )


class ReportExport(SoftDeleteModel):
    """Report export file."""
    __tablename__ = "report_exports"
    
    run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("report_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    format: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf, html, csv, json, xlsx
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # File info
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA256
    
    # URLs
    download_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    download_url_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="generating", nullable=False)  # generating, ready, failed, expired
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Expiry
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    
    # Timestamps
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    run: Mapped["ReportRun"] = relationship("ReportRun")
    
    __table_args__ = (
        Index("ix_report_exports_run_format", "run_id", "format"),
    )


class ReportVersion(SoftDeleteModel):
    """Report version for version control."""
    __tablename__ = "report_versions"
    
    report_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("report_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Snapshot
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sections: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    filters: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    formats: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    schedule: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    recipients: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Metadata
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changelog: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    report: Mapped["ReportDefinition"] = relationship("ReportDefinition")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    
    __table_args__ = (
        Index("ix_report_versions_report_version", "report_id", "version", unique=True),
    )


# Widget definitions for drag-drop report builder
class WidgetDefinition(SoftDeleteModel):
    """Widget definition for report builder."""
    __tablename__ = "widget_definitions"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # kpi_card, line_chart, bar_chart, table, funnel, cohort_heatmap, etc.
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False, index=True)
    
    # Data source
    data_source: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Visual config
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    default_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Props schema
    props_schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    default_props: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Preview
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    preview_props: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Validation
    required_data: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    supported_formats: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Metadata
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    __table_args__ = (
        Index("ix_widget_definitions_client_slug", "client_id", "slug", unique=True),
        Index("ix_widget_definitions_type_category", "type", "category"),
    )
