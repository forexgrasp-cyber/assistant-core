"""
Data Residency Service for Retention Analytics Platform.

Implements multi-region data isolation and cross-region replication for
GDPR (EU), CCPA (US), and other data sovereignty requirements.

Leverages shared-canonical-services:
- unified_monitoring for region health and replication status
- immutable_audit_log for tamper-proof residency audit trails
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import structlog

from retention_analytics_core.service_base import CanonicalService, ServiceResponse

log = structlog.get_logger(__name__)


class Region(StrEnum):
    """Supported deployment regions."""
    US_EAST_1 = "us-east-1"
    US_WEST_2 = "us-west-2"
    EU_WEST_1 = "eu-west-1"
    EU_CENTRAL_1 = "eu-central-1"
    AP_SOUTHEAST_1 = "ap-southeast-1"
    AP_NORTHEAST_1 = "ap-northeast-1"


class DataClassification(StrEnum):
    """Data classification for residency rules."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"  # PHI, PII, financial
    SOVEREIGN = "sovereign"    # Must stay in specific jurisdiction


class ReplicationStatus(StrEnum):
    """Replication status."""
    HEALTHY = "healthy"
    LAGGING = "lagging"
    FAILED = "failed"
    PAUSED = "paused"
    INITIALIZING = "initializing"


class ResidencyRuleType(StrEnum):
    """Types of residency rules."""
    STORE_IN_REGION = "store_in_region"           # Data must be stored in specific region
    PROCESS_IN_REGION = "process_in_region"       # Processing must occur in region
    BACKUP_IN_REGION = "backup_in_region"         # Backups must be in region
    NO_CROSS_BORDER = "no_cross_border"           # No cross-border transfer allowed
    ENCRYPTION_REQUIRED = "encryption_required"   # Encryption required for cross-region


@dataclass
class DataResidencyRule:
    """A data residency rule for a tenant/data type."""
    rule_id: str
    tenant_id: str
    name: str
    description: str
    data_classification: DataClassification
    rule_type: ResidencyRuleType
    allowed_regions: list[Region]
    required_region: Region | None = None
    forbidden_regions: list[Region] = field(default_factory=list)
    encryption_required: bool = True
    applies_to: list[str] = field(default_factory=list)  # table names, stream names, etc.
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    active: bool = True


@dataclass
class RegionDeployment:
    """A region deployment configuration."""
    deployment_id: str
    region: Region
    name: str
    primary: bool = False
    status: str = "active"  # active, standby, maintenance, decommissioned
    capacity: dict[str, Any] = field(default_factory=dict)  # compute, storage, network
    services: list[str] = field(default_factory=list)  # deployed services
    compliance_certifications: list[str] = field(default_factory=list)  # SOC2, HIPAA, GDPR
    data_types_supported: list[DataClassification] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_health_check: str | None = None


@dataclass
class ReplicationConfig:
    """Cross-region replication configuration."""
    config_id: str
    source_region: Region
    target_region: Region
    data_types: list[DataClassification]
    replication_mode: str = "async"  # async, sync, semi-sync
    rpo_seconds: int = 300  # Recovery Point Objective
    rto_seconds: int = 3600  # Recovery Time Objective
    status: ReplicationStatus = ReplicationStatus.INITIALIZING
    lag_seconds: float = 0.0
    last_sync: str | None = None
    error_message: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class TenantResidencyProfile:
    """A tenant's data residency configuration."""
    profile_id: str
    tenant_id: str
    primary_region: Region
    allowed_regions: list[Region]
    data_classification_overrides: dict[str, DataClassification] = field(default_factory=dict)
    custom_rules: list[DataResidencyRule] = field(default_factory=list)
    backup_regions: list[Region] = field(default_factory=list)
    disaster_recovery_region: Region | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class ResidencyAuditEvent:
    """Audit event for data residency compliance."""
    event_id: str
    timestamp: str
    tenant_id: str
    event_type: str  # data_created, data_moved, data_accessed, rule_violation, replication_lag
    region: Region
    data_classification: DataClassification
    resource_type: str
    resource_id: str
    details: dict[str, Any] = field(default_factory=dict)
    compliant: bool = True
    violation_reason: str | None = None


