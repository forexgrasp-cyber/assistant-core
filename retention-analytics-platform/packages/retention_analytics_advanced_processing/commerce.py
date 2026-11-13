"""Commerce + retention analytics that close the Hiro gaps:

1. Time between orders — median gap, attributed (after a campaign/flow) vs on their own
2. Product purchase paths — 1st -> 2nd -> 3rd purchase paths, retention by product
3. Subscription LTV by product at 1/3/6/12m + one-time -> subscriber conversion
   + product trends (most starts, fastest growing, most cancels, top add-on)
4. RFM movement over time — segment counts moving, net change, biggest moves

All operate on orders stored through the orders repository (tenant-scoped).
"""

from __future__ import annotations

import json
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from retention_analytics_core.repository import repository_for
from retention_analytics_core.service_registry import ServiceRegistry

logger = structlog.get_logger(__name__)

ORDER_BUCKETS = [(0, 30), (30, 60), (60, 90), (90, 120), (120, 180), (180, 360), (360, 10_000)]
RFM_SEGMENTS = ["champions", "loyal", "needs_attention", "at_risk", "inactive"]


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    mid = len(s) // 2
    if len(s) % 2:
        return float(s[mid])
    return round((s[mid - 1] + s[mid]) / 2, 1)


class CommerceAnalytics:
    """Order/product/subscription analytics over tenant-scoped records."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("analytics.commerce", version="1.0.0", metadata={"domain": "analytics", "type": "commerce"})
        reg.actions["record_order"] = self._record_order
        reg.actions["time_between_orders"] = self._time_between
        reg.actions["product_paths"] = self._product_paths
        reg.actions["subscription_ltv"] = self._subscription_ltv
        reg.actions["one_time_to_subscriber"] = self._one_time_to_sub
        reg.actions["product_trends"] = self._product_trends
        reg.actions["rfm_movement"] = self._rfm_movement

    # ------------------------------------------------------------ data in
    async def _record_order(self, p: dict[str, Any]) -> dict[str, Any]:
        """Record a purchase (order) with products, campaign attribution and subscription flag."""
        order = {
            "order_id": p.get("order_id") or f"ord-{uuid.uuid4().hex[:10]}",
            "tenant_id": p.get("tenant_id", ""),
            "customer_email": p.get("customer_email", ""),
            "customer_id": p.get("customer_id", ""),
            "amount": float(p.get("amount", 0)),
            "currency": p.get("currency", "USD"),
            "products": p.get("products", []),  # [{name, sku, units, revenue, type: one_time|subscription|add_on}]
            "campaign_id": p.get("campaign_id", ""),
            "flow_id": p.get("flow_id", ""),
            "is_subscription": bool(p.get("is_subscription", False)),
            "subscription_product": p.get("subscription_product", ""),
            "placed_at": p.get("placed_at", datetime.now(UTC).isoformat()),
            "created_at": datetime.now(UTC).isoformat(),
        }
        repo = repository_for("orders", order["tenant_id"])
        await repo.save(order["order_id"], order)
        return {"status": "recorded", "order": order}

    async def _orders(self, tenant: str) -> list[dict[str, Any]]:
        records = await repository_for("orders", tenant).list_all()
        rows = []
        for item in records:
            if isinstance(item, tuple):
                rec = item[1]
            elif isinstance(item, dict):
                rec = item
            else:
                continue
            if isinstance(rec, dict):
                rows.append(rec)
        rows.sort(key=lambda x: str(x.get("placed_at", "")))
        return rows

    # ------------------------------------------- 1. time between orders
    async def _time_between(self, p: dict[str, Any]) -> dict[str, Any]:
        """Median days between orders: all, after a campaign/flow, and on their own."""
        tenant = p.get("tenant_id", "")
        orders = await self._orders(tenant)
        by_customer: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for o in orders:
            by_customer[str(o.get("customer_email") or o.get("customer_id") or "")].append(o)

        all_gaps, attributed_gaps, organic_gaps = [], [], []
        for cust_orders in by_customer.values():
            for prev, nxt in zip(cust_orders, cust_orders[1:]):
                try:
                    d1 = datetime.fromisoformat(str(prev["placed_at"]).replace("Z", "+00:00"))
                    d2 = datetime.fromisoformat(str(nxt["placed_at"]).replace("Z", "+00:00"))
                except Exception:
                    continue
                gap = (d2 - d1).days
                if gap <= 0:
                    continue
                all_gaps.append(gap)
                if nxt.get("campaign_id") or nxt.get("flow_id"):
                    attributed_gaps.append(gap)
                else:
                    organic_gaps.append(gap)

        buckets = []
        for lo, hi in ORDER_BUCKETS:
            count = sum(1 for g in all_gaps if lo <= g < hi)
            buckets.append({"range": f"{lo}-{hi if hi < 10_000 else '+'}d", "from": lo,
                            "to": None if hi >= 10_000 else hi, "count": count})

        med_all = _median(all_gaps)
        med_attr = _median(attributed_gaps)
        med_org = _median(organic_gaps)
        return {
            "status": "ok",
            "returning_customers": sum(1 for v in by_customer.values() if len(v) > 1),
            "all_reorders": len(all_gaps),
            "median_gap_days": med_all,
            "after_campaign": {"reorders": len(attributed_gaps), "median_gap_days": med_attr,
                               "days_sooner": round(med_org - med_attr, 1) if med_attr and med_org else None},
            "on_their_own": {"reorders": len(organic_gaps), "median_gap_days": med_org},
            "buckets": buckets,
        }

    # ------------------------------------------ 2. product purchase paths
    async def _product_paths(self, p: dict[str, Any]) -> dict[str, Any]:
        """1st -> 2nd -> 3rd purchase paths, retention by product, keyword filter."""
        tenant = p.get("tenant_id", "")
        keyword = (p.get("keyword") or "").lower().strip()
        orders = await self._orders(tenant)
        by_customer: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for o in orders:
            by_customer[str(o.get("customer_email") or o.get("customer_id") or "")].append(o)

        path_counts: Counter = Counter()
        product_first: Counter = Counter()
        product_repeat: Counter = Counter()
        product_customers: dict[str, set] = defaultdict(set)
        product_retained: dict[str, set] = defaultdict(set)

        def products_of(order: dict[str, Any]) -> list[str]:
            names = []
            for pr in order.get("products", []):
                n = pr.get("name", "") if isinstance(pr, dict) else str(pr)
                if keyword and keyword not in n.lower():
                    continue
                names.append(n)
            return names

        for cust_orders in by_customer.values():
            seq = [products_of(o) for o in cust_orders]
            seq = [s for s in seq if s]
            if not seq:
                continue
            for name in set(seq[0]):
                product_first[name] += 1
                product_customers[name].add(cust_orders[0].get("customer_email", ""))
            # a "repeat buyer" of a product = bought it again in any later order
            bought_later = set()
            for later in seq[1:]:
                bought_later.update(later)
            for name in set(seq[0]) & bought_later:
                product_repeat[name] += 1
                product_retained[name].add(cust_orders[0].get("customer_email", ""))
            if len(seq) >= 2:
                for name in set(seq[1]):
                    product_repeat[name] += 0  # second-order products are not repeats of themselves
                path_counts[" → ".join([seq[0][0], seq[1][0]])] += 1
            if len(seq) >= 3:
                path_counts[" → ".join([seq[0][0], seq[1][0], seq[2][0]])] += 1

        by_product = []
        for name, first in product_first.most_common():
            custs = len(product_customers.get(name, set()))
            retained = len(product_retained.get(name, set()))
            by_product.append({"product": name, "first_time_buyers": first,
                               "repeat_buyers": product_repeat.get(name, 0),
                               "repeat_rate": round(retained / custs * 100, 1) if custs else 0})

        return {"status": "ok", "keyword": keyword or None,
                "paths": [{"path": k, "count": v} for k, v in path_counts.most_common(25)],
                "by_product": by_product, "customers": len(by_customer)}

    # ------------------------- 3. subscription LTV + one-time->subscriber
    async def _subscription_ltv(self, p: dict[str, Any]) -> dict[str, Any]:
        """Subscription LTV by starting product at 1/3/6/12 months."""
        tenant = p.get("tenant_id", "")
        orders = await self._orders(tenant)
        starts: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for o in orders:
            if o.get("is_subscription") and o.get("subscription_product"):
                starts[o["subscription_product"]].append(o)

        out = []
        for product, prod_orders in starts.items():
            rows = []
            for months in (1, 3, 6, 12):
                cutoff = datetime.now(UTC) - timedelta(days=months * 30)
                value = 0.0
                for o in prod_orders:
                    placed = datetime.fromisoformat(str(o["placed_at"]).replace("Z", "+00:00"))
                    if placed >= cutoff:
                        value += float(o.get("amount", 0))
                rows.append({"months": months, "value": round(value, 2)})
            out.append({"product": product, "subscribers": len(prod_orders),
                        "ltv": rows,
                        "ltv_12m": next((r["value"] for r in rows if r["months"] == 12), 0)})
        out.sort(key=lambda x: x["ltv_12m"], reverse=True)
        return {"status": "ok", "by_product": out, "total_subscription_starts": sum(len(v) for v in starts.values())}

    async def _one_time_to_sub(self, p: dict[str, Any]) -> dict[str, Any]:
        """Which one-time purchases become subscribers, and how fast."""
        tenant = p.get("tenant_id", "")
        orders = await self._orders(tenant)
        by_customer: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for o in orders:
            by_customer[str(o.get("customer_email") or o.get("customer_id") or "")].append(o)

        converted = 0
        days_total = 0
        first_product: Counter = Counter()
        for cust_orders in by_customer.values():
            one_time = [o for o in cust_orders if not o.get("is_subscription")]
            subs = [o for o in cust_orders if o.get("is_subscription")]
            if not one_time or not subs:
                continue
            converted += 1
            try:
                d1 = datetime.fromisoformat(str(one_time[0]["placed_at"]).replace("Z", "+00:00"))
                d2 = datetime.fromisoformat(str(subs[0]["placed_at"]).replace("Z", "+00:00"))
                days_total += max(0, (d2 - d1).days)
            except Exception:
                pass
            for pr in one_time[0].get("products", []):
                n = pr.get("name", "") if isinstance(pr, dict) else str(pr)
                if n:
                    first_product[n] += 1

        one_time_buyers = sum(1 for v in by_customer.values() if any(not o.get("is_subscription") for o in v))
        rate = round(converted / one_time_buyers * 100, 1) if one_time_buyers else 0
        return {"status": "ok", "one_time_buyers": one_time_buyers, "converted": converted,
                "conversion_rate": rate,
                "avg_days_to_subscribe": round(days_total / converted, 1) if converted else None,
                "best_first_product": first_product.most_common(1)[0][0] if first_product else None}

    async def _product_trends(self, p: dict[str, Any]) -> dict[str, Any]:
        """Most new starts, fastest growing, most cancels, top one-time add-on."""
        tenant = p.get("tenant_id", "")
        orders = await self._orders(tenant)
        now = datetime.now(UTC)
        current_cut = now - timedelta(days=30)
        prev_cut = now - timedelta(days=60)

        starts_cur, starts_prev = Counter(), Counter()
        cancels_cur = Counter()
        addons = Counter()
        for o in orders:
            placed = datetime.fromisoformat(str(o["placed_at"]).replace("Z", "+00:00"))
            is_sub = bool(o.get("is_subscription"))
            prod = o.get("subscription_product") or ""
            if is_sub and prod:
                if placed >= current_cut:
                    starts_cur[prod] += 1
                elif placed >= prev_cut:
                    starts_prev[prod] += 1
            if o.get("cancelled") and o.get("subscription_product"):
                if placed >= current_cut:
                    cancels_cur[o["subscription_product"]] += 1
            if not is_sub:
                for pr in o.get("products", []):
                    n = pr.get("name", "") if isinstance(pr, dict) else str(pr)
                    if n and (pr.get("type") == "add_on" if isinstance(pr, dict) else False):
                        addons[n] += 1

        def growth(name: str) -> int:
            cur, prev = starts_cur.get(name, 0), starts_prev.get(name, 0)
            return cur - prev

        return {
            "status": "ok",
            "most_new_starts": [{"product": k, "starts": v, "change": growth(k)} for k, v in starts_cur.most_common(5)],
            "fastest_growing": [{"product": k, "change": growth(k)} for k, _ in sorted(starts_cur.items(), key=lambda kv: growth(kv[0]), reverse=True)[:5]],
            "most_cancels": [{"product": k, "cancels": v} for k, v in cancels_cur.most_common(5)],
            "top_add_on": [{"product": k, "orders": v} for k, v in addons.most_common(5)],
        }

    # ----------------------------------------------- 4. RFM movement
    async def _rfm_movement(self, p: dict[str, Any]) -> dict[str, Any]:
        """Segment counts moving between two periods + the biggest moves."""
        tenant = p.get("tenant_id", "")
        orders = await self._orders(tenant)
        now = datetime.now(UTC)
        cur_cut = now - timedelta(days=30)
        prev_cut = now - timedelta(days=60)

        def segment_for(days_since: float, freq: int, monetary: float) -> str:
            if days_since <= 30 and freq >= 4:
                return "champions"
            if days_since <= 60 and freq >= 2:
                return "loyal"
            if days_since <= 90:
                return "needs_attention"
            if days_since <= 180:
                return "at_risk"
            return "inactive"

        def buckets(since: datetime, until: datetime | None) -> dict[str, str]:
            by_cust: dict[str, list[dict]] = defaultdict(list)
            for o in orders:
                placed = datetime.fromisoformat(str(o["placed_at"]).replace("Z", "+00:00"))
                if placed < since or (until and placed >= until):
                    continue
                by_cust[str(o.get("customer_email") or o.get("customer_id") or "")].append(o)
            out = {}
            for cust, cust_orders in by_cust.items():
                days_since = (until or now) - datetime.fromisoformat(str(cust_orders[-1]["placed_at"]).replace("Z", "+00:00"))
                freq = len(cust_orders)
                monetary = sum(float(o.get("amount", 0)) for o in cust_orders)
                out[cust] = segment_for(days_since.total_seconds() / 86400, freq, monetary)
            return out

        current = buckets(cur_cut, None)
        previous = buckets(prev_cut, cur_cut)

        movement = Counter()
        attributed_moves = Counter()
        campaign_by_customer: dict[str, str] = {}
        for o in orders:
            if o.get("campaign_id") or o.get("flow_id"):
                campaign_by_customer[str(o.get("customer_email") or o.get("customer_id") or "")] = \
                    o.get("campaign_id") or o.get("flow_id")

        for cust, seg in current.items():
            old = previous.get(cust)
            if old and old != seg:
                movement[f"{old}→{seg}"] += 1
                camp = campaign_by_customer.get(cust)
                if camp:
                    attributed_moves[f"{old}→{seg}"] += 1

        counts = {s: sum(1 for v in current.values() if v == s) for s in RFM_SEGMENTS}
        prev_counts = {s: sum(1 for v in previous.values() if v == s) for s in RFM_SEGMENTS}
        net = {s: counts[s] - prev_counts[s] for s in RFM_SEGMENTS}
        biggest = [{"move": k, "count": v, "attributed": attributed_moves.get(k, 0),
                    "attributed_pct": round(attributed_moves.get(k, 0) / v * 100, 1) if v else 0}
                   for k, v in movement.most_common(10)]
        return {"status": "ok", "segments": [{"segment": s, "customers": counts[s],
                                             "previous": prev_counts[s], "net_change": net[s]} for s in RFM_SEGMENTS],
                "biggest_moves": biggest, "attributed_share": round(
                    sum(attributed_moves.values()) / max(sum(movement.values()), 1) * 100, 1)}


__all__ = ["CommerceAnalytics", "ORDER_BUCKETS", "RFM_SEGMENTS"]
