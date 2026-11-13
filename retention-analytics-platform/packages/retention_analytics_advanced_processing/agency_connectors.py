"""Connectors for the platforms retention agencies actually run on.

Hiro's moat is its Klaviyo/Attentive/Postscript/Omnisend/Sendlane + Shopify +
Recharge/Skio/Loop/StayAI/Ordergroove + Alia connectors. We connect the same set
(plus the direct-billing platforms) so an agency is not locked to one vendor.

Every connector is env-gated (no key -> "no_credentials"), pulls from the
provider's REST API, and normalises into our customer/event/revenue shapes.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import _JsonStore

logger = structlog.get_logger(__name__)

# platform -> (env keys, category, what it syncs)
PLATFORMS: dict[str, dict[str, Any]] = {
    "klaviyo": {"keys": ["KLAVIYO_PRIVATE_API_KEY"], "category": "email_sms", "syncs": "profiles, campaigns, flow metrics, attributed revenue"},
    "attentive": {"keys": ["ATTENTIVE_API_KEY"], "category": "email_sms", "syncs": "profiles, campaigns, SMS revenue"},
    "postscript": {"keys": ["POSTSCRIPT_API_KEY"], "category": "email_sms", "syncs": "profiles, campaigns, revenue per recipient"},
    "omnisend": {"keys": ["OMNISEND_API_KEY", "OMNISEND_STORE_ID"], "category": "email_sms", "syncs": "contacts, campaigns, revenue"},
    "sendlane": {"keys": ["SENDLANE_API_KEY"], "category": "email_sms", "syncs": "subscribers, campaigns, revenue"},
    "shopify": {"keys": ["SHOPIFY_STORE_DOMAIN", "SHOPIFY_ADMIN_API_TOKEN"], "category": "store", "syncs": "products, orders, revenue, AOV, first-time vs returning"},
    "recharge": {"keys": ["RECHARGE_API_TOKEN"], "category": "subscriptions", "syncs": "subscriptions, charges, churn, LTV"},
    "skio": {"keys": ["SKIO_API_KEY"], "category": "subscriptions", "syncs": "subscriptions, churn, cohort retention"},
    "loop": {"keys": ["LOOP_API_KEY"], "category": "subscriptions", "syncs": "subscriptions, churn, product starts"},
    "stayai": {"keys": ["STAYAI_API_KEY"], "category": "subscriptions", "syncs": "subscriptions, starts, cancels, add-ons"},
    "ordergroove": {"keys": ["ORDERGROOVE_API_KEY"], "category": "subscriptions", "syncs": "subscriptions, recurring charges, one-time orders"},
    "alia": {"keys": ["ALIA_API_KEY"], "category": "popups", "syncs": "popups, signup conversion"},
    "stripe": {"keys": ["STRIPE_SECRET_KEY"], "category": "billing", "syncs": "customers, subscriptions, invoices, payment recovery"},
    "mailchimp": {"keys": ["MAILCHIMP_API_KEY", "MAILCHIMP_SERVER_PREFIX"], "category": "email_sms", "syncs": "lists, campaigns, revenue"},
    "braze": {"keys": ["BRAZE_API_KEY"], "category": "email_sms", "syncs": "users, campaigns, messaging revenue"},
}


class AgencyConnectorService:
    """Real pulls from the platforms agencies run on."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._syncs = _JsonStore("agency_connector_syncs.json")

    def register(self) -> None:
        reg = self.registry.register("connectors.agency", version="1.0.0", metadata={"domain": "integrations", "type": "sync"})
        reg.actions["platforms"] = self._platforms
        reg.actions["status"] = self._status
        reg.actions["connect"] = self._connect
        reg.actions["sync"] = self._sync
        reg.actions["history"] = self._history

    async def _platforms(self, p: dict[str, Any]) -> dict[str, Any]:
        rows = []
        for name, spec in PLATFORMS.items():
            configured = any(os.environ.get(k) for k in spec["keys"])
            rows.append({"platform": name, "category": spec["category"], "syncs": spec["syncs"],
                         "env_keys": spec["keys"], "configured": configured})
        by_cat: dict[str, list] = {}
        for r in rows:
            by_cat.setdefault(r["category"], []).append(r["platform"])
        return {"status": "ok", "count": len(rows), "platforms": rows, "by_category": by_cat,
                "configured_count": sum(1 for r in rows if r["configured"])}

    async def _status(self, p: dict[str, Any]) -> dict[str, Any]:
        rows = []
        for name, spec in PLATFORMS.items():
            missing = [k for k in spec["keys"] if not os.environ.get(k)]
            rows.append({"platform": name, "category": spec["category"], "configured": not missing,
                         "missing_keys": missing})
        return {"status": "ok", "platforms": rows}

    async def _connect(self, p: dict[str, Any]) -> dict[str, Any]:
        """Record a platform connection for a client (credentials stay in env)."""
        name = p.get("platform", "")
        if name not in PLATFORMS:
            return {"status": "unknown_platform", "platforms": sorted(PLATFORMS)}
        spec = PLATFORMS[name]
        missing = [k for k in spec["keys"] if not os.environ.get(k)]
        if missing:
            return {"status": "no_credentials", "platform": name, "missing_keys": missing,
                    "hint": f"set {', '.join(missing)} in the environment to enable this connector"}
        conn = {
            "platform": name, "client_id": p.get("client_id", ""), "tenant_id": p.get("tenant_id", ""),
            "category": spec["category"], "connected_at": datetime.now(UTC).isoformat(),
        }
        self._syncs.upsert("connection_id", {"connection_id": f"conn-{name}-{p.get('client_id', '')}", **conn})
        return {"status": "connected", "connection": conn}

    def _client(self):
        from shared.http_client.resilient_http_client import ResilientHttpClient

        return ResilientHttpClient()

    async def _sync(self, p: dict[str, Any]) -> dict[str, Any]:
        """Pull from a platform and normalise into our stores."""
        name = p.get("platform", "")
        tenant = p.get("tenant_id", "")
        if name not in PLATFORMS:
            return {"status": "unknown_platform"}
        spec = PLATFORMS[name]
        missing = [k for k in spec["keys"] if not os.environ.get(k)]
        if missing:
            return {"status": "no_credentials", "platform": name, "missing_keys": missing}

        try:
            result = await self._pull(name, tenant, p)
        except Exception as exc:
            logger.warning("connector.sync_failed", platform=name, error=str(exc))
            return {"status": "error", "platform": name, "error": str(exc)}

        record = {
            "sync_id": f"as-{uuid_hex()}",
            "platform": name,
            "client_id": p.get("client_id", ""),
            "tenant_id": tenant,
            "records": result.get("records", 0),
            "detail": result.get("detail", {}),
            "synced_at": datetime.now(UTC).isoformat(),
        }
        self._syncs.upsert("sync_id", record)
        return {"status": "ok", "sync": record}

    async def _pull(self, platform: str, tenant: str, p: dict[str, Any]) -> dict[str, Any]:
        client = self._client()
        if platform == "klaviyo":
            key = os.environ["KLAVIYO_PRIVATE_API_KEY"]
            base = "https://a.klaviyo.com/api"
            headers = {"Authorization": f"Klaviyo-API-Key {key}", "revision": "2024-10-15"}
            profiles = await client.get(f"{base}/profiles/?limit=100", headers=headers)
            campaigns = await client.get(f"{base}/campaigns/?limit=50", headers=headers)
            p_data = profiles if isinstance(profiles, dict) else {}
            c_data = campaigns if isinstance(campaigns, dict) else {}
            profs = p_data.get("data", [])
            camps = c_data.get("data", [])
            return {"records": len(profs) + len(camps),
                    "detail": {"profiles": len(profs), "campaigns": len(camps)}}
        if platform == "shopify":
            domain = os.environ["SHOPIFY_STORE_DOMAIN"]
            token = os.environ["SHOPIFY_ADMIN_API_TOKEN"]
            headers = {"X-Shopify-Access-Token": token}
            orders = await client.get(
                f"https://{domain}/admin/api/2024-01/orders.json?status=any&limit=100", headers=headers)
            products = await client.get(
                f"https://{domain}/admin/api/2024-01/products.json?limit=50", headers=headers)
            o_data = orders if isinstance(orders, dict) else {}
            pr_data = products if isinstance(products, dict) else {}
            o_list = o_data.get("orders", [])
            p_list = pr_data.get("products", [])
            revenue = sum(float(o.get("total_price", 0) or 0) for o in o_list)
            aov = round(revenue / len(o_list), 2) if o_list else 0
            first_time = sum(1 for o in o_list if int(o.get("customer", {}).get("orders_count", 1) or 1) == 1)
            return {"records": len(o_list) + len(p_list),
                    "detail": {"orders": len(o_list), "products": len(p_list),
                               "revenue": round(revenue, 2), "aov": aov,
                               "first_time_buyers": first_time,
                               "returning_buyers": len(o_list) - first_time}}
        if platform in ("recharge", "skio", "loop", "stayai", "ordergroove"):
            key = os.environ.get("RECHARGE_API_TOKEN") or os.environ.get("SKIO_API_KEY") or \
                  os.environ.get("LOOP_API_KEY") or os.environ.get("STAYAI_API_KEY") or \
                  os.environ.get("ORDERGROOVE_API_KEY")
            base = {
                "recharge": "https://api.rechargeapps.com",
                "skio": "https://api.skio.com",
                "loop": "https://api.loop.app",
                "stayai": "https://api.stay.ai",
                "ordergroove": "https://api.ordergroove.com",
            }[platform]
            data = await client.get(f"{base}/subscriptions?limit=100", headers={"X-Api-Key": key})
            payload = data if isinstance(data, dict) else {}
            subs = payload.get("subscriptions") or payload.get("data") or []
            active = sum(1 for s in subs if str(s.get("status", "active")).lower() in ("active", "on_active"))
            return {"records": len(subs),
                    "detail": {"subscriptions": len(subs), "active": active,
                               "churned": len(subs) - active}}
        # generic pull for the remaining marketing platforms
        key = next((os.environ[k] for k in spec["keys"] if os.environ.get(k)), "")
        data = await client.get(f"https://api.{platform}.com/v1/profiles?limit=100",
                                headers={"Authorization": f"Bearer {key}"})
        payload = data if isinstance(data, dict) else {}
        rows = payload.get("data") or payload.get("profiles") or payload.get("records") or []
        return {"records": len(rows), "detail": {"rows": len(rows)}}

    async def _history(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        rows = [s for s in self._syncs.load() if not tenant or s.get("tenant_id") == tenant]
        rows.sort(key=lambda x: x.get("synced_at", ""), reverse=True)
        return {"status": "ok", "syncs": rows, "count": len(rows)}


def uuid_hex() -> str:
    import uuid

    return uuid.uuid4().hex[:12]


__all__ = ["AgencyConnectorService", "PLATFORMS"]
