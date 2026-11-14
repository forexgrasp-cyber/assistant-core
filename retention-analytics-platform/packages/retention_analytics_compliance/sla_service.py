"""
SLA (Service Level Agreement) Service for Retention Analytics Platform.

Implements enterprise-grade SLA management with:
- 99.9%+ uptime commitments with credit policies
- Real-time uptime monitoring via unified_monitoring
- Incident response tracking and SLA breach detection
- Automated credit calculation and reporting
- Status page integration

Leverages shared-canonical-services:
- unified_monitoring for endpoint/pipeline health
- immutable_audit_log for tamper-proof SLA audit trails
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


class SLATier(StrEnum):
    """SLA tier levels."""
    STANDARD = "standard"      # 99.5% uptime
    PROFESSIONAL = "professional"  # 99.9% uptime
    ENTERPRISE = "enterprise"  # 99.95% uptime
    CRITICAL = "critical"      # 99.99% uptime


class SLAComponent(StrEnum):
    """Components covered by SLA."""
    API = "api"
    DATABASE = "database"
    CACHE = "cache"
    WORKER = "worker"
    WEBHOOK = "webhook"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    STORAGE = "storage"
    CDN = "cdn"


class IncidentSeverity(StrEnum):
    """Incident severity for SLA purposes."""
    SEV1 = "sev1"  # Critical - service down
    SEV2 = "sev2"  # Major - significant degradation
    SEV3 = "sev3"  # Minor - partial degradation
    SEV4 = "sev4"  # Low - cosmetic/non-functional


class IncidentStatus(StrEnum):
    """Incident lifecycle status."""
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    RESOLVING = "resolving"
    RESOLVED = "resolved"
    CLOSED = "closed"
    POSTMORTEM_PENDING = "postmortem_pending"
    POSTMORTEM_COMPLETE = "postmortem_complete"


class CreditStatus(StrEnum):
    """Credit claim status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


@dataclass
class SLADefinition:
    """SLA definition for a tier."""
    tier: SLATier
    name: str
    uptime_target: float  # e.g., 99.9
    measurement_window: str = "monthly"  # monthly, quarterly, annually
    components: list[SLAComponent] = field(default_factory=list)
    excluded_components: list[SLAComponent] = field(default_factory=list)
    credit_schedule: dict[float, float] = field(default_factory=dict)  # uptime % -> credit %
    response_times: dict[IncidentSeverity, int] = field(default_factory=dict)  # minutes
    resolution_times: dict[IncidentSeverity, int] = field(default_factory=dict)  # minutes
    maintenance_windows: list[dict[str, Any]] = field(default_factory=list)
    force_majeure_exclusions: list[str] = field(default_factory=list)


@dataclass
class TenantSLA:
    """A tenant's SLA agreement."""
    sla_id: str
    tenant_id: str
    tier: SLATier
    custom_name: str | None = None
    effective_date: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    expiration_date: str | None = None
    status: str = "active"  # active, expired, terminated, suspended
    components_covered: list[SLAComponent] = field(default_factory=list)
    custom_uptime_target: float | None = None
    custom_credit_schedule: dict[float, float] | None = None
    billing_contact: str = ""
    technical_contacts: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class SLAIncident:
    """An incident affecting SLA."""
    incident_id: str
    tenant_id: str
    sla_id: str
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.DETECTED
    title: str = ""
    description: str = ""
    affected_components: list[SLAComponent] = field(default_factory=list)
    detected_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    acknowledged_at: str | None = None
    resolved_at: str | None = None
    closed_at: str | None = None
    root_cause: str = ""
    resolution_summary: str = ""
    postmortem_url: str | None = None
    sla_breach: bool = False
    breach_details: dict[str, Any] = field(default_factory=dict)
    response_time_minutes: float | None = None
    resolution_time_minutes: float | None = None
    downtime_minutes: float = 0.0


@dataclass
class UptimeMeasurement:
    """Uptime measurement for a component."""
    measurement_id: str
    tenant_id: str
    sla_id: str
    component: SLAComponent
    region: str
    window_start: str
    window_end: str
    uptime_percentage: float
    total_minutes: int
    downtime_minutes: float
    incidents: list[str] = field(default_factory=list)  # incident_ids
    measured_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class SLACredit:
    """SLA credit calculation."""
    credit_id: str
    tenant_id: str
    sla_id: str
    measurement_period_start: str
    measurement_period_end: str
    actual_uptime: float
    target_uptime: float
    credit_percentage: float
    credit_amount: float
    currency: str = "USD"
    status: CreditStatus = CreditStatus.PENDING
    calculated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    approved_at: str | None = None
    applied_at: str | None = None
    invoice_id: str | None = None


@dataclass
class SLAStatusPageEntry:
    """Status page entry for incident communication."""
    entry_id: str
    incident_id: str
    title: str
    status: str  # investigating, identified, monitoring, resolved
    message: str
    affected_components: list[SLAComponent]
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    public: bool = True