class DataResidencyService(CanonicalService):
    """
    Data Residency Service for multi-region deployments.

    Provides:
    - Region deployment management
    - Data residency rules per tenant/classification
    - Cross-region replication configuration and monitoring
    - Tenant residency profiles
    - Residency audit trail
    - Compliance reporting (GDPR, CCPA, etc.)
    """

    SERVICE_NAME = "data_residency"
    VERSION = "1.0.0"

    # Default region capabilities
    REGION_CAPABILITIES = {
        Region.US_EAST_1: {
            "compliance": ["SOC2", "HIPAA", "CCPA"],
            "data_types": [DataClassification.PUBLIC, DataClassification.INTERNAL, DataClassification.CONFIDENTIAL, DataClassification.RESTRICTED],
            "capacity": {"compute": "high", "storage": "high", "network": "high"},
        },
        Region.US_WEST_2: {
            "compliance": ["SOC2", "HIPAA", "CCPA"],
            "data_types": [DataClassification.PUBLIC, DataClassification.INTERNAL, DataClassification.CONFIDENTIAL, DataClassification.RESTRICTED],
            "capacity": {"compute": "high", "storage": "high", "network": "high"},
        },
        Region.EU_WEST_1: {
            "compliance": ["SOC2", "GDPR", "ISO27001"],
            "data_types": [DataClassification.PUBLIC, DataClassification.INTERNAL, DataClassification.CONFIDENTIAL, DataClassification.RESTRICTED, DataClassification.SOVEREIGN],
            "capacity": {"compute": "high", "storage": "high", "network": "high"},
        },
        Region.EU_CENTRAL_1: {
            "compliance": ["SOC2", "GDPR", "ISO27001"],
            "data_types": [DataClassification.PUBLIC, DataClassification.INTERNAL, DataClassification.CONFIDENTIAL, DataClassification.RESTRICTED, DataClassification.SOVEREIGN],
            "capacity": {"compute": "medium", "storage": "high", "network": "high"},
        },
        Region.AP_SOUTHEAST_1: {
            "compliance": ["SOC2", "ISO27001", "PDPA"],
            "data_types": [DataClassification.PUBLIC, DataClassification.INTERNAL, DataClassification.CONFIDENTIAL, DataClassification.RESTRICTED],
            "capacity": {"compute": "medium", "storage": "medium", "network": "high"},
        },
        Region.AP_NORTHEAST_1: {
            "compliance": ["SOC2", "ISO27001", "APPI"],
            "data_types": [DataClassification.PUBLIC, DataClassification.INTERNAL, DataClassification.CONFIDENTIAL, DataClassification.RESTRICTED],
            "capacity": {"compute": "medium", "storage": "medium", "network": "high"},
        },
    }

    def __init__(
        self,
        registry: Any = None,
        dry_run: bool = False,
        tenant_id: str | None = None,
    ) -> None:
        super().__init__(
            name="data_residency",
            registry=registry,
            version=self.VERSION,
            tenant_id=tenant_id,
            dry_run=dry_run,
        )
        self.registry = registry
        self._rules: dict[str, DataResidencyRule] = {}
        self._deployments: dict[str, RegionDeployment] = {}
        self._replication_configs: dict[str, ReplicationConfig] = {}
        self._tenant_profiles: dict[str, TenantResidencyProfile] = {}
        self._audit_events: dict[str, ResidencyAuditEvent] = {}
        self._initialize_default_deployments()
        # Don't call _register_actions here - main.py will call register() which calls it

    def _register_actions(self) -> None:
        if not self.registry:
            return
        # Use the same service name that main.py registers us with
        reg = self.registry.register("data_residency", version=self.VERSION, metadata={"domain": "compliance", "type": "platform"})
        reg.actions["manage_rule"] = self.manage_rule
        reg.actions["list_rules"] = self.list_rules
        reg.actions["manage_deployment"] = self.manage_deployment
        reg.actions["list_deployments"] = self.list_deployments
        reg.actions["manage_replication"] = self.manage_replication
        reg.actions["list_replications"] = self.list_replications
        reg.actions["manage_tenant_profile"] = self.manage_tenant_profile
        reg.actions["get_tenant_profile"] = self.get_tenant_profile
        reg.actions["validate_residency"] = self.validate_residency
        reg.actions["log_audit_event"] = self.log_audit_event
        reg.actions["get_audit_events"] = self.get_audit_events
        reg.actions["generate_compliance_report"] = self.generate_compliance_report
        reg.actions["check_replication_health"] = self.check_replication_health

    def register(
        self,
        subscribes_to: list | None = None,
        metadata: dict[str, Any] | None = None,
        service_type: str = "platform",
    ) -> None:
        """Register this service's actions with the platform registry."""
        # Don't call parent register - main.py already registers the service
        # Just register our actions
        self._register_actions()

    def _initialize_default_deployments(self) -> None:
        """Initialize default region deployments."""
        for region, caps in self.REGION_CAPABILITIES.items():
            deployment = RegionDeployment(
                deployment_id=f"deploy-{region.value}",
                region=region,
                name=f"Primary {region.value.upper()}",
                primary=(region == Region.US_EAST_1),
                compliance_certifications=caps["compliance"],
                data_types_supported=caps["data_types"],
                capacity=caps["capacity"],
                services=["api", "workers", "database", "cache", "monitoring"],
            )
            self._deployments[deployment.deployment_id] = deployment

        # Set up default replication from US-EAST-1 to US-WEST-2 and EU-WEST-1
        default_replications = [
            (Region.US_EAST_1, Region.US_WEST_2, [DataClassification.PUBLIC, DataClassification.INTERNAL, DataClassification.CONFIDENTIAL]),
            (Region.US_EAST_1, Region.EU_WEST_1, [DataClassification.PUBLIC, DataClassification.INTERNAL]),
        ]
        for source, target, data_types in default_replications:
            config = ReplicationConfig(
                config_id=f"repl-{source.value}-to-{target.value}",
                source_region=source,
                target_region=target,
                data_types=data_types,
                replication_mode="async",
                rpo_seconds=300,
                rto_seconds=3600,
            )
            self._replication_configs[config.config_id] = config

    # ── Rule Management ──

    async def manage_rule(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create, update, or delete a residency rule."""
        action = params.get("action", "create")
        rule_id = params.get("rule_id")

        if action == "create":
            rule = DataResidencyRule(
                rule_id=f"rule-{uuid.uuid4().hex[:12]}",
                tenant_id=params.get("tenant_id", ""),
                name=params.get("name", ""),
                description=params.get("description", ""),
                data_classification=DataClassification(params.get("data_classification", "confidential")),
                rule_type=ResidencyRuleType(params.get("rule_type", "store_in_region")),
                allowed_regions=[Region(r) for r in params.get("allowed_regions", [])],
                required_region=Region(params["required_region"]) if params.get("required_region") else None,
                forbidden_regions=[Region(r) for r in params.get("forbidden_regions", [])],
                encryption_required=params.get("encryption_required", True),
                applies_to=params.get("applies_to", []),
            )
            self._rules[rule.rule_id] = rule
            return {"status": "ok", "rule_id": rule.rule_id, "action": "created"}

        elif action in ("update", "delete"):
            rule = self._rules.get(rule_id)
            if not rule:
                return {"status": "error", "message": f"Rule {rule_id} not found"}

            if action == "delete":
                del self._rules[rule_id]
                return {"status": "ok", "rule_id": rule_id, "action": "deleted"}

            updates = params.get("updates", {})
            for key, value in updates.items():
                if hasattr(rule, key) and key != "rule_id":
                    if key in ("allowed_regions", "forbidden_regions"):
                        value = [Region(r) for r in value]
                    elif key == "required_region" and value:
                        value = Region(value)
                    elif key == "data_classification":
                        value = DataClassification(value)
                    elif key == "rule_type":
                        value = ResidencyRuleType(value)
                    setattr(rule, key, value)

            rule.updated_at = datetime.now(UTC).isoformat()
            return {"status": "ok", "rule_id": rule_id, "action": "updated"}

        return {"status": "error", "message": f"Invalid action: {action}"}

    async def list_rules(self, params: dict[str, Any]) -> dict[str, Any]:
        """List residency rules with filtering."""
        tenant_id = params.get("tenant_id")
        data_classification = params.get("data_classification")
        active_only = params.get("active_only", True)

        rules = list(self._rules.values())

        if tenant_id:
            rules = [r for r in rules if r.tenant_id == tenant_id]
        if data_classification:
            rules = [r for r in rules if r.data_classification.value == data_classification]
        if active_only:
            rules = [r for r in rules if r.active]

        return {
            "status": "ok",
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "tenant_id": r.tenant_id,
                    "name": r.name,
                    "data_classification": r.data_classification.value,
                    "rule_type": r.rule_type.value,
                    "allowed_regions": [reg.value for reg in r.allowed_regions],
                    "required_region": r.required_region.value if r.required_region else None,
                    "forbidden_regions": [reg.value for reg in r.forbidden_regions],
                    "encryption_required": r.encryption_required,
                    "active": r.active,
                }
                for r in rules
            ],
        }

    # ── Deployment Management ──

    async def manage_deployment(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create, update, or delete a region deployment."""
        action = params.get("action", "create")
        deployment_id = params.get("deployment_id")

        if action == "create":
            deployment = RegionDeployment(
                deployment_id=f"deploy-{uuid.uuid4().hex[:12]}",
                region=Region(params.get("region")),
                name=params.get("name", ""),
                primary=params.get("primary", False),
                compliance_certifications=params.get("compliance_certifications", []),
                data_types_supported=[DataClassification(d) for d in params.get("data_types_supported", [])],
                capacity=params.get("capacity", {}),
                services=params.get("services", []),
            )
            self._deployments[deployment.deployment_id] = deployment
            return {"status": "ok", "deployment_id": deployment.deployment_id, "action": "created"}

        elif action in ("update", "delete"):
            deployment = self._deployments.get(deployment_id)
            if not deployment:
                return {"status": "error", "message": f"Deployment {deployment_id} not found"}

            if action == "delete":
                del self._deployments[deployment_id]
                return {"status": "ok", "deployment_id": deployment_id, "action": "deleted"}

            updates = params.get("updates", {})
            for key, value in updates.items():
                if hasattr(deployment, key) and key != "deployment_id":
                    if key in ("compliance_certifications", "services"):
                        pass  # list types
                    elif key == "data_types_supported":
                        value = [DataClassification(d) for d in value]
                    elif key == "region":
                        value = Region(value)
                    setattr(deployment, key, value)

            return {"status": "ok", "deployment_id": deployment_id, "action": "updated"}

        return {"status": "error", "message": f"Invalid action: {action}"}

    async def list_deployments(self, params: dict[str, Any]) -> dict[str, Any]:
        """List region deployments."""
        region = params.get("region")
        status = params.get("status")

        deployments = list(self._deployments.values())

        if region:
            deployments = [d for d in deployments if d.region.value == region]
        if status:
            deployments = [d for d in deployments if d.status == status]

        return {
            "status": "ok",
            "deployments": [
                {
                    "deployment_id": d.deployment_id,
                    "region": d.region.value,
                    "name": d.name,
                    "primary": d.primary,
                    "status": d.status,
                    "compliance_certifications": d.compliance_certifications,
                    "data_types_supported": [dt.value for dt in d.data_types_supported],
                    "capacity": d.capacity,
                    "services": d.services,
                }
                for d in deployments
            ],
        }

    # ── Replication Management ──

    async def manage_replication(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create, update, or delete a replication configuration."""
        action = params.get("action", "create")
        config_id = params.get("config_id")

        if action == "create":
            config = ReplicationConfig(
                config_id=f"repl-{uuid.uuid4().hex[:12]}",
                source_region=Region(params.get("source_region")),
                target_region=Region(params.get("target_region")),
                data_types=[DataClassification(d) for d in params.get("data_types", [])],
                replication_mode=params.get("replication_mode", "async"),
                rpo_seconds=params.get("rpo_seconds", 300),
                rto_seconds=params.get("rto_seconds", 3600),
            )
            self._replication_configs[config.config_id] = config
            return {"status": "ok", "config_id": config.config_id, "action": "created"}

        elif action in ("update", "delete", "pause", "resume"):
            config = self._replication_configs.get(config_id)
            if not config:
                return {"status": "error", "message": f"Replication config {config_id} not found"}

            if action == "delete":
                del self._replication_configs[config_id]
                return {"status": "ok", "config_id": config_id, "action": "deleted"}

            elif action == "pause":
                config.status = ReplicationStatus.PAUSED
                config.updated_at = datetime.now(UTC).isoformat()
                return {"status": "ok", "config_id": config_id, "action": "paused"}

            elif action == "resume":
                config.status = ReplicationStatus.INITIALIZING
                config.updated_at = datetime.now(UTC).isoformat()
                return {"status": "ok", "config_id": config_id, "action": "resumed"}

            updates = params.get("updates", {})
            for key, value in updates.items():
                if hasattr(config, key) and key != "config_id":
                    if key in ("source_region", "target_region"):
                        value = Region(value)
                    elif key == "data_types":
                        value = [DataClassification(d) for d in value]
                    elif key == "replication_mode":
                        pass
                    elif key == "status":
                        value = ReplicationStatus(value)
                    setattr(config, key, value)

            config.updated_at = datetime.now(UTC).isoformat()
            return {"status": "ok", "config_id": config_id, "action": "updated"}

        return {"status": "error", "message": f"Invalid action: {action}"}

    async def list_replications(self, params: dict[str, Any]) -> dict[str, Any]:
        """List replication configurations."""
        source_region = params.get("source_region")
        target_region = params.get("target_region")
        status = params.get("status")

        configs = list(self._replication_configs.values())

        if source_region:
            configs = [c for c in configs if c.source_region.value == source_region]
        if target_region:
            configs = [c for c in configs if c.target_region.value == target_region]
        if status:
            configs = [c for c in configs if c.status.value == status]

        return {
            "status": "ok",
            "replications": [
                {
                    "config_id": c.config_id,
                    "source_region": c.source_region.value,
                    "target_region": c.target_region.value,
                    "data_types": [dt.value for dt in c.data_types],
                    "replication_mode": c.replication_mode,
                    "rpo_seconds": c.rpo_seconds,
                    "rto_seconds": c.rto_seconds,
                    "status": c.status.value,
                    "lag_seconds": c.lag_seconds,
                    "last_sync": c.last_sync,
                    "error_message": c.error_message,
                }
                for c in configs
            ],
        }

    # ── Tenant Profile Management ──

    async def manage_tenant_profile(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create or update a tenant residency profile."""
        action = params.get("action", "create")
        tenant_id = params.get("tenant_id")

        if not tenant_id:
            return {"status": "error", "message": "tenant_id required"}

        if action == "create":
            profile = TenantResidencyProfile(
                profile_id=f"prof-{uuid.uuid4().hex[:12]}",
                tenant_id=tenant_id,
                primary_region=Region(params.get("primary_region", "us-east-1")),
                allowed_regions=[Region(r) for r in params.get("allowed_regions", ["us-east-1"])],
                backup_regions=[Region(r) for r in params.get("backup_regions", [])],
                disaster_recovery_region=Region(params["disaster_recovery_region"]) if params.get("disaster_recovery_region") else None,
            )
            # Add custom rules if provided
            for rule_data in params.get("custom_rules", []):
                rule = DataResidencyRule(
                    rule_id=f"rule-{uuid.uuid4().hex[:12]}",
                    tenant_id=tenant_id,
                    name=rule_data.get("name", ""),
                    description=rule_data.get("description", ""),
                    data_classification=DataClassification(rule_data.get("data_classification", "confidential")),
                    rule_type=ResidencyRuleType(rule_data.get("rule_type", "store_in_region")),
                    allowed_regions=[Region(r) for r in rule_data.get("allowed_regions", [])],
                    required_region=Region(rule_data["required_region"]) if rule_data.get("required_region") else None,
                    forbidden_regions=[Region(r) for r in rule_data.get("forbidden_regions", [])],
                    encryption_required=rule_data.get("encryption_required", True),
                    applies_to=rule_data.get("applies_to", []),
                )
                profile.custom_rules.append(rule)

            self._tenant_profiles[tenant_id] = profile
            return {"status": "ok", "profile_id": profile.profile_id, "action": "created"}

        elif action in ("update", "delete"):
            profile = self._tenant_profiles.get(tenant_id)
            if not profile:
                return {"status": "error", "message": f"Profile for tenant {tenant_id} not found"}

            if action == "delete":
                del self._tenant_profiles[tenant_id]
                return {"status": "ok", "tenant_id": tenant_id, "action": "deleted"}

            updates = params.get("updates", {})
            for key, value in updates.items():
                if hasattr(profile, key) and key != "profile_id":
                    if key in ("allowed_regions", "backup_regions"):
                        value = [Region(r) for r in value]
                    elif key == "primary_region":
                        value = Region(value)
                    elif key == "disaster_recovery_region" and value:
                        value = Region(value)
                    elif key == "data_classification_overrides":
                        value = {k: DataClassification(v) for k, v in value.items()}
                    setattr(profile, key, value)

            profile.updated_at = datetime.now(UTC).isoformat()
            return {"status": "ok", "tenant_id": tenant_id, "action": "updated"}

        return {"status": "error", "message": f"Invalid action: {action}"}

    async def get_tenant_profile(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get a tenant's residency profile."""
        tenant_id = params.get("tenant_id")
        profile = self._tenant_profiles.get(tenant_id)

        if not profile:
            return {"status": "error", "message": f"Profile for tenant {tenant_id} not found"}

        return {
            "status": "ok",
            "profile": {
                "profile_id": profile.profile_id,
                "tenant_id": profile.tenant_id,
                "primary_region": profile.primary_region.value,
                "allowed_regions": [r.value for r in profile.allowed_regions],
                "backup_regions": [r.value for r in profile.backup_regions],
                "disaster_recovery_region": profile.disaster_recovery_region.value if profile.disaster_recovery_region else None,
                "data_classification_overrides": {k: v.value for k, v in profile.data_classification_overrides.items()},
                "custom_rules_count": len(profile.custom_rules),
                "created_at": profile.created_at,
                "updated_at": profile.updated_at,
            },
        }

    # ── Residency Validation ──

    async def validate_residency(self, params: dict[str, Any]) -> dict[str, Any]:
        """Validate if a data operation complies with residency rules."""
        tenant_id = params.get("tenant_id")
        region = Region(params.get("region"))
        data_classification = DataClassification(params.get("data_classification", "confidential"))
        resource_type = params.get("resource_type", "")
        resource_id = params.get("resource_id", "")
        operation = params.get("operation", "store")  # store, process, backup, access

        # Get tenant profile
        profile = self._tenant_profiles.get(tenant_id)

        # Get applicable rules
        rules = [r for r in self._rules.values() if r.tenant_id == tenant_id and r.active]
        if profile:
            rules.extend(profile.custom_rules)

        # Filter rules for this data classification
        applicable_rules = [r for r in rules if r.data_classification == data_classification or r.data_classification == DataClassification.PUBLIC]

        violations = []
        compliant = True

        for rule in applicable_rules:
            # Check required region
            if rule.required_region and rule.required_region != region:
                violations.append({
                    "rule_id": rule.rule_id,
                    "violation": f"Data must be stored in {rule.required_region.value}, not {region.value}",
                    "rule_type": rule.rule_type.value,
                })
                compliant = False

            # Check forbidden regions
            if region in rule.forbidden_regions:
                violations.append({
                    "rule_id": rule.rule_id,
                    "violation": f"Region {region.value} is forbidden for this data",
                    "rule_type": rule.rule_type.value,
                })
                compliant = False

            # Check allowed regions
            if rule.allowed_regions and region not in rule.allowed_regions:
                violations.append({
                    "rule_id": rule.rule_id,
                    "violation": f"Region {region.value} not in allowed regions: {[r.value for r in rule.allowed_regions]}",
                    "rule_type": rule.rule_type.value,
                })
                compliant = False

            # Check encryption requirement
            if rule.encryption_required and not params.get("encrypted", True):
                violations.append({
                    "rule_id": rule.rule_id,
                    "violation": "Encryption required but not enabled",
                    "rule_type": rule.rule_type.value,
                })
                compliant = False

        # If no specific rules, check tenant profile allowed regions
        if not applicable_rules and profile:
            if region not in profile.allowed_regions:
                violations.append({
                    "violation": f"Region {region.value} not in tenant allowed regions: {[r.value for r in profile.allowed_regions]}",
                    "rule_type": "tenant_profile",
                })
                compliant = False

        # Log audit event
        await self.log_audit_event({
            "tenant_id": tenant_id,
            "event_type": f"residency_check_{operation}",
            "region": region.value,
            "data_classification": data_classification.value,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": {
                "operation": operation,
                "compliant": compliant,
                "violations": violations,
            },
            "compliant": compliant,
        })

        return {
            "status": "ok",
            "compliant": compliant,
            "violations": violations,
            "tenant_id": tenant_id,
            "region": region.value,
            "data_classification": data_classification.value,
            "checked_at": datetime.now(UTC).isoformat(),
        }

    # ── Audit Events ──

    async def log_audit_event(self, params: dict[str, Any]) -> dict[str, Any]:
        """Log a residency audit event."""
        event = ResidencyAuditEvent(
            event_id=f"audit-{uuid.uuid4().hex[:12]}",
            timestamp=params.get("timestamp", datetime.now(UTC).isoformat()),
            tenant_id=params.get("tenant_id", ""),
            event_type=params.get("event_type", ""),
            region=Region(params.get("region")),
            data_classification=DataClassification(params.get("data_classification", "confidential")),
            resource_type=params.get("resource_type", ""),
            resource_id=params.get("resource_id", ""),
            details=params.get("details", {}),
            compliant=params.get("compliant", True),
            violation_reason=params.get("violation_reason"),
        )

        self._audit_events[event.event_id] = event

        # Also log to immutable audit log
        try:
            from shared.audit.immutable_audit_log import get_audit_log
            audit_log = get_audit_log()
            audit_log.log_event(
                event_type="data_residency",
                actor_id=params.get("actor_id", "system"),
                tenant_id=params.get("tenant_id", "system"),
                resource_type="data_residency_audit",
                resource_id=event.event_id,
                action=params.get("event_type", "check"),
                details={
                    "region": params.get("region"),
                    "data_classification": params.get("data_classification"),
                    "compliant": params.get("compliant", True),
                    "event_type": params.get("event_type"),
                },
            )
        except ImportError:
            pass

        return {"status": "ok", "event_id": event.event_id}

    async def get_audit_events(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get residency audit events with filtering."""
        tenant_id = params.get("tenant_id")
        event_type = params.get("event_type")
        region = params.get("region")
        compliant = params.get("compliant")
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        limit = params.get("limit", 100)

        events = list(self._audit_events.values())

        if tenant_id:
            events = [e for e in events if e.tenant_id == tenant_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if region:
            events = [e for e in events if e.region.value == region]
        if compliant is not None:
            events = [e for e in events if e.compliant == compliant]
        if start_date:
            events = [e for e in events if e.timestamp >= start_date]
        if end_date:
            events = [e for e in events if e.timestamp <= end_date]

        events.sort(key=lambda x: x.timestamp, reverse=True)

        return {
            "status": "ok",
            "events": [
                {
                    "event_id": e.event_id,
                    "timestamp": e.timestamp,
                    "tenant_id": e.tenant_id,
                    "event_type": e.event_type,
                    "region": e.region.value,
                    "data_classification": e.data_classification.value,
                    "resource_type": e.resource_type,
                    "resource_id": e.resource_id,
                    "compliant": e.compliant,
                    "violation_reason": e.violation_reason,
                }
                for e in events[:limit]
            ],
            "total": len(events),
        }

    # ── Reporting ──

    async def generate_compliance_report(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate data residency compliance report."""
        tenant_id = params.get("tenant_id")
        regulation = params.get("regulation", "all")  # gdpr, ccpa, hipaa, all
        period_start = params.get("period_start", (datetime.now(UTC) - timedelta(days=90)).isoformat())
        period_end = params.get("period_end", datetime.now(UTC).isoformat())

        # Filter audit events for period
        events = [e for e in self._audit_events.values() if period_start <= e.timestamp <= period_end]
        if tenant_id:
            events = [e for e in events if e.tenant_id == tenant_id]

        violations = [e for e in events if not e.compliant]
        by_region = {}
        by_classification = {}
        by_type = {}

        for e in events:
            by_region[e.region.value] = by_region.get(e.region.value, 0) + 1
            by_classification[e.data_classification.value] = by_classification.get(e.data_classification.value, 0) + 1
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1

        # GDPR-specific metrics
        gdpr_metrics = {}
        if regulation in ("gdpr", "all"):
            eu_events = [e for e in events if e.region in (Region.EU_WEST_1, Region.EU_CENTRAL_1)]
            gdpr_metrics = {
                "eu_data_events": len(eu_events),
                "eu_violations": len([e for e in eu_events if not e.compliant]),
                "data_transfer_outside_eu": len([e for e in events if e.region not in (Region.EU_WEST_1, Region.EU_CENTRAL_1) and e.details.get("operation") == "transfer"]),
            }

        # CCPA-specific metrics
        ccpa_metrics = {}
        if regulation in ("ccpa", "all"):
            us_events = [e for e in events if e.region in (Region.US_EAST_1, Region.US_WEST_2)]
            ccpa_metrics = {
                "us_data_events": len(us_events),
                "us_violations": len([e for e in us_events if not e.compliant]),
                "consumer_requests": len([e for e in events if "consumer_request" in e.event_type]),
            }

        return {
            "status": "ok",
            "report_type": "data_residency_compliance",
            "regulation": regulation,
            "period": {"start": period_start, "end": period_end},
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": {
                "total_events": len(events),
                "violations": len(violations),
                "compliance_rate": round((len(events) - len(violations)) / len(events) * 100, 2) if events else 100,
            },
            "by_region": by_region,
            "by_classification": by_classification,
            "by_event_type": by_type,
            "gdpr_metrics": gdpr_metrics,
            "ccpa_metrics": ccpa_metrics,
            "top_violations": [
                {"violation": v.get("violation", ""), "count": 1}
                for v in [e.details.get("violations", [{}])[0] for e in violations if e.details.get("violations")]
            ][:10],
        }

    # ── Continuous Monitoring ──

    async def check_replication_health(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check health of all replication configurations."""
        checks = []

        for config in self._replication_configs.values():
            # Simulate health check (in production, would query actual replication status)
            # For now, use the stored status
            passed = config.status == ReplicationStatus.HEALTHY
            lag_ok = config.lag_seconds <= config.rpo_seconds

            checks.append({
                "config_id": config.config_id,
                "source_region": config.source_region.value,
                "target_region": config.target_region.value,
                "status": config.status.value,
                "lag_seconds": config.lag_seconds,
                "rpo_seconds": config.rpo_seconds,
                "lag_within_rpo": lag_ok,
                "passed": passed and lag_ok,
                "last_sync": config.last_sync,
                "error_message": config.error_message,
            })

        failed = [c for c in checks if not c["passed"]]

        return {
            "status": "ok",
            "checks_run": len(checks),
            "passed": len(checks) - len(failed),
            "failed": len(failed),
            "checks": checks,
            "run_at": datetime.now(UTC).isoformat(),
        }


__all__ = [
    "DataResidencyService",
    "DataResidencyRule",
    "RegionDeployment",
    "ReplicationConfig",
    "TenantResidencyProfile",
    "ResidencyAuditEvent",
    "Region",
    "DataClassification",
    "ReplicationStatus",
    "ResidencyRuleType",
]