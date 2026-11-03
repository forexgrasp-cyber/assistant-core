"""Cohort service.

Computes retention cohorts per tenant from the persisted order history and
persists the cohort result, so dashboards and reports consume real cohort
data instead of a hardcoded sample.

A cohort is the set of customers whose first order falls in a given month.
Each cohort row reports how much of that cohort ordered again in the
following months.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

import structlog
from retention_analytics_core.repository import new_id, repository_for
from retention_analytics_core.service_base import CanonicalService

logger = structlog.get_logger(__name__)


class CohortService(CanonicalService):
    SERVICE_NAME = "analytics.cohort"

    def __init__(self, registry: Any) -> None:
        super().__init__("analytics.cohort", registry)
        self.register_action("compute_cohorts", self._compute_cohorts)

    def register(
        self,
        subscribes_to: list | None = None,
        metadata: dict[str, Any] | None = None,
        service_type: str = "platform",
    ) -> None:
        super().register(
            subscribes_to=subscribes_to,
            metadata={**(metadata or {}), "domain": "analytics"},
            service_type=service_type,
        )

    def _tenant(self, payload: dict[str, Any]) -> str:
        return str(payload.get("tenant_id") or "default")

    async def _compute_cohorts(self, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = self._tenant(payload)
        cohort_months = int(payload.get("cohort_months", 6))
        orders = [record for _id, record in await repository_for("orders", tenant_id).list_all()]

        first_order: dict[str, datetime] = {}
        active_months: dict[str, set[str]] = defaultdict(set)

        for order in orders:
            if not isinstance(order, dict):
                continue
            email = str(order.get("customer_email") or "")
            placed_at = _placed_at(order)
            if not email or placed_at is None:
                continue
            month = placed_at.strftime("%Y-%m")
            active_months[email].add(month)
            current = first_order.get(email)
            if current is None or placed_at < current:
                first_order[email] = placed_at

        cohort_members: dict[str, set[str]] = defaultdict(set)
        for email, first in first_order.items():
            cohort_members[first.strftime("%Y-%m")].add(email)

        cohorts: list[dict[str, Any]] = []
        for cohort_month in sorted(cohort_members)[-cohort_months:]:
            members = cohort_members[cohort_month]
            rows = []
            for offset in range(0, cohort_months):
                target = _add_months(cohort_month, offset)
                active = sum(
                    1
                    for email in members
                    if target in active_months.get(email, set())
                    and target >= cohort_month
                )
                rows.append(
                    {
                        "month": target,
                        "retained": active,
                        "size": len(members),
                        "retention": round(active / len(members), 4) if members else 0.0,
                    }
                )
            cohorts.append({"cohort": cohort_month, "size": len(members), "months": rows})

        result = {
            "metric": "cohorts",
            "tenant_id": tenant_id,
            "cohort_months": cohort_months,
            "cohorts": cohorts,
            "computed_at": datetime.now(UTC).isoformat(),
        }
        cohort_id = new_id("coh")
        await repository_for("cohorts", tenant_id).save(cohort_id, {**result, "cohort_id": cohort_id})
        logger.info("cohort.compute", tenant_id=tenant_id, cohorts=len(cohorts))
        return {**result, "cohort_id": cohort_id}


def _placed_at(order: dict[str, Any]) -> datetime | None:
    raw = order.get("placed_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


def _add_months(year_month: str, offset: int) -> str:
    year, month = (int(part) for part in year_month.split("-"))
    index = (year * 12 + (month - 1)) + offset
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


__all__ = ["CohortService"]