class SLAService(CanonicalService):
    """
    SLA Management Service for enterprise uptime commitments.

    Provides:
    - SLA tier definitions with credit schedules
    - Tenant SLA agreement management
    - Real-time uptime monitoring integration
    - Incident tracking with SLA breach detection
    - Automated credit calculation
    - Status page entries for incident communication
    - Compliance reporting
    """

    SERVICE_NAME = "sla_management"
    VERSION = "1.0.0"

    # Default SLA tier definitions
    DEFAULT_TIERS = {
        SLATier.STANDARD: SLADefinition(
            tier=SLATier.STANDARD,
            name="Standard",
            uptime_target=99.5,
            components=list(SLAComponent),
            credit_schedule={
                99.5: 0,
                99.0: 10,
                95.0: 25,
                90.0: 50,
                0.0: 100,
            },
            response_times={
                IncidentSeverity.SEV1: 60,
                IncidentSeverity.SEV2: 240,
                IncidentSeverity.SEV3: 1440,
                IncidentSeverity.SEV4: 10080,
            },
            resolution_times={
                IncidentSeverity.SEV1: 240,
                IncidentSeverity.SEV2: 1440,
                IncidentSeverity.SEV3: 10080,
                IncidentSeverity.SEV4: 43200,
            },
            maintenance_windows=[
                {"day": "saturday", "start": "02:00", "end": "06:00", "timezone": "UTC", "frequency": "weekly"},
            ],
            force_majeure_exclusions=["natural_disaster", "terrorism", "war", "government_action", "isp_outage"],
        ),
        SLATier.PROFESSIONAL: SLADefinition(
            tier=SLATier.PROFESSIONAL,
            name="Professional",
            uptime_target=99.9,
            components=list(SLAComponent),
            credit_schedule={
                99.9: 0,
                99.5: 10,
                99.0: 25,
                95.0: 50,
                90.0: 100,
            },
            response_times={
                IncidentSeverity.SEV1: 15,
                IncidentSeverity.SEV2: 60,
                IncidentSeverity.SEV3: 240,
                IncidentSeverity.SEV4: 1440,
            },
            resolution_times={
                IncidentSeverity.SEV1: 60,
                IncidentSeverity.SEV2: 240,
                IncidentSeverity.SEV3: 1440,
                IncidentSeverity.SEV4: 10080,
            },
            maintenance_windows=[
                {"day": "saturday", "start": "02:00", "end": "04:00", "timezone": "UTC", "frequency": "weekly"},
            ],
            force_majeure_exclusions=["natural_disaster", "terrorism", "war", "government_action", "isp_outage"],
        ),
        SLATier.ENTERPRISE: SLADefinition(
            tier=SLATier.ENTERPRISE,
            name="Enterprise",
            uptime_target=99.95,
            components=list(SLAComponent),
            credit_schedule={
                99.95: 0,
                99.9: 10,
                99.5: 25,
                99.0: 50,
                95.0: 100,
            },
            response_times={
                IncidentSeverity.SEV1: 5,
                IncidentSeverity.SEV2: 15,
                IncidentSeverity.SEV3: 60,
                IncidentSeverity.SEV4: 240,
            },
            resolution_times={
                IncidentSeverity.SEV1: 30,
                IncidentSeverity.SEV2: 60,
                IncidentSeverity.SEV3: 240,
                IncidentSeverity.SEV4: 1440,
            },
            maintenance_windows=[
                {"day": "sunday", "start": "03:00", "end": "04:00", "timezone": "UTC", "frequency": "weekly"},
            ],
            force_majeure_exclusions=["natural_disaster", "terrorism", "war", "government_action", "isp_outage"],
        ),
        SLATier.CRITICAL: SLADefinition(
            tier=SLATier.CRITICAL,
            name="Critical",
            uptime_target=99.99,
            components=list(SLAComponent),
            credit_schedule={
                99.99: 0,
                99.95: 10,
                99.9: 25,
                99.5: 50,
                99.0: 100,
            },
            response_times={
                IncidentSeverity.SEV1: 2,
                IncidentSeverity.SEV2: 5,
                IncidentSeverity.SEV3: 15,
                IncidentSeverity.SEV4: 60,
            },
            resolution_times={
                IncidentSeverity.SEV1: 15,
                IncidentSeverity.SEV2: 30,
                IncidentSeverity.SEV3: 60,
                IncidentSeverity.SEV4: 240,
            },
            maintenance_windows=[
                {"day": "sunday", "start": "03:00", "end": "03:30", "timezone": "UTC", "frequency": "weekly"},
            ],
            force_majeure_exclusions=["natural_disaster", "terrorism", "war", "government_action", "isp_outage"],
        ),
    }

    def __init__(
        self,
        registry: Any = None,
        dry_run: bool = False,
        tenant_id: str | None = None,
    ) -> None:
        super().__init__(
            name="sla_management",
            registry=registry,
            version=self.VERSION,
            tenant_id=tenant_id,
            dry_run=dry_run,
        )
        self.registry = registry
        self._tiers: dict[SLATier, SLADefinition] = dict(self.DEFAULT_TIERS)
        self._tenant_slas: dict[str, TenantSLA] = {}
        self._incidents: dict[str, SLAIncident] = {}
        self._uptime_measurements: dict[str, UptimeMeasurement] = {}
        self._credits: dict[str, SLACredit] = {}
        self._status_page_entries: dict[str, SLAStatusPageEntry] = {}
        # Don't call _register_actions here - main.py will call register() which calls it

    def _register_actions(self) -> None:
        if not self.registry:
            return
        reg = self.registry.register("sla_management", version=self.VERSION, metadata={"domain": "compliance", "type": "platform"})
        reg.actions["list_tiers"] = self.list_tiers
        reg.actions["get_tier"] = self.get_tier
        reg.actions["manage_tier"] = self.manage_tier
        reg.actions["manage_tenant_sla"] = self.manage_tenant_sla
        reg.actions["get_tenant_sla"] = self.get_tenant_sla
        reg.actions["list_tenant_slas"] = self.list_tenant_slas
        reg.actions["create_incident"] = self.create_incident
        reg.actions["update_incident"] = self.update_incident
        reg.actions["get_incident"] = self.get_incident
        reg.actions["list_incidents"] = self.list_incidents
        reg.actions["record_uptime"] = self.record_uptime
        reg.actions["get_uptime_measurements"] = self.get_uptime_measurements
        reg.actions["calculate_credits"] = self.calculate_credits
        reg.actions["get_credits"] = self.get_credits
        reg.actions["manage_status_page"] = self.manage_status_page
        reg.actions["get_status_page"] = self.get_status_page
        reg.actions["generate_sla_report"] = self.generate_sla_report
        reg.actions["check_sla_compliance"] = self.check_sla_compliance

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

    # ── Tier Management ──

    async def list_tiers(self, params: dict[str, Any]) -> dict[str, Any]:
        """List all SLA tier definitions."""
        return {
            "status": "ok",
            "tiers": [
                {
                    "tier": tier.value,
                    "name": definition.name,
                    "uptime_target": definition.uptime_target,
                    "measurement_window": definition.measurement_window,
                    "components_covered": [c.value for c in definition.components],
                    "excluded_components": [c.value for c in definition.excluded_components],
                    "credit_schedule": definition.credit_schedule,
                    "response_times": {k.value: v for k, v in definition.response_times.items()},
                    "resolution_times": {k.value: v for k, v in definition.resolution_times.items()},
                    "maintenance_windows": definition.maintenance_windows,
                }
                for tier, definition in self._tiers.items()
            ],
        }

    async def get_tier(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get detailed tier definition."""
        tier = SLATier(params.get("tier"))
        definition = self._tiers.get(tier)

        if not definition:
            return {"status": "error", "message": f"Tier {tier} not found"}

        return {
            "status": "ok",
            "tier": {
                "tier": definition.tier.value,
                "name": definition.name,
                "uptime_target": definition.uptime_target,
                "measurement_window": definition.measurement_window,
                "components_covered": [c.value for c in definition.components],
                "excluded_components": [c.value for c in definition.excluded_components],
                "credit_schedule": definition.credit_schedule,
                "response_times": {k.value: v for k, v in definition.response_times.items()},
                "resolution_times": {k.value: v for k, v in definition.resolution_times.items()},
                "maintenance_windows": definition.maintenance_windows,
                "force_majeure_exclusions": definition.force_majeure_exclusions,
            },
        }

    async def manage_tier(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create or update a custom SLA tier."""
        action = params.get("action", "create")
        tier = SLATier(params.get("tier"))

        if action == "create" or (action == "update" and tier not in self._tiers):
            definition = SLADefinition(
                tier=tier,
                name=params.get("name", tier.value.title()),
                uptime_target=params.get("uptime_target", 99.9),
                measurement_window=params.get("measurement_window", "monthly"),
                components=[SLAComponent(c) for c in params.get("components", [c.value for c in SLAComponent])],
                excluded_components=[SLAComponent(c) for c in params.get("excluded_components", [])],
                credit_schedule=params.get("credit_schedule", {}),
                response_times={IncidentSeverity(k): v for k, v in params.get("response_times", {}).items()},
                resolution_times={IncidentSeverity(k): v for k, v in params.get("resolution_times", {}).items()},
                maintenance_windows=params.get("maintenance_windows", []),
                force_majeure_exclusions=params.get("force_majeure_exclusions", []),
            )
            self._tiers[tier] = definition
            return {"status": "ok", "tier": tier.value, "action": "created" if action == "create" else "updated"}

        elif action == "delete":
            if tier in self.DEFAULT_TIERS:
                return {"status": "error", "message": "Cannot delete default tier"}
            if tier in self._tiers:
                del self._tiers[tier]
                return {"status": "ok", "tier": tier.value, "action": "deleted"}

        return {"status": "error", "message": f"Invalid action: {action}"}

    # ── Tenant SLA Management ──

    async def manage_tenant_sla(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create, update, or terminate a tenant SLA."""
        action = params.get("action", "create")
        tenant_id = params.get("tenant_id")
        sla_id = params.get("sla_id")

        if not tenant_id:
            return {"status": "error", "message": "tenant_id required"}

        if action == "create":
            tier = SLATier(params.get("tier", "professional"))
            sla = TenantSLA(
                sla_id=f"sla-{uuid.uuid4().hex[:12]}",
                tenant_id=tenant_id,
                tier=tier,
                custom_name=params.get("custom_name"),
                expiration_date=params.get("expiration_date"),
                components_covered=[SLAComponent(c) for c in params.get("components_covered", [])],
                custom_uptime_target=params.get("custom_uptime_target"),
                custom_credit_schedule=params.get("custom_credit_schedule"),
                billing_contact=params.get("billing_contact", ""),
                technical_contacts=params.get("technical_contacts", []),
            )
            self._tenant_slas[sla.sla_id] = sla
            return {"status": "ok", "sla_id": sla.sla_id, "action": "created"}

        elif action in ("update", "terminate", "suspend", "reactivate"):
            sla = self._tenant_slas.get(sla_id)
            if not sla:
                return {"status": "error", "message": f"SLA {sla_id} not found"}

            if sla.tenant_id != tenant_id:
                return {"status": "error", "message": "SLA does not belong to tenant"}

            if action == "terminate":
                sla.status = "terminated"
                sla.expiration_date = datetime.now(UTC).isoformat()
            elif action == "suspend":
                sla.status = "suspended"
            elif action == "reactivate":
                sla.status = "active"
            else:
                updates = params.get("updates", {})
                for key, value in updates.items():
                    if hasattr(sla, key) and key not in ("sla_id", "tenant_id", "created_at"):
                        if key in ("components_covered", "technical_contacts"):
                            value = [SLAComponent(c) for c in value] if key == "components_covered" else value
                        elif key == "tier":
                            value = SLATier(value)
                        setattr(sla, key, value)

            sla.updated_at = datetime.now(UTC).isoformat()
            return {"status": "ok", "sla_id": sla_id, "action": action}

        return {"status": "error", "message": f"Invalid action: {action}"}

    async def get_tenant_sla(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get a tenant's SLA details."""
        sla_id = params.get("sla_id")
        sla = self._tenant_slas.get(sla_id)

        if not sla:
            return {"status": "error", "message": f"SLA {sla_id} not found"}

        tier_def = self._tiers.get(sla.tier)

        return {
            "status": "ok",
            "sla": {
                "sla_id": sla.sla_id,
                "tenant_id": sla.tenant_id,
                "tier": sla.tier.value,
                "tier_name": tier_def.name if tier_def else sla.tier.value,
                "uptime_target": sla.custom_uptime_target or (tier_def.uptime_target if tier_def else 99.9),
                "custom_name": sla.custom_name,
                "effective_date": sla.effective_date,
                "expiration_date": sla.expiration_date,
                "status": sla.status,
                "components_covered": [c.value for c in sla.components_covered] if sla.components_covered else [c.value for c in tier_def.components] if tier_def else [],
                "billing_contact": sla.billing_contact,
                "technical_contacts": sla.technical_contacts,
                "credit_schedule": sla.custom_credit_schedule or (tier_def.credit_schedule if tier_def else {}),
            },
        }

    async def list_tenant_slas(self, params: dict[str, Any]) -> dict[str, Any]:
        """List SLAs for a tenant."""
        tenant_id = params.get("tenant_id")
        status = params.get("status")

        slas = list(self._tenant_slas.values())
        if tenant_id:
            slas = [s for s in slas if s.tenant_id == tenant_id]
        if status:
            slas = [s for s in slas if s.status == status]

        return {
            "status": "ok",
            "slas": [
                {
                    "sla_id": s.sla_id,
                    "tenant_id": s.tenant_id,
                    "tier": s.tier.value,
                    "status": s.status,
                    "effective_date": s.effective_date,
                    "expiration_date": s.expiration_date,
                }
                for s in slas
            ],
        }

    # ── Incident Management ──

    async def create_incident(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create an SLA incident."""
        tenant_id = params.get("tenant_id")
        sla_id = params.get("sla_id")

        if not tenant_id or not sla_id:
            return {"status": "error", "message": "tenant_id and sla_id required"}

        sla = self._tenant_slas.get(sla_id)
        if not sla or sla.tenant_id != tenant_id:
            return {"status": "error", "message": "Invalid SLA for tenant"}

        incident = SLAIncident(
            incident_id=f"inc-{uuid.uuid4().hex[:12]}",
            tenant_id=tenant_id,
            sla_id=sla_id,
            severity=IncidentSeverity(params.get("severity", "sev3")),
            title=params.get("title", ""),
            description=params.get("description", ""),
            affected_components=[SLAComponent(c) for c in params.get("affected_components", [])],
        )

        self._incidents[incident.incident_id] = incident

        # Create status page entry
        status_entry = SLAStatusPageEntry(
            entry_id=f"status-{uuid.uuid4().hex[:12]}",
            incident_id=incident.incident_id,
            title=incident.title or "Service Incident",
            status="investigating",
            message=incident.description or "We are investigating a service issue.",
            affected_components=incident.affected_components,
        )
        self._status_page_entries[status_entry.entry_id] = status_entry

        # Log to immutable audit log
        try:
            from shared.audit.immutable_audit_log import get_audit_log
            audit_log = get_audit_log()
            audit_log.log_event(
                event_type="sla_incident_created",
                actor_id=params.get("actor_id", "system"),
                tenant_id=tenant_id,
                resource_type="sla_incident",
                resource_id=incident.incident_id,
                action="created",
                details={
                    "severity": incident.severity.value,
                    "affected_components": [c.value for c in incident.affected_components],
                    "sla_id": sla_id,
                },
            )
        except ImportError:
            pass

        return {
            "status": "ok",
            "incident_id": incident.incident_id,
            "status_page_entry_id": status_entry.entry_id,
            "severity": incident.severity.value,
            "response_target_minutes": self._get_response_target(sla, incident.severity),
            "resolution_target_minutes": self._get_resolution_target(sla, incident.severity),
        }

    async def update_incident(self, params: dict[str, Any]) -> dict[str, Any]:
        """Update an SLA incident."""
        incident_id = params.get("incident_id")
        incident = self._incidents.get(incident_id)

        if not incident:
            return {"status": "error", "message": f"Incident {incident_id} not found"}

        updates = params.get("updates", {})
        status_changed = False

        for key, value in updates.items():
            if hasattr(incident, key) and key != "incident_id":
                if key in ("severity", "status"):
                    value = IncidentSeverity(value) if key == "severity" else IncidentStatus(value)
                elif key == "affected_components":
                    value = [SLAComponent(c) for c in value]
                old_value = getattr(incident, key, None)
                setattr(incident, key, value)
                if key == "status" and old_value != value:
                    status_changed = True

        # Handle status transitions
        if "status" in updates:
            new_status = IncidentStatus(updates["status"])
            if new_status == IncidentStatus.ACKNOWLEDGED and not incident.acknowledged_at:
                incident.acknowledged_at = datetime.now(UTC).isoformat()
                incident.response_time_minutes = self._calculate_minutes(incident.detected_at, incident.acknowledged_at)
            elif new_status == IncidentStatus.RESOLVED and not incident.resolved_at:
                incident.resolved_at = datetime.now(UTC).isoformat()
                incident.resolution_time_minutes = self._calculate_minutes(incident.detected_at, incident.resolved_at)
                incident.downtime_minutes = incident.resolution_time_minutes
            elif new_status == IncidentStatus.CLOSED and not incident.closed_at:
                incident.closed_at = datetime.now(UTC).isoformat()

        # Check for SLA breach
        sla = self._tenant_slas.get(incident.sla_id)
        if sla and incident.severity == IncidentSeverity.SEV1:
            tier_def = self._tiers.get(sla.tier)
            if tier_def and incident.resolution_time_minutes:
                target = tier_def.resolution_times.get(incident.severity, 0)
                if incident.resolution_time_minutes > target:
                    incident.sla_breach = True
                    incident.breach_details = {
                        "type": "resolution_time_exceeded",
                        "target_minutes": target,
                        "actual_minutes": incident.resolution_time_minutes,
                    }

        # Update status page entry
        for entry in self._status_page_entries.values():
            if entry.incident_id == incident_id:
                if incident.status == IncidentStatus.INVESTIGATING:
                    entry.status = "investigating"
                elif incident.status == IncidentStatus.IDENTIFIED:
                    entry.status = "identified"
                elif incident.status == IncidentStatus.RESOLVING:
                    entry.status = "monitoring"
                elif incident.status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
                    entry.status = "resolved"
                entry.updated_at = datetime.now(UTC).isoformat()
                break

        return {"status": "ok", "incident_id": incident_id, "sla_breach": incident.sla_breach}

    def _get_response_target(self, sla: TenantSLA, severity: IncidentSeverity) -> int:
        tier_def = self._tiers.get(sla.tier)
        if tier_def:
            return tier_def.response_times.get(severity, 60)
        return 60

    def _get_resolution_target(self, sla: TenantSLA, severity: IncidentSeverity) -> int:
        tier_def = self._tiers.get(sla.tier)
        if tier_def:
            return tier_def.resolution_times.get(severity, 240)
        return 240

    def _calculate_minutes(self, start: str, end: str) -> float:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return (end_dt - start_dt).total_seconds() / 60

    async def get_incident(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get incident details."""
        incident_id = params.get("incident_id")
        incident = self._incidents.get(incident_id)

        if not incident:
            return {"status": "error", "message": f"Incident {incident_id} not found"}

        return {
            "status": "ok",
            "incident": {
                "incident_id": incident.incident_id,
                "tenant_id": incident.tenant_id,
                "sla_id": incident.sla_id,
                "severity": incident.severity.value,
                "status": incident.status.value,
                "title": incident.title,
                "description": incident.description,
                "affected_components": [c.value for c in incident.affected_components],
                "detected_at": incident.detected_at,
                "acknowledged_at": incident.acknowledged_at,
                "resolved_at": incident.resolved_at,
                "closed_at": incident.closed_at,
                "response_time_minutes": incident.response_time_minutes,
                "resolution_time_minutes": incident.resolution_time_minutes,
                "downtime_minutes": incident.downtime_minutes,
                "sla_breach": incident.sla_breach,
                "breach_details": incident.breach_details,
                "root_cause": incident.root_cause,
            },
        }

    async def list_incidents(self, params: dict[str, Any]) -> dict[str, Any]:
        """List incidents with filtering."""
        tenant_id = params.get("tenant_id")
        sla_id = params.get("sla_id")
        severity = params.get("severity")
        status = params.get("status")
        start_date = params.get("start_date")
        end_date = params.get("end_date")

        incidents = list(self._incidents.values())

        if tenant_id:
            incidents = [i for i in incidents if i.tenant_id == tenant_id]
        if sla_id:
            incidents = [i for i in incidents if i.sla_id == sla_id]
        if severity:
            incidents = [i for i in incidents if i.severity.value == severity]
        if status:
            incidents = [i for i in incidents if i.status.value == status]
        if start_date:
            incidents = [i for i in incidents if i.detected_at >= start_date]
        if end_date:
            incidents = [i for i in incidents if i.detected_at <= end_date]

        incidents.sort(key=lambda x: x.detected_at, reverse=True)

        return {
            "status": "ok",
            "incidents": [
                {
                    "incident_id": i.incident_id,
                    "tenant_id": i.tenant_id,
                    "sla_id": i.sla_id,
                    "severity": i.severity.value,
                    "status": i.status.value,
                    "title": i.title,
                    "detected_at": i.detected_at,
                    "resolved_at": i.resolved_at,
                    "sla_breach": i.sla_breach,
                }
                for i in incidents
            ],
        }

    # ── Uptime Measurements ──

    async def record_uptime(self, params: dict[str, Any]) -> dict[str, Any]:
        """Record an uptime measurement for a component."""
        tenant_id = params.get("tenant_id")
        sla_id = params.get("sla_id")
        component = SLAComponent(params.get("component"))
        region = params.get("region", "us-east-1")
        window_start = params.get("window_start")
        window_end = params.get("window_end")
        uptime_percentage = params.get("uptime_percentage")
        downtime_minutes = params.get("downtime_minutes", 0.0)
        incidents = params.get("incidents", [])

        if not all([tenant_id, sla_id, component, window_start, window_end, uptime_percentage is not None]):
            return {"status": "error", "message": "Missing required fields"}

        measurement = UptimeMeasurement(
            measurement_id=f"upt-{uuid.uuid4().hex[:12]}",
            tenant_id=tenant_id,
            sla_id=sla_id,
            component=component,
            region=region,
            window_start=window_start,
            window_end=window_end,
            uptime_percentage=uptime_percentage,
            total_minutes=int((datetime.fromisoformat(window_end.replace("Z", "+00:00")) - datetime.fromisoformat(window_start.replace("Z", "+00:00"))).total_seconds() / 60),
            downtime_minutes=downtime_minutes,
            incidents=incidents,
        )

        self._uptime_measurements[measurement.measurement_id] = measurement

        return {"status": "ok", "measurement_id": measurement.measurement_id}

    async def get_uptime_measurements(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get uptime measurements."""
        tenant_id = params.get("tenant_id")
        sla_id = params.get("sla_id")
        component = params.get("component")
        start_date = params.get("start_date")
        end_date = params.get("end_date")

        measurements = list(self._uptime_measurements.values())

        if tenant_id:
            measurements = [m for m in measurements if m.tenant_id == tenant_id]
        if sla_id:
            measurements = [m for m in measurements if m.sla_id == sla_id]
        if component:
            measurements = [m for m in measurements if m.component.value == component]
        if start_date:
            measurements = [m for m in measurements if m.window_start >= start_date]
        if end_date:
            measurements = [m for m in measurements if m.window_end <= end_date]

        measurements.sort(key=lambda x: x.window_start, reverse=True)

        return {
            "status": "ok",
            "measurements": [
                {
                    "measurement_id": m.measurement_id,
                    "tenant_id": m.tenant_id,
                    "sla_id": m.sla_id,
                    "component": m.component.value,
                    "region": m.region,
                    "window_start": m.window_start,
                    "window_end": m.window_end,
                    "uptime_percentage": m.uptime_percentage,
                    "downtime_minutes": m.downtime_minutes,
                    "incidents": m.incidents,
                }
                for m in measurements
            ],
        }

    # ── Credit Calculation ──

    async def calculate_credits(self, params: dict[str, Any]) -> dict[str, Any]:
        """Calculate SLA credits for a measurement period."""
        tenant_id = params.get("tenant_id")
        sla_id = params.get("sla_id")
        period_start = params.get("period_start")
        period_end = params.get("period_end")
        monthly_fee = params.get("monthly_fee", 0.0)

        if not all([tenant_id, sla_id, period_start, period_end]):
            return {"status": "error", "message": "Missing required fields"}

        sla = self._tenant_slas.get(sla_id)
        if not sla or sla.tenant_id != tenant_id:
            return {"status": "error", "message": "Invalid SLA for tenant"}

        tier_def = self._tiers.get(sla.tier)
        if not tier_def:
            return {"status": "error", "message": "Tier definition not found"}

        # Get uptime measurements for period
        measurements = [
            m for m in self._uptime_measurements.values()
            if m.tenant_id == tenant_id and m.sla_id == sla_id
            and period_start <= m.window_start <= period_end
        ]

        if not measurements:
            return {"status": "ok", "credits": [], "message": "No measurements for period"}

        # Calculate weighted average uptime across components
        components = sla.components_covered if sla.components_covered else tier_def.components
        component_uptime = {}

        for comp in components:
            comp_measurements = [m for m in measurements if m.component == comp]
            if comp_measurements:
                total_minutes = sum(m.total_minutes for m in comp_measurements)
                total_downtime = sum(m.downtime_minutes for m in comp_measurements)
                uptime = (total_minutes - total_downtime) / total_minutes * 100 if total_minutes > 0 else 100
                component_uptime[comp.value] = uptime

        # Overall uptime (average across components)
        overall_uptime = sum(component_uptime.values()) / len(component_uptime) if component_uptime else 100

        # Determine credit based on tier's credit schedule
        target_uptime = sla.custom_uptime_target or tier_def.uptime_target
        credit_schedule = sla.custom_credit_schedule or tier_def.credit_schedule

        # Find applicable credit tier
        credit_pct = 0.0
        for threshold, credit in sorted(credit_schedule.items(), reverse=True):
            if overall_uptime < threshold:
                credit_pct = credit
                break

        credit_amount = monthly_fee * credit_pct / 100

        credit = SLACredit(
            credit_id=f"credit-{uuid.uuid4().hex[:12]}",
            tenant_id=tenant_id,
            sla_id=sla_id,
            measurement_period_start=period_start,
            measurement_period_end=period_end,
            actual_uptime=round(overall_uptime, 2),
            target_uptime=target_uptime,
            credit_percentage=credit_pct,
            credit_amount=round(credit_amount, 2),
        )

        self._credits[credit.credit_id] = credit

        return {
            "status": "ok",
            "credit": {
                "credit_id": credit.credit_id,
                "tenant_id": tenant_id,
                "sla_id": sla_id,
                "period_start": period_start,
                "period_end": period_end,
                "actual_uptime": credit.actual_uptime,
                "target_uptime": credit.target_uptime,
                "credit_percentage": credit.credit_percentage,
                "credit_amount": credit.credit_amount,
                "currency": credit.currency,
                "component_uptime": component_uptime,
            },
        }

    async def get_credits(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get SLA credits for a tenant."""
        tenant_id = params.get("tenant_id")
        sla_id = params.get("sla_id")
        status = params.get("status")

        credits = list(self._credits.values())

        if tenant_id:
            credits = [c for c in credits if c.tenant_id == tenant_id]
        if sla_id:
            credits = [c for c in credits if c.sla_id == sla_id]
        if status:
            credits = [c for c in credits if c.status.value == status]

        credits.sort(key=lambda x: x.calculated_at, reverse=True)

        return {
            "status": "ok",
            "credits": [
                {
                    "credit_id": c.credit_id,
                    "tenant_id": c.tenant_id,
                    "sla_id": c.sla_id,
                    "period_start": c.measurement_period_start,
                    "period_end": c.measurement_period_end,
                    "actual_uptime": c.actual_uptime,
                    "target_uptime": c.target_uptime,
                    "credit_percentage": c.credit_percentage,
                    "credit_amount": c.credit_amount,
                    "currency": c.currency,
                    "status": c.status.value,
                }
                for c in credits
            ],
        }

    # ── Status Page ──

    async def manage_status_page(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create or update a status page entry."""
        action = params.get("action", "create")
        entry_id = params.get("entry_id")

        if action == "create":
            entry = SLAStatusPageEntry(
                entry_id=f"status-{uuid.uuid4().hex[:12]}",
                incident_id=params.get("incident_id", ""),
                title=params.get("title", ""),
                status=params.get("status", "investigating"),
                message=params.get("message", ""),
                affected_components=[SLAComponent(c) for c in params.get("affected_components", [])],
                public=params.get("public", True),
            )
            self._status_page_entries[entry.entry_id] = entry
            return {"status": "ok", "entry_id": entry.entry_id, "action": "created"}

        elif action in ("update", "delete"):
            entry = self._status_page_entries.get(entry_id)
            if not entry:
                return {"status": "error", "message": f"Status page entry {entry_id} not found"}

            if action == "delete":
                del self._status_page_entries[entry_id]
                return {"status": "ok", "entry_id": entry_id, "action": "deleted"}

            updates = params.get("updates", {})
            for key, value in updates.items():
                if hasattr(entry, key) and key != "entry_id":
                    if key == "affected_components":
                        value = [SLAComponent(c) for c in value]
                    setattr(entry, key, value)

            entry.updated_at = datetime.now(UTC).isoformat()
            return {"status": "ok", "entry_id": entry_id, "action": "updated"}

        return {"status": "error", "message": f"Invalid action: {action}"}

    async def get_status_page(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get status page entries."""
        incident_id = params.get("incident_id")
        public_only = params.get("public_only", True)

        entries = list(self._status_page_entries.values())

        if incident_id:
            entries = [e for e in entries if e.incident_id == incident_id]
        if public_only:
            entries = [e for e in entries if e.public]

        entries.sort(key=lambda x: x.created_at, reverse=True)

        return {
            "status": "ok",
            "entries": [
                {
                    "entry_id": e.entry_id,
                    "incident_id": e.incident_id,
                    "title": e.title,
                    "status": e.status,
                    "message": e.message,
                    "affected_components": [c.value for c in e.affected_components],
                    "created_at": e.created_at,
                    "updated_at": e.updated_at,
                    "public": e.public,
                }
                for e in entries
            ],
        }

    # ── Reporting ──

    async def generate_sla_report(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate SLA compliance report."""
        tenant_id = params.get("tenant_id")
        sla_id = params.get("sla_id")
        period_start = params.get("period_start", (datetime.now(UTC) - timedelta(days=30)).isoformat())
        period_end = params.get("period_end", datetime.now(UTC).isoformat())

        slas = list(self._tenant_slas.values())
        if tenant_id:
            slas = [s for s in slas if s.tenant_id == tenant_id]
        if sla_id:
            slas = [s for s in slas if s.sla_id == sla_id]

        report_slas = []
        total_credits = 0.0

        for sla in slas:
            tier_def = self._tiers.get(sla.tier)
            target_uptime = sla.custom_uptime_target or (tier_def.uptime_target if tier_def else 99.9)

            # Get measurements for period
            measurements = [
                m for m in self._uptime_measurements.values()
                if m.tenant_id == sla.tenant_id and m.sla_id == sla.sla_id
                and period_start <= m.window_start <= period_end
            ]

            # Calculate uptime
            if measurements:
                total_minutes = sum(m.total_minutes for m in measurements)
                total_downtime = sum(m.downtime_minutes for m in measurements)
                actual_uptime = (total_minutes - total_downtime) / total_minutes * 100 if total_minutes > 0 else 100
            else:
                actual_uptime = 100.0

            # Get incidents
            incidents = [
                i for i in self._incidents.values()
                if i.tenant_id == sla.tenant_id and i.sla_id == sla.sla_id
                and period_start <= i.detected_at <= period_end
            ]

            # Get credits
            credits = [
                c for c in self._credits.values()
                if c.tenant_id == sla.tenant_id and c.sla_id == sla.sla_id
                and period_start <= c.measurement_period_start <= period_end
            ]

            sla_credit_total = sum(c.credit_amount for c in credits)
            total_credits += sla_credit_total

            report_slas.append({
                "sla_id": sla.sla_id,
                "tenant_id": sla.tenant_id,
                "tier": sla.tier.value,
                "target_uptime": target_uptime,
                "actual_uptime": round(actual_uptime, 2),
                "compliant": actual_uptime >= target_uptime,
                "total_downtime_minutes": sum(m.downtime_minutes for m in measurements),
                "incidents_count": len(incidents),
                "sev1_incidents": len([i for i in incidents if i.severity == IncidentSeverity.SEV1]),
                "sla_breaches": len([i for i in incidents if i.sla_breach]),
                "credits_issued": len(credits),
                "credit_amount": round(sla_credit_total, 2),
            })

        return {
            "status": "ok",
            "report_type": "sla_compliance",
            "period": {"start": period_start, "end": period_end},
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": {
                "total_slas": len(report_slas),
                "compliant_slas": len([s for s in report_slas if s["compliant"]]),
                "total_credits_issued": round(total_credits, 2),
                "total_downtime_minutes": sum(s["total_downtime_minutes"] for s in report_slas),
                "total_incidents": sum(s["incidents_count"] for s in report_slas),
                "total_sev1_incidents": sum(s["sev1_incidents"] for s in report_slas),
                "total_sla_breaches": sum(s["sla_breaches"] for s in report_slas),
            },
            "slas": report_slas,
        }

    # ── Continuous Monitoring ──

    async def check_sla_compliance(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check current SLA compliance across all tenants."""
        try:
            from shared.unified_monitoring.monitor import UnifiedMonitor, MonitorConfig
            monitor = UnifiedMonitor(MonitorConfig())
            health = monitor.get_health()
            monitor.get_dashboard()
        except Exception:
            health = {"status": "unknown"}

        checks = []
        overall_compliant = True

        for sla in self._tenant_slas.values():
            if sla.status != "active":
                continue

            tier_def = self._tiers.get(sla.tier)
            if not tier_def:
                continue

            target = sla.custom_uptime_target or tier_def.uptime_target

            # Get recent measurements (last 30 days)
            recent_start = (datetime.now(UTC) - timedelta(days=30)).isoformat()
            measurements = [
                m for m in self._uptime_measurements.values()
                if m.tenant_id == sla.tenant_id and m.sla_id == sla.sla_id
                and m.window_start >= recent_start
            ]

            if measurements:
                total_minutes = sum(m.total_minutes for m in measurements)
                total_downtime = sum(m.downtime_minutes for m in measurements)
                uptime = (total_minutes - total_downtime) / total_minutes * 100 if total_minutes > 0 else 100
                compliant = uptime >= target
            else:
                uptime = 100.0
                compliant = True

            # Check for active SEV1 incidents
            active_sev1 = [
                i for i in self._incidents.values()
                if i.tenant_id == sla.tenant_id and i.sla_id == sla.sla_id
                and i.severity == IncidentSeverity.SEV1
                and i.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)
            ]

            checks.append({
                "sla_id": sla.sla_id,
                "tenant_id": sla.tenant_id,
                "tier": sla.tier.value,
                "target_uptime": target,
                "actual_uptime": round(uptime, 2),
                "compliant": compliant and len(active_sev1) == 0,
                "active_sev1_incidents": len(active_sev1),
                "measurements_count": len(measurements),
            })

            if not compliant or active_sev1:
                overall_compliant = False

        return {
            "status": "ok",
            "overall_compliant": overall_compliant,
            "platform_health": health.get("status", "unknown"),
            "checks": checks,
            "run_at": datetime.now(UTC).isoformat(),
        }


__all__ = [
    "SLAService",
    "SLADefinition",
    "TenantSLA",
    "SLAIncident",
    "UptimeMeasurement",
    "SLACredit",
    "SLAStatusPageEntry",
    "SLATier",
    "SLAComponent",
    "IncidentSeverity",
    "IncidentStatus",
    "CreditStatus",
]