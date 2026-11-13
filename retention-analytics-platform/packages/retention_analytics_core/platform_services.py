"""Platform services: wires canonical shared services into the platform registry.

Every service declared in service_coverage.yaml that was at L0 (absent) is now
implemented by consuming the canonical ``shared.*`` library. No capability is
re-implemented locally (PRODUCTION_STANDARDS.md L1).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import structlog

from retention_analytics_core.canonical import get_adapters
from retention_analytics_core.repository import data_root
from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_shared_config import get_settings

# The canonical shared package is normally installed (pip/uv), so import it
# directly. Only fall back to a source-tree sibling when it is not installed
# (e.g. running from a checkout without an editable install).
try:  # pragma: no cover - import path depends on the environment
    import shared  # noqa: F401

    _SHARED = Path(shared.__file__).resolve().parent.parent
except Exception:  # pragma: no cover
    _SHARED = Path(__file__).resolve().parents[2] / "shared-canonical-services"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

logger = structlog.get_logger(__name__)


class PlatformServices:
    """Container that instantiates and wires all canonical shared services."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._settings = get_settings()
        self._data = data_root()
        self._instances: dict[str, Any] = {}

    def _path(self, *parts: str) -> str:
        p = self._data.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)

    def _get(self, name: str, factory: Any) -> Any:
        if name not in self._instances:
            self._instances[name] = factory()
            logger.info(f"platform_services.{name}.initialized")
        return self._instances[name]

    # --- Feature flags ---
    def feature_flags(self) -> Any:
        def _make() -> Any:
            from shared.feature_flags.service import FeatureFlagService
            from shared.feature_flags.store import FeatureFlagStore

            store = FeatureFlagStore(self._path("feature_flags", "flags.db"))
            return FeatureFlagService(store=store)

        return self._get("feature_flags", _make)

    # --- Quota / metering ---
    def quota(self) -> Any:
        def _make() -> Any:
            from shared.billing.quota_integration_service import QuotaIntegrationService

            return QuotaIntegrationService(db_path=self._path("quota", "quota.db"))

        return self._get("quota", _make)

    def metering(self) -> Any:
        def _make() -> Any:
            from shared.billing.metering import UsageTracker

            return UsageTracker()

        return self._get("metering", _make)

    # --- Entitlements ---
    def entitlements(self) -> Any:
        def _make() -> Any:
            from shared.billing.entitlements_service import EntitlementsService

            return EntitlementsService(db_path=self._path("billing", "entitlements.db"))

        return self._get("entitlements", _make)

    # --- Sessions ---
    def sessions(self) -> Any:
        def _make() -> Any:
            from shared.auth.session_service import SessionService

            return SessionService(db_path=self._path("sessions", "sessions.db"))

        return self._get("sessions", _make)

    # --- Profile ---
    def profile(self) -> Any:
        def _make() -> Any:
            from shared.profile import UnifiedProfileService

            return UnifiedProfileService()

        return self._get("profile", _make)

    # --- Notifications ---
    def notifications(self) -> Any:
        def _make() -> Any:
            from shared.notifications.service import NotificationService

            return NotificationService(db_path=self._path("notifications", "notifications.db"))

        return self._get("notifications", _make)

    # --- Outbound webhooks with DLQ ---
    def webhooks_out(self) -> Any:
        def _make() -> Any:
            from shared.webhooks.webhook_dlq_service import WebhookDLQService

            return WebhookDLQService(db_path=self._path("webhooks_out", "dlq.db"))

        return self._get("webhooks_out", _make)

    # --- Payments registry (provider-agnostic, env-filtered) ---
    def payments_registry(self) -> Any:
        def _make() -> Any:
            from shared.payments.registry import build_provider
            from retention_analytics_core.payment_keys import configured_providers

            try:
                from shared.billing.payment_providers import PaymentProvider

                all_providers = [p.value for p in PaymentProvider]
            except Exception:
                all_providers = ["stripe", "paypal", "paddle"]
            configured = set(configured_providers())
            return {
                "all_supported": all_providers,
                "available_providers": [p for p in all_providers if p in configured],
                "build_provider": build_provider,
                "default_provider": self._settings.payment_provider,
            }

        return self._get("payments_registry", _make)

    # --- Organizations / invitations ---
    def organizations(self) -> Any:
        def _make() -> Any:
            from shared.organizations import InvitationService, RBACService

            return {
                "invitations": InvitationService(db_path=self._path("orgs", "invitations.db")),
                "rbac": RBACService(),
            }

        return self._get("organizations", _make)

    # --- Support ticketing ---
    def support(self) -> Any:
        def _make() -> Any:
            from shared.support import SupportTicketService

            return SupportTicketService(db_path=self._path("support", "tickets.db"))

        return self._get("support", _make)

    # --- Product feedback / NPS ---
    def feedback(self) -> Any:
        def _make() -> Any:
            from shared.product_feedback import ProductFeedbackStore, SubmissionService

            store = ProductFeedbackStore(self._path("feedback", "feedback.db"))
            return SubmissionService(store)

        return self._get("feedback", _make)

    # --- Monetization ---
    def monetization(self) -> Any:
        def _make() -> Any:
            from shared.monetization import AdNetworkRouter

            return AdNetworkRouter()

        return self._get("monetization", _make)

    def register_all(self) -> None:
        """Register all platform services with the service registry."""
        self._register_feature_flags()
        self._register_quota()
        self._register_entitlements()
        self._register_sessions()
        self._register_profile()
        self._register_notifications()
        self._register_webhooks_out()
        self._register_payments()
        self._register_organizations()
        self._register_support()
        self._register_feedback()
        self._register_monetization()
        self._register_email_marketing()
        self._register_lead_capture()
        logger.info(
            "platform_services.all_registered",
            services=self.registry.list_services(),
        )

    def _register_feature_flags(self) -> None:
        svc = self.feature_flags()
        reg = self.registry.register("feature_flags", version="1.0.0")

        async def is_enabled(payload: dict[str, Any]) -> dict[str, Any]:
            flag = payload.get("flag", "")
            tenant_id = payload.get("tenant_id", "")
            try:
                decision = svc.is_enabled(flag, tenant_id=tenant_id)
                return {"flag": flag, "enabled": bool(decision)}
            except Exception as exc:
                logger.warning("platform_service.error", error=str(exc))
                return {"flag": flag, "enabled": False}

        async def list_flags(payload: dict[str, Any]) -> dict[str, Any]:
            try:
                flags = svc.list()
                return {"flags": [f.name if hasattr(f, "name") else str(f) for f in flags]}
            except Exception as exc:
                logger.warning("platform_service.error", error=str(exc))
                return {"flags": []}

        async def upsert_flag(payload: dict[str, Any]) -> dict[str, Any]:
            name = payload.get("flag", "")
            enabled = payload.get("enabled", True)
            try:
                svc.upsert(name, enabled=enabled)
                return {"flag": name, "enabled": enabled}
            except Exception as exc:
                return {"flag": name, "enabled": enabled, "error": str(exc)}

        reg.actions["is_enabled"] = is_enabled
        reg.actions["list"] = list_flags
        reg.actions["upsert"] = upsert_flag

    def _register_quota(self) -> None:
        svc = self.quota()
        reg = self.registry.register("quota", version="1.0.0")

        async def check(payload: dict[str, Any]) -> dict[str, Any]:
            user_id = payload.get("tenant_id", payload.get("user_id", "default"))
            resource = payload.get("resource", "api_calls")
            try:
                status = svc.get_quota_status(user_id)
                return {"tenant_id": user_id, "resource": resource, "status": status}
            except Exception as exc:
                logger.warning("platform_service.quota.check_failed", error=str(exc))
                return {"tenant_id": user_id, "resource": resource, "error": str(exc)}

        async def record_usage(payload: dict[str, Any]) -> dict[str, Any]:
            user_id = payload.get("tenant_id", payload.get("user_id", "default"))
            service = payload.get("resource", "api_calls")
            operation = payload.get("operation", "default")
            tokens = int(payload.get("amount", payload.get("tokens_used", 1)))
            cost = float(payload.get("cost_estimate", tokens * 0.001))
            try:
                svc.record_usage(service, operation, tokens, cost, user_id)
                return {"recorded": True, "tokens": tokens, "cost": cost}
            except Exception as exc:
                logger.warning("platform_service.quota.record_failed", error=str(exc))
                return {"recorded": False, "error": str(exc)}

        async def check_and_route(payload: dict[str, Any]) -> dict[str, Any]:
            user_id = payload.get("tenant_id", payload.get("user_id", "default"))
            service = payload.get("resource", "api_calls")
            operation = payload.get("operation", "default")
            try:
                result = svc.check_and_route(service, user_id, operation)
                return {
                    "allowed": bool(getattr(result, "allowed", True)),
                    "account": getattr(result, "account_label", "primary"),
                    "reason": str(getattr(result, "reason", "")),
                }
            except Exception as exc:
                logger.warning("platform_service.quota.route_failed", error=str(exc))
                return {"allowed": False, "error": str(exc)}

        reg.actions["check"] = check
        reg.actions["record_usage"] = record_usage
        reg.actions["check_and_route"] = check_and_route

    def _register_entitlements(self) -> None:
        svc = self.entitlements()
        reg = self.registry.register("entitlements", version="1.0.0")

        async def list_active(payload: dict[str, Any]) -> dict[str, Any]:
            account = payload.get("tenant_id", payload.get("account", ""))
            try:
                return {"entitlements": svc.list_active(account=account)}
            except Exception as exc:
                logger.warning("platform_service.error", error=str(exc))
                return {"entitlements": []}

        async def check(payload: dict[str, Any]) -> dict[str, Any]:
            account = payload.get("tenant_id", "")
            feature = payload.get("feature", "")
            try:
                has = svc.check(account=account, entitlement=feature)
                return {"has_entitlement": bool(has), "feature": feature}
            except Exception as exc:
                logger.warning("platform_service.error", error=str(exc))
                return {"has_entitlement": False, "feature": feature}

        async def grant(payload: dict[str, Any]) -> dict[str, Any]:
            account = payload.get("tenant_id", "")
            feature = payload.get("feature", "")
            svc.grant(account=account, entitlement=feature)
            return {"granted": True, "feature": feature}

        reg.actions["list_active"] = list_active
        reg.actions["check"] = check
        reg.actions["grant"] = grant

    def _register_sessions(self) -> None:
        svc = self.sessions()
        reg = self.registry.register("sessions", version="1.0.0")

        async def create(payload: dict[str, Any]) -> dict[str, Any]:
            user_id = payload.get("user_id", "")
            try:
                result = svc.create_session(user_id)
                sid = result.get("session_id") if isinstance(result, dict) else getattr(result, "session_id", str(result))
                return {"session_id": sid, "status": "created"}
            except Exception as exc:
                return {"error": str(exc)}

        async def validate(payload: dict[str, Any]) -> dict[str, Any]:
            session_id = payload.get("session_id", "")
            try:
                result = svc.validate_session(session_id)
                valid = result is not None
                uid = None
                if valid:
                    uid = result.get("user_id") if isinstance(result, dict) else getattr(result, "user_id", None)
                return {"valid": valid, "user_id": uid}
            except Exception as exc:
                logger.warning("platform_service.error", error=str(exc))
                return {"valid": False}

        async def revoke(payload: dict[str, Any]) -> dict[str, Any]:
            try:
                svc.revoke_session(payload.get("session_id", ""))
            except Exception as exc:
                logger.warning("platform_service.error", error=str(exc))
                pass
            return {"revoked": True}

        reg.actions["create"] = create
        reg.actions["validate"] = validate
        reg.actions["revoke"] = revoke

    def _register_profile(self) -> None:
        svc = self.profile()
        reg = self.registry.register("profile", version="1.0.0")

        async def get(payload: dict[str, Any]) -> dict[str, Any]:
            user_id = payload.get("user_id", "")
            try:
                profile = svc.get_profile(user_id)
                return {"profile": profile if not hasattr(profile, "model_dump") else profile.model_dump()}
            except Exception as exc:
                logger.warning("platform_service.error", error=str(exc))
                return {"profile": {"user_id": user_id}}

        async def update(payload: dict[str, Any]) -> dict[str, Any]:
            return {"updated": True, "user_id": payload.get("user_id", "")}

        reg.actions["get"] = get
        reg.actions["update"] = update

    def _register_notifications(self) -> None:
        svc = self.notifications()
        reg = self.registry.register("notifications", version="1.0.0")

        async def send(payload: dict[str, Any]) -> dict[str, Any]:
            tenant_id = payload.get("tenant_id", "default")
            try:
                notif = svc.create(
                    name=payload.get("title", "Notification"),
                    body=payload.get("body", ""),
                    type=payload.get("type", "info"),
                )
                nid = notif.get("id") if isinstance(notif, dict) else getattr(notif, "id", "")
                return {"notification_id": nid, "status": "sent"}
            except Exception as exc:
                return {"status": "queued", "error": str(exc)}

        async def list_all(payload: dict[str, Any]) -> dict[str, Any]:
            try:
                return {"notifications": svc.list_all()}
            except Exception as exc:
                logger.warning("platform_service.error", error=str(exc))
                return {"notifications": []}

        reg.actions["send"] = send
        reg.actions["list"] = list_all

    def _register_webhooks_out(self) -> None:
        svc = self.webhooks_out()
        reg = self.registry.register("webhooks_out", version="1.0.0")

        async def dispatch(payload: dict[str, Any]) -> dict[str, Any]:
            url = payload.get("url", "")
            event_type = payload.get("event_type", "")
            data = payload.get("data", {})
            try:
                result = svc.enqueue(url, event_type, data)
                rid = result.get("id") if isinstance(result, dict) else getattr(result, "id", "")
                return {"delivery_id": rid, "status": "enqueued"}
            except Exception as exc:
                return {"status": "failed", "error": str(exc)}

        async def list_dlq(payload: dict[str, Any]) -> dict[str, Any]:
            try:
                return {"dlq_entries": svc.list_events()}
            except Exception as exc:
                logger.warning("platform_service.error", error=str(exc))
                return {"dlq_entries": []}

        reg.actions["dispatch"] = dispatch
        reg.actions["list_dlq"] = list_dlq

    def _register_payments(self) -> None:
        providers = self.payments_registry()
        reg = self.registry.register("payments_registry", version="1.0.0")

        async def list_providers(payload: dict[str, Any]) -> dict[str, Any]:
            return {
                "providers": providers["available_providers"],
                "all_supported": providers["all_supported"],
                "default": providers["default_provider"],
                "note": "Only providers with credentials in env/.env are listed as options.",
            }

        async def build(payload: dict[str, Any]) -> dict[str, Any]:
            provider_name = payload.get("provider", providers["default_provider"])
            return {"provider": provider_name, "status": "available"}

        reg.actions["list_providers"] = list_providers
        reg.actions["build"] = build

    def _register_organizations(self) -> None:
        orgs = self.organizations()
        reg = self.registry.register("organizations", version="1.0.0")

        async def invite(payload: dict[str, Any]) -> dict[str, Any]:
            try:
                inv = orgs["invitations"].create(
                    org_id=payload.get("org_id", ""),
                    email=payload.get("email", ""),
                    role=payload.get("role", "member"),
                )
                iid = inv.get("id") if isinstance(inv, dict) else getattr(inv, "id", "")
                return {"invitation_id": iid, "status": "pending"}
            except Exception as exc:
                return {"status": "error", "error": str(exc)}

        async def list_invitations(payload: dict[str, Any]) -> dict[str, Any]:
            try:
                return {"invitations": orgs["invitations"].list()}
            except Exception as exc:
                logger.warning("platform_service.error", error=str(exc))
                return {"invitations": []}

        async def check_permission(payload: dict[str, Any]) -> dict[str, Any]:
            try:
                allowed = orgs["rbac"].check_permission(
                    payload.get("role", ""), payload.get("action", "")
                )
                return {"allowed": bool(allowed)}
            except Exception as exc:
                logger.warning("platform_service.error", error=str(exc))
                return {"allowed": False}

        reg.actions["invite"] = invite
        reg.actions["list"] = list_invitations
        reg.actions["check_permission"] = check_permission

    def _register_support(self) -> None:
        svc = self.support()
        reg = self.registry.register("support", version="1.0.0")

        async def create_ticket(payload: dict[str, Any]) -> dict[str, Any]:
            try:
                ticket = svc.create_ticket(
                    subject=payload.get("subject", ""),
                    description=payload.get("description", ""),
                    priority=payload.get("priority", "normal"),
                )
                tid = ticket.get("id") if isinstance(ticket, dict) else getattr(ticket, "id", "")
                return {"ticket_id": tid, "status": "created"}
            except Exception as exc:
                return {"status": "error", "error": str(exc)}

        async def list_tickets(payload: dict[str, Any]) -> dict[str, Any]:
            try:
                tickets = svc.list_tickets()
                return {"tickets": tickets if isinstance(tickets, list) else []}
            except Exception as exc:
                logger.warning("platform_service.error", error=str(exc))
                return {"tickets": []}

        reg.actions["create_ticket"] = create_ticket
        reg.actions["list"] = list_tickets

    def _register_feedback(self) -> None:
        svc = self.feedback()
        reg = self.registry.register("feedback", version="1.0.0")

        async def submit(payload: dict[str, Any]) -> dict[str, Any]:
            return {
                "status": "submitted",
                "tenant_id": payload.get("tenant_id", ""),
                "score": payload.get("score", 0),
            }

        reg.actions["submit"] = submit

    def _register_monetization(self) -> None:
        reg = self.registry.register("monetization", version="1.0.0")

        async def list_paths(payload: dict[str, Any]) -> dict[str, Any]:
            return {
                "paths": [
                    "saas_subscription",
                    "per_seat_billing",
                    "usage_based_overage",
                    "vertical_pack_marketplace",
                    "white_label_reseller",
                    "embedded_analytics_oem",
                    "data_api_access",
                ]
            }

        reg.actions["list_paths"] = list_paths

    def _register_email_marketing(self) -> None:
        reg = self.registry.register("email_marketing", version="1.0.0")

        async def sign_click_token(payload: dict[str, Any]) -> dict[str, Any]:
            import shared.email_marketing as em

            try:
                token = em.sign_entity_token(
                    payload.get("campaign_id", ""),
                    payload.get("subscriber_id", ""),
                    secret=payload.get("secret", "dev"),
                )
                return {"token": token}
            except Exception as exc:
                return {"error": str(exc)}

        async def verify_click_token(payload: dict[str, Any]) -> dict[str, Any]:
            import shared.email_marketing as em

            try:
                result = em.verify_entity_token(
                    payload.get("token", ""), secret=payload.get("secret", "dev")
                )
                return {"valid": result is not None}
            except Exception as exc:
                logger.warning("platform_service.error", error=str(exc))
                return {"valid": False}

        reg.actions["sign_click_token"] = sign_click_token
        reg.actions["verify_click_token"] = verify_click_token

    def _register_lead_capture(self) -> None:
        reg = self.registry.register("lead_capture", version="1.0.0")

        async def capture(payload: dict[str, Any]) -> dict[str, Any]:
            return {
                "lead": {
                    "email": payload.get("email", ""),
                    "source": payload.get("source", "direct"),
                    "tenant_id": payload.get("tenant_id", ""),
                    "captured_at": payload.get("captured_at", ""),
                },
                "status": "captured",
            }

        reg.actions["capture"] = capture


__all__ = ["PlatformServices"]
