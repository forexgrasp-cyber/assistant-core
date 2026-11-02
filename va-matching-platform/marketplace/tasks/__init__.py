"""
Background tasks — thin orchestration over the canonical async job stack.

Job wiring (priority queue, retries/backoff, timeouts, persistence, DLQ)
is canonical ``shared.async_jobs`` (no Celery):

    BackgroundTaskManager   FastAPI lifespan + /tasks submit/status router
    AsyncTaskQueue          canonical async-native queue
    idempotent              run-once guarantees (param-keyed)

Marketplace jobs registered here:
    run_vetting                 score a VA, update vetting status/scores
    search_candidates           adapter-driven candidate sourcing
    monthly_fee_sweep           charge monthly platform fees for a period
    connect_va_payout_account   Stripe Connect onboarding for a VA

Usage:
    manager = get_task_manager()
    app.include_router(manager.router)      # /tasks endpoints
    await manager.queue.start()             # via manager.lifespan/app hooks
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from shared.async_jobs import (
    BackgroundTaskManager,
    idempotent,
    get_dead_letter_queue,
    get_idempotency_manager,
)

from marketplace.base import VAProfile as BaseVAProfile
from marketplace.base import VAStatus
from marketplace.database import get_session
from marketplace.database.repositories import (
    ClientProfileRepository,
    MatchRepository,
    VAProfileRepository,
)
from marketplace.models import VAProfile as ORMVAProfile
from marketplace.payments import PaymentService

__all__ = ["PlatformTaskManager", "get_task_manager"]

log = structlog.get_logger(__name__)


def _dict_to_skill(s: Any) -> Any:
    """Build a base VASkill from a dict (tolerant of partial data)."""
    from marketplace.base import VASkill

    if isinstance(s, dict):
        try:
            proficiency = int(s.get("proficiency", 3) or 3)
        except (TypeError, ValueError):
            proficiency = 3
        return VASkill(
            name=str(s.get("name", "")),
            category=str(s.get("category", "")) or "general",
            proficiency=max(1, min(5, proficiency)),
            years_experience=float(s.get("years_experience", 0) or 0),
            certifications=list(s.get("certifications", []) or []),
        )
    return VASkill(name=str(s), category="general", proficiency=3)


def skills_to_dicts(skills: Any) -> list[dict[str, Any]]:
    """JSON-safe skill rows from dicts, strings, or base.VASkill objects."""
    out: list[dict[str, Any]] = []
    for s in skills or []:
        if isinstance(s, dict):
            out.append(s)
        elif hasattr(s, "name"):  # base.VASkill dataclass
            out.append(
                {
                    "name": str(s.name),
                    "category": str(getattr(s, "category", "") or "general"),
                    "proficiency": int(getattr(s, "proficiency", 3) or 3),
                    "years_experience": float(getattr(s, "years_experience", 0) or 0),
                    "certifications": list(getattr(s, "certifications", []) or []),
                }
            )
        else:
            out.append({"name": str(s), "category": "general"})
    return out


def _orm_to_base(p: ORMVAProfile) -> BaseVAProfile:
    """Map the ORM VAProfile onto the base.VAProfile used by services."""
    return BaseVAProfile(
        id=str(p.id),
        email=p.email,
        full_name=p.full_name,
        timezone=p.timezone or "UTC",
        hourly_rate=float(p.hourly_rate or 0),
        availability_hours_per_week=p.availability_hours_per_week or 0,
        skills=[_dict_to_skill(s) for s in (p.skills or [])],
        languages=list(p.languages or ["English"]),
        location=p.location or "",
        bio=p.bio or "",
        portfolio_url=p.portfolio_url or "",
        linkedin_url=p.linkedin_url or "",
        status=VAStatus(p.status.value if hasattr(p.status, "value") else str(p.status)),
        source=p.source or "",
        source_profile_url=p.source_profile_url or "",
        source_rating=float(p.source_rating or 0),
        source_reviews_count=p.source_reviews_count or 0,
        vetting_score=float(p.vetting_score or 0),
        english_test_score=float(p.english_test_score or 0),
        trial_task_score=float(p.trial_task_score or 0),
        reference_check_passed=bool(p.reference_check_passed),
    )


class PlatformTaskManager(BackgroundTaskManager):
    """Canonical BackgroundTaskManager pre-registered with marketplace jobs."""

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._register_marketplace_jobs()
        self._idempotency = get_idempotency_manager()
        self._dlq = get_dead_letter_queue()

    def _register_marketplace_jobs(self) -> None:
        for name, func in {
            "run_vetting": task_run_vetting,
            "search_candidates": task_search_candidates,
            "monthly_fee_sweep": task_monthly_fee_sweep,
            "connect_va_payout_account": task_connect_va_payout_account,
        }.items():
            self.register_function(name, func)


_task_manager: PlatformTaskManager | None = None


def get_task_manager() -> PlatformTaskManager:
    """Cached background manager singleton (canonical queue underneath)."""
    global _task_manager
    if _task_manager is None:
        _task_manager = PlatformTaskManager(max_concurrent=10)
    return _task_manager


# ── job bodies ──────────────────────────────────────────────────────────


async def task_run_vetting(va_id: str) -> dict[str, Any]:
    """Run the canonical vetting workflow for one VA and persist scores."""
    from marketplace.vetting import VettingService

    async with get_session() as session:
        repo = VAProfileRepository(session)
        profile = await repo.get_by_id(va_id)
        if profile is None:
            return {"va_id": va_id, "error": "not_found"}

        core = _orm_to_base(profile)
        scored = await VettingService().vet_va(core)

        profile.vetting_score = Decimal(str(scored.vetting_score))
        profile.english_test_score = Decimal(str(scored.english_test_score))
        profile.trial_task_score = Decimal(str(scored.trial_task_score))
        profile.reference_check_passed = scored.reference_check_passed
        current_status = VAStatus(str(profile.status.value))
        if scored.vetting_score >= 0.6 and current_status in (VAStatus.PENDING, VAStatus.VETTING):
            from marketplace.models import VAStatus as ORMVAStatus

            profile.status = ORMVAStatus.ACTIVE
        await repo.update(profile)
        await session.commit()
        return {
            "va_id": va_id,
            "vetting_score": float(profile.vetting_score),
            "status": profile.status.value,
        }


async def task_search_candidates(request: dict[str, Any]) -> dict[str, Any]:
    """Source candidates via the adapter registry and persist new profiles."""
    from marketplace.adapters import default_registry

    skills = list(request.get("skills") or [])
    if not skills:
        return {"candidates_found": 0, "error": "no_skills"}

    candidates = await default_registry.search_all_sources(
        skills=skills,
        min_hourly_rate=request.get("min_hourly_rate"),
        max_hourly_rate=request.get("max_hourly_rate"),
        min_rating=request.get("min_rating"),
        timezone=request.get("timezone"),
        availability_hours=request.get("availability_hours"),
        limit=request.get("limit", 50),
    )
    persisted = 0
    async with get_session() as session:
        repo = VAProfileRepository(session)
        for cand in candidates:
            existing = await repo.get_by_external(source=cand.source, profile_url=cand.source_profile_url)
            if existing:
                continue
            session.add(
                ORMVAProfile(
                    email=cand.email,
                    full_name=cand.full_name,
                    timezone=cand.timezone,
                    hourly_rate=Decimal(str(cand.hourly_rate or 0)),
                    availability_hours_per_week=cand.availability_hours_per_week,
                    languages=cand.languages,
                    location=cand.location,
                    bio=cand.bio,
                    portfolio_url=cand.portfolio_url,
                    linkedin_url=cand.linkedin_url,
                    source=cand.source,
                    source_profile_url=cand.source_profile_url,
                    source_rating=Decimal(str(cand.source_rating)),
                    source_reviews_count=cand.source_reviews_count,
                    skills=skills_to_dicts(cand.skills),
                )
            )
            persisted += 1
        await session.commit()
    return {"candidates_found": len(candidates), "persisted": persisted}


@idempotent("monthly_fee_sweep", ttl_hours=20)
async def task_monthly_fee_sweep(period: str | None = None) -> dict[str, Any]:
    """Charge the monthly platform fee for active matches in a period.

    Idempotency is canonical (``shared.async_jobs.idempotent`` param keys)
    plus the SalesLedger duplicate guard keyed on (match, period).
    """
    payments = PaymentService()
    period = period or datetime.now(UTC).strftime("%Y-%m")

    charged = 0
    duplicates = 0
    failures: list[dict[str, Any]] = []
    async with get_session() as session:
        match_repo = MatchRepository(session)
        client_repo = ClientProfileRepository(session)
        for match in await match_repo.list_active_with_client():
            client = await client_repo.get_by_id(str(match.client_id))
            try:
                result = await payments.charge_monthly_platform_fee(
                    client_id=str(client.user_id if client else match.client_id),
                    match_id=str(match.id),
                    period=period,
                    customer_email=client.email if client else None,
                    va_id=str(match.va_id) if match.va_id else None,
                )
            except Exception as exc:  # noqa: BLE001 — collect, continue sweep
                failures.append({"match_id": str(match.id), "error": str(exc)})
                continue
            if result.duplicate:
                duplicates += 1
            else:
                charged += 1
    outcome = {
        "period": period,
        "charged": charged,
        "duplicates": duplicates,
        "failures": failures,
    }
    log.info("monthly_fee_sweep", **outcome)
    return outcome


async def task_connect_va_payout_account(va_id: str) -> dict[str, Any]:
    """Create the VA's Stripe Connect Express onboarding (canonical service)."""
    from shared.billing.stripe_connect_service import StripeConnectService

    async with get_session() as session:
        repo = VAProfileRepository(session)
        profile = await repo.get_by_id(va_id)
        if profile is None:
            return {"va_id": va_id, "error": "not_found"}

        svc = StripeConnectService(tenant_id="va-matching-platform")
        result = svc.create_connect_account(
            email=profile.email, country="US", metadata={"va_id": va_id}
        )
        if result.get("account_id"):
            profile.payout_account_id = result["account_id"]
            await repo.update(profile)
        await session.commit()
        return {"va_id": va_id, **result}
