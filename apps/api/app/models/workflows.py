"""
Workflow models: Definitions, Executions, Nodes, Edges, Triggers.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index, Enum as SQLEnum, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from .base import SoftDeleteModel


class WorkflowDefinition(SoftDeleteModel):
    """Workflow definition (visual builder)."""
    __tablename__ = "workflow_definitions"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False, index=True)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)  # draft, published, deprecated, archived
    
    # Definition (React Flow JSON)
    nodes: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    edges: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    viewport: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Triggers
    triggers: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Settings
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # {
    #   "concurrency_limit": 10,
    #   "timeout_seconds": 3600,
    #   "retry_policy": {"max_retries": 3, "backoff_seconds": 60},
    #   "error_handling": "stop" | "continue" | "retry",
    #   "notifications": {"on_failure": ["email"], "on_success": []}
    # }
    
    # Execution limits
    max_concurrent_executions: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_backoff_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    
    # Scheduling
    schedule: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # cron
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    
    # Versioning
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deprecated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    changelog: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Stats
    total_executions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_executions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_executions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_execution_time_ms: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    
    # Relationships
    executions: Mapped[List["WorkflowExecution"]] = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")
    versions: Mapped[List["WorkflowVersion"]] = relationship("WorkflowVersion", back_populates="workflow", cascade="all, delete-orphan")
    triggers_ref: Mapped[List["WorkflowTrigger"]] = relationship("WorkflowTrigger", back_populates="workflow", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_workflow_definitions_client_slug", "client_id", "slug", unique=True),
    )


class WorkflowVersion(SoftDeleteModel):
    """Workflow version for rollback/history."""
    __tablename__ = "workflow_versions"
    
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Snapshot
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nodes: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    edges: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    viewport: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    triggers: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
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
    workflow: Mapped["WorkflowDefinition"] = relationship("WorkflowDefinition", back_populates="versions")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    
    __table_args__ = (
        Index("ix_workflow_versions_workflow_version", "workflow_id", "version", unique=True),
    )


class WorkflowExecution(SoftDeleteModel):
    """Workflow execution instance."""
    __tablename__ = "workflow_executions"
    
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_triggers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Trigger data
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)  # schedule, event, api, webhook, manual
    trigger_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    trigger_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # api, webhook, scheduler, user
    
    # Context
    context: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    variables: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)  # pending, running, completed, failed, cancelled, paused, retrying
    
    # Progress
    current_node_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    completed_nodes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_nodes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0, nullable=False)
    
    # Retry
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    last_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Error handling
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_node_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_handled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Queue
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Parent/child
    parent_execution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    root_execution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Output
    output: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Revenue attribution
    revenue_attributed: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Relationships
    workflow: Mapped["WorkflowDefinition"] = relationship("WorkflowDefinition", back_populates="executions")
    trigger: Mapped[Optional["WorkflowTrigger"]] = relationship("WorkflowTrigger", foreign_keys=[trigger_id])
    node_executions: Mapped[List["WorkflowNodeExecution"]] = relationship("WorkflowNodeExecution", back_populates="execution", cascade="all, delete-orphan")
    child_executions: Mapped[List["WorkflowExecution"]] = relationship("WorkflowExecution", backref="parent_execution", remote_side="WorkflowExecution.id")
    root_execution: Mapped[Optional["WorkflowExecution"]] = relationship("WorkflowExecution", backref="child_executions", remote_side="WorkflowExecution.id", foreign_keys=[root_execution_id])
    
    __table_args__ = (
        Index("ix_workflow_executions_workflow_status", "workflow_id", "status"),
        Index("ix_workflow_executions_queued", "queued_at", "priority"),
        Index("ix_workflow_executions_root", "root_execution_id"),
    )


class WorkflowNodeExecution(SoftDeleteModel):
    """Individual node execution within a workflow."""
    __tablename__ = "workflow_node_executions"
    
    execution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)  # action, condition, delay, branch, loop, subflow, webhook
    node_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, running, completed, failed, skipped, retrying
    
    # Input/Output
    input_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    output_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Retry
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Dependencies
    depends_on: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)  # node_ids
    branch_condition: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    branch_taken: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # true, false
    
    # Subflow
    sub_execution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Relationships
    execution: Mapped["WorkflowExecution"] = relationship("WorkflowExecution", back_populates="node_executions")
    sub_execution: Mapped[Optional["WorkflowExecution"]] = relationship("WorkflowExecution", foreign_keys=[sub_execution_id])
    
    __table_args__ = (
        Index("ix_workflow_node_executions_execution", "execution_id"),
        Index("ix_workflow_node_executions_node", "node_id"),
    )


class WorkflowTrigger(SoftDeleteModel):
    """Workflow trigger definition."""
    __tablename__ = "workflow_triggers"
    
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # schedule, event, webhook, api, manual
    
    # Configuration
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # Schedule: {"cron": "0 0 * * *", "timezone": "UTC"}
    # Event: {"event_type": "order.created", "filters": {"status": "confirmed"}}
    # Webhook: {"path": "/webhook/order", "secret": "xxx", "method": "POST"}
    # API: {"endpoint": "/api/v1/workflows/trigger", "auth_required": true}
    
    # Conditions
    conditions: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Deduplication
    deduplication_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deduplication_window_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Rate limiting
    rate_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # per minute
    rate_limit_window: Mapped[int] = mapped_column(Integer, default=60, nullable=False)  # seconds
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_webhook_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Stats
    total_triggers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_triggers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_triggers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    workflow: Mapped["WorkflowDefinition"] = relationship("WorkflowDefinition", back_populates="triggers_ref")
    executions: Mapped[List["WorkflowExecution"]] = relationship("WorkflowExecution", back_populates="trigger")
    
    __table_args__ = (
        Index("ix_workflow_triggers_workflow_active", "workflow_id", "is_active"),
    )
