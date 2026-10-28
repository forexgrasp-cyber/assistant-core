"""
Audit and compliance models: Audit logs, GDPR, Consent, DPA, Encryption keys.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index, Enum as SQLEnum, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from .base import SoftDeleteModel


class AuditLog(SoftDeleteModel):
    """Immutable audit log for all critical operations."""
    __tablename__ = "audit_logs"
    
    # Actor
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    impersonated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Session
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    api_key_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Request context
    request_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referrer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Action
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # create, read, update, delete, export, login, logout, permission_change
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    resource_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Changes
    old_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    changed_fields: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Result
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False, index=True)  # success, failure, partial
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Risk
    risk_level: Mapped[str] = mapped_column(String(20), default="low", nullable=False)  # low, medium, high, critical
    risk_score: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0, nullable=False)
    
    # Compliance
    requires_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Cryptographic integrity
    hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256 of log entry
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    hash_chain_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])
    impersonated_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[impersonated_by_id])
    session: Mapped[Optional["Session"]] = relationship("Session", foreign_keys=[session_id])
    api_key: Mapped[Optional["ApiKey"]] = relationship("ApiKey", foreign_keys=[api_key_id])
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_id])
    
    __table_args__ = (
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_status_timestamp", "status", "timestamp"),
        Index("ix_audit_logs_hash_chain", "hash", "previous_hash"),
    )


class GDPRRequest(SoftDeleteModel):
    """GDPR/CCPA data subject request."""
    __tablename__ = "gdpr_requests"
    
    # Request type
    request_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # access, rectification, erasure, restriction, portability, objection, automated_decision
    
    # Subject
    subject_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    subject_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Verification
    verification_token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    verification_token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # email, sms, manual
    
    # Scope
    scope: Mapped[str] = mapped_column(String(50), default="all", nullable=False)  # all, specific, custom
    scope_details: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="submitted", nullable=False, index=True)  # submitted, verified, processing, completed, rejected, expired
    priority: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)  # low, normal, high, urgent
    
    # Processing
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    
    # Results
    data_provided: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    data_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    data_rectified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    data_exported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    export_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    export_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Files
    attached_files: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    export_files: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Communication
    communication_log: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Timestamps
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    assigned_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_id])
    
    __table_args__ = (
        Index("ix_gdpr_requests_status_due", "status", "due_at"),
        Index("ix_gdpr_requests_subject", "subject_email"),
    )


class ConsentRecord(SoftDeleteModel):
    """Granular consent record for GDPR/ePrivacy."""
    __tablename__ = "consent_records"
    
    # Subject
    subject_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    subject_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    subject_type: Mapped[str] = mapped_column(String(50), default="customer", nullable=False)  # customer, user, lead, visitor
    
    # Consent details
    purpose: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # marketing_email, marketing_sms, analytics, personalization, profiling, third_party_sharing
    purpose_category: Mapped[str] = mapped_column(String(50), default="marketing", nullable=False, index=True)  # necessary, preferences, statistics, marketing
    lawful_basis: Mapped[str] = mapped_column(String(50), default="consent", nullable=False)  # consent, contract, legal_obligation, vital_interests, public_task, legitimate_interests
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="granted", nullable=False, index=True)  # granted, denied, withdrawn, expired
    is_explicit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_informed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_freely_given: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_specific: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Granularity
    granular_consents: Mapped[Dict[str, bool]] = mapped_column(JSONB, default=dict, nullable=False)  # {"email": true, "sms": false, "analytics": true}
    
    # Context
    source: Mapped[str] = mapped_column(String(50), default="direct", nullable=False)  # direct, form, import, api, checkout, signup
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_referrer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )
    form_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Version
    consent_version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)
    privacy_policy_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    terms_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Evidence
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    consent_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # exact text shown to user
    consent_method: Mapped[str] = mapped_column(String(50), default="checkbox", nullable=False)  # checkbox, toggle, button, signature, verbal
    
    # Withdrawal
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawal_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # link, email, phone, api, admin
    withdrawal_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    withdrawal_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    
    # Expiry
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    renewal_reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    renewal_reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Validation
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    validation_errors: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Timestamps
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship("Customer", foreign_keys="Customer.email==ConsentRecord.subject_email")
    
    __table_args__ = (
        Index("ix_consent_records_subject_purpose", "subject_email", "purpose"),
        Index("ix_consent_records_status_purpose", "status", "purpose"),
        Index("ix_consent_records_expires", "expires_at"),
    )


class DataProcessingAgreement(SoftDeleteModel):
    """Data Processing Agreement (DPA) with subprocessors."""
    __tablename__ = "data_processing_agreements"
    
    # Parties
    controller_name: Mapped[str] = mapped_column(String(255), nullable=False)
    controller_email: Mapped[str] = mapped_column(String(255), nullable=False)
    processor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    processor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Agreement
    agreement_version: Mapped[str] = mapped_column(String(50), nullable=False)
    agreement_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_by_controller: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    signed_by_processor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Scope
    processing_purposes: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    data_categories: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    data_subject_categories: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    processing_operations: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Technical measures
    encryption_at_rest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    encryption_in_transit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    access_controls: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    audit_logging: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    data_minimization: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    pseudonymization: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Subprocessors
    subprocessors: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    subprocessor_notification: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    subprocessor_consent_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # International transfers
    international_transfers: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transfer_mechanisms: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)  # adequacy, scc, bcr, derogation
    transfer_countries: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Rights
    data_subject_rights: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    breach_notification_hours: Mapped[int] = mapped_column(Integer, default=72, nullable=False)
    
    # Duration
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notice_period_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)  # draft, active, expired, terminated
    termination_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Documents
    documents: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Review
    review_frequency_months: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    reviewed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Relationships
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_id])
    
    __table_args__ = (
        Index("ix_dpa_status_next_review", "status", "next_review_at"),
    )


class EncryptionKey(SoftDeleteModel):
    """Encryption key management."""
    __tablename__ = "encryption_keys"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    
    # Key details
    algorithm: Mapped[str] = mapped_column(String(50), default="AES-256-GCM", nullable=False)
    key_length: Mapped[int] = mapped_column(Integer, default=256, nullable=False)
    
    # Key material (encrypted)
    key_material_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # KMS
    kms_provider: Mapped[str] = mapped_column(String(50), default="aws_kms", nullable=False)  # aws_kms, gcp_kms, azure_kms, hashicorp_vault, local
    kms_key_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    kms_key_arn: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Purpose
    purpose: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # database, files, pii, secrets, backups, analytics
    scope: Mapped[str] = mapped_column(String(50), default="platform", nullable=False)  # platform, client, tenant
    
    # Rotation
    rotation_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rotation_interval_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    last_rotated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_rotation_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    rotation_notification_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    
    # Backup
    backup_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    backup_key_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    backup_location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)  # active, deprecated, compromised, destroyed, backup
    deprecated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    destroyed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    destruction_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Usage tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    rotations: Mapped[List["KeyRotationLog"]] = relationship("KeyRotationLog", back_populates="key", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_encryption_keys_purpose_status", "purpose", "status"),
        Index("ix_encryption_keys_rotation", "next_rotation_at"),
    )


class KeyRotationLog(SoftDeleteModel):
    """Key rotation audit log."""
    __tablename__ = "key_rotation_logs"
    
    key_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("encryption_keys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Rotation details
    old_key_id: Mapped[str] = mapped_column(String(255), nullable=False)
    new_key_id: Mapped[str] = mapped_column(String(255), nullable=False)
    old_version: Mapped[int] = mapped_column(Integer, nullable=False)
    new_version: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Trigger
    trigger: Mapped[str] = mapped_column(String(50), nullable=False)  # scheduled, manual, emergency, compromised, policy_change
    triggered_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Process
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, in_progress, completed, failed, rolled_back
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Re-encryption
    items_reencrypted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reencryption_errors: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Verification
    verification_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Rollback
    rolled_back: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rolled_back_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rollback_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    key: Mapped["EncryptionKey"] = relationship("EncryptionKey", back_populates="rotations")
    triggered_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[triggered_by_id])
    verified_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[verified_by_id])
    
    __table_args__ = (
        Index("ix_key_rotation_logs_key_status", "key_id", "status"),
        Index("ix_key_rotation_logs_started", "started_at"),
    )
