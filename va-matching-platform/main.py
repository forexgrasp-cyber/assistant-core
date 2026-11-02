"""
VA Matching Platform - FastAPI Application
========================================== REST API for the VA Matching Platform.

Canonical-service wiring:
- auth        shared.auth.jwt_service (+ marketplace adapter)
- payments    shared.payments (Provider + WebhookGate + SalesLedger) via marketplace.payments
- jobs        shared.async_jobs.BackgroundTaskManager (/tasks router) via marketplace.tasks
- ledger      shared.payments.sales_ledger.SalesLedger via marketplace.banking
- notify      shared.communications EmailChannel via marketplace.notifications
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from marketplace.auth import (
    ensure_platform_login_user,
    get_auth_service,
    get_current_user,
    get_current_user_with_role,
    require_role,
)
from marketplace.banking import get_market_ledger
from marketplace.carriers import OnboardingManager
from marketplace.database import db_session, get_session, init_db
from marketplace.database.repositories import (
    ClientProfileRepository,
    DeliveryRepository,
    MatchRepository,
    NotificationRepository,
    PaymentRepository,
    SubscriptionRepository,
    UserRepository,
    VAProfileRepository,
)
from marketplace.models import (
    ClientProfile,
    ClientStatus,
    Delivery,
    Match,
    MatchStatus,
    Notification,
    OnboardingPlan,
    PaymentIntent,
    PaymentStatus,
    PaymentType,
    Subscription,
    UserRole,
    VAProfile,
    VAStatus as ORMVAStatus,
)
from marketplace.monitoring import add_monitoring
from marketplace.notifications import NotificationService
from marketplace.payments import PaymentService
from marketplace.rate_limiting import RateLimitMiddleware
from shared.async_jobs import TaskPriority
from marketplace.tasks import (
    _orm_to_base,
    get_task_manager,
    skills_to_dicts,
    task_run_vetting,
)

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create schema + wire services; Shutdown: canonical task queue."""
    log.info("Starting VA Matching Platform...")
    await init_db()
    app.state.payments = PaymentService()
    app.state.notifications = NotificationService()
    async with get_task_manager().lifespan(app):
        yield
    log.info("Shutting down VA Matching Platform...")


app = FastAPI(
    title="VA Matching Platform",
    description="Two-sided marketplace for VA matching - Buy Back Your Time",
    version="2026.10",
    lifespan=lifespan,
)

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    default_rate=100,
    default_per=60,
    auth_rate=5,
    auth_per=60,
    api_rate=30,
    api_per=60,
)

# Add monitoring (readiness, liveness, metrics, structured logging)
add_monitoring(app)

templates = Jinja2Templates(directory="frontend/templates")
app.include_router(get_task_manager().router, prefix="/tasks")


# ==================== SCHEMAS ====================


class ClientIntakeForm(BaseModel):
    """Client intake form data."""

    email: EmailStr
    company_name: str = Field(..., min_length=1, max_length=200)
    contact_name: str = Field(..., min_length=1, max_length=100)
    timezone: str = Field(..., description="IANA timezone, e.g., America/New_York")
    industry: str = Field(..., min_length=1, max_length=100)
    company_size: int = Field(..., ge=1)
    monthly_budget: float = Field(..., gt=0)
    needed_hours_per_week: int = Field(..., ge=1, le=80)
    required_skills: list[str] = Field(..., min_length=1)
    tasks_to_delegate: list[str] = Field(..., min_length=1)
    current_tools: list[str] = Field(default_factory=list)
    preferred_timezone_overlap_hours: int = Field(default=4, ge=1, le=12)
    max_hourly_rate: float = Field(default=0, ge=0)
    source: str = "direct"


class VASourceRequest(BaseModel):
    """Request to source VAs."""

    skills: list[str] = Field(..., min_length=1)
    min_hourly_rate: float | None = None
    max_hourly_rate: float | None = None
    min_rating: float | None = None
    timezone: str | None = None
    availability_hours: int | None = None
    limit: int = Field(default=20, ge=1, le=100)


class VAProfileResponse(BaseModel):
    """VA profile response."""

    id: str
    email: str
    full_name: str
    timezone: str
    hourly_rate: float
    availability_hours_per_week: int
    skills: list[dict]
    languages: list[str]
    location: str
    bio: str
    portfolio_url: str
    source: str
    source_rating: float
    source_reviews_count: int
    status: str
    vetting_score: float


class MatchRequest(BaseModel):
    """Match client with VAs."""

    client_id: str
    limit: int = Field(default=5, ge=1, le=10)
    min_score: float = Field(default=0.4, ge=0, le=1)


class MatchResponse(BaseModel):
    """Match response."""

    match_id: str
    client_id: str
    va_id: str
    match_score: float
    match_factors: dict
    status: str


class DeliveryCreate(BaseModel):
    """Create a delivery."""

    match_id: str
    task_id: str
    va_id: str
    client_id: str
    title: str
    description: str = ""


class DeliverySubmit(BaseModel):
    """Submit delivery."""

    delivery_id: str
    deliverables: list[str] = Field(..., min_length=1)
    hours_logged: float = Field(..., gt=0)


class DeliveryReview(BaseModel):
    """Review delivery."""

    delivery_id: str
    status: str = Field(
        ..., pattern="^(approved|rejected|revision_requested|delivered)$"
    )
    feedback: str = ""


class RefundRequest(BaseModel):
    """Refund request."""

    sale_intent_id: str
    payment_id: str
    amount: float | None = None
    reason: str = Field(default="requested_by_customer", min_length=1)


class MonthlyFeeRequest(BaseModel):
    """Monthly platform fee setup / cycle charge."""

    match_id: str
    period: str | None = None


class RegisterRequest(BaseModel):
    """Registration payload."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str
    company: str | None = None


class LoginRequest(BaseModel):
    """Login payload."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh payload."""

    refresh_token: str


class NotificationOut(BaseModel):
    """Notification payload."""

    id: str
    type: str
    title: str
    message: str
    read: bool
    created_at: str


def _va_row_response(p: VAProfile) -> VAProfileResponse:
    """ORM VAProfile -> API response model."""
    return VAProfileResponse(
        id=str(p.id),
        email=p.email,
        full_name=p.full_name,
        timezone=p.timezone or "UTC",
        hourly_rate=float(p.hourly_rate or 0),
        availability_hours_per_week=p.availability_hours_per_week,
        skills=[s if isinstance(s, dict) else {"name": s} for s in (p.skills or [])],
        languages=list(p.languages or []),
        location=p.location or "",
        bio=p.bio or "",
        portfolio_url=p.portfolio_url or "",
        source=p.source or "",
        source_rating=float(p.source_rating or 0),
        source_reviews_count=p.source_reviews_count,
        status=str(p.status.value),
        vetting_score=float(p.vetting_score or 0),
    )


# ==================== HEALTH / PAGES ====================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "va-matching-platform", "version": "2026.10"}


@app.get("/intake", response_class=HTMLResponse)
async def intake_form(request: Request):
    """Render client intake form."""
    return templates.TemplateResponse("intake.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


# ==================== AUTH (canonical JWTAuthService) ====================


@app.post("/api/auth/register")
async def register(payload: RegisterRequest):
    """Register through the canonical auth service."""
    return await get_auth_service().register(
        email=payload.email,
        password=payload.password,
        name=payload.name,
        company=payload.company,
    )


@app.post("/api/auth/login")
async def login(payload: LoginRequest):
    """Login through the canonical auth service."""
    result = await get_auth_service().login(payload.email, payload.password)
    auth_user = result.get("user") or {}
    user_id = str(auth_user.get("user_id") or result.get("user_id") or "")
    if user_id:
        async with get_session() as session:
            await ensure_platform_login_user(
                user_id=user_id, email=payload.email, session=session
            )
            await session.commit()
    return result


@app.post("/api/auth/refresh")
async def refresh(payload: RefreshRequest):
    """Rotate refresh token (canonical)."""
    return await get_auth_service().refresh_token(payload.refresh_token)


@app.get("/api/auth/me")
async def me(user: dict = Depends(get_current_user_with_role)):
    """Current user (auth claims + marketplace role)."""
    return user


# ==================== CLIENT INTAKE ====================


@app.post("/api/clients")
async def create_client(
    form: ClientIntakeForm,
    user: dict = Depends(get_current_user),
    session: Any = Depends(db_session),
):
    """Create a client profile from the intake form (auth user linked)."""
    try:
        await ensure_platform_login_user(
            user_id=user["user_id"], email=user["email"], session=session
        )
        platform_user = await UserRepository(session).get_by_id(user["user_id"])

        client_repo = ClientProfileRepository(session)
        if await client_repo.get_by_user_id(user["user_id"]):
            raise HTTPException(409, "Client profile already exists")
        client = ClientProfile(
            user_id=platform_user.id if platform_user else user["user_id"],
            email=str(form.email),
            company_name=form.company_name,
            contact_name=form.contact_name,
            timezone=form.timezone,
            industry=form.industry,
            company_size=form.company_size,
            monthly_budget=Decimal(str(form.monthly_budget)),
            needed_hours_per_week=form.needed_hours_per_week,
            required_skills=form.required_skills,
            tasks_to_delegate=form.tasks_to_delegate,
            current_tools=form.current_tools,
            preferred_timezone_overlap_hours=form.preferred_timezone_overlap_hours,
            max_hourly_rate=Decimal(str(form.max_hourly_rate)),
            source=form.source,
            status=ClientStatus.LEAD,
        )
        await client_repo.create(client)
        await session.commit()
        return {"client_id": str(client.id), "message": "Client created successfully"}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        log.error("Client creation failed: %s", exc)
        raise HTTPException(500, f"Client creation failed: {exc}")


@app.get("/api/clients/{client_id}")
async def get_client(client_id: str, session: Any = Depends(db_session)):
    """Get client profile."""
    client = await ClientProfileRepository(session).get_by_id(client_id)
    if client is None:
        raise HTTPException(404, "Client not found")
    return {
        "client_id": str(client.id),
        "email": client.email,
        "company_name": client.company_name,
        "timezone": client.timezone,
        "status": client.status.value,
        "needed_hours_per_week": client.needed_hours_per_week,
    }


# ==================== VA SOURCING ====================


@app.post("/api/vas/search", response_model=list[VAProfileResponse])
async def search_vas(request: VASourceRequest, session: Any = Depends(db_session)):
    """Search VAs across all sources; persist new candidates; enqueue vetting."""
    from marketplace.adapters import get_default_registry

    registry = get_default_registry(dry_run=True)
    candidates = await registry.search_all_sources(
        skills=request.skills,
        min_hourly_rate=request.min_hourly_rate,
        max_hourly_rate=request.max_hourly_rate,
        min_rating=request.min_rating,
        timezone=request.timezone,
        availability_hours=request.availability_hours,
        limit=request.limit,
    )
    new_ids: list[str] = []
    known_rows = []
    repo = VAProfileRepository(session)
    for cand in candidates:
        found = await repo.get_by_external(
            source=cand.source, profile_url=cand.source_profile_url
        )
        if found:
            known_rows.append(found)
            continue
        profile = VAProfile(
            id=str(uuid4()),
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
            status=ORMVAStatus.PENDING,
        )
        session.add(profile)
        known_rows.append(profile)
        new_ids.append(str(profile.id))
    await session.commit()

    manager = get_task_manager()
    for va_id in new_ids:
        try:
            await manager.submit(task_run_vetting, va_id, priority=TaskPriority.HIGH)
        except Exception as exc:  # noqa: BLE001 — vetting is async, non-fatal
            log.error("vetting_enqueue_failed va=%s: %s", va_id, exc)

    return [_va_row_response(p) for p in known_rows]


@app.post("/api/vas/{va_id}/payout/onboarding")
async def va_payout_onboarding(
    va_id: str,
    session: Any = Depends(db_session),
):
    """Create the VA's Stripe Connect Express account + onboarding link."""
    repo = VAProfileRepository(session)
    profile = await repo.get_by_id(va_id)
    if profile is None:
        raise HTTPException(404, "VA not found")
    payments: PaymentService = app.state.payments
    connect = payments.create_va_connect_account(email=profile.email, metadata={"va_id": va_id})
    account_id = connect.get("account_id")
    if not account_id:
        raise HTTPException(502, f"Connect account creation failed: {connect}")
    profile.payout_account_id = account_id
    await repo.update(profile)
    await session.commit()
    link = payments.create_va_account_link(account_id)
    return {"va_id": va_id, "account_id": account_id, "onboarding_url": link.get("url")}


# ==================== MATCHING ====================


@app.post("/api/matches", response_model=list[MatchResponse])
async def match_client(request: MatchRequest, session: Any = Depends(db_session)):
    """Find matches for a client (canonical matching algorithm)."""
    from marketplace.matching import DefaultMatchingAlgorithm

    client = await ClientProfileRepository(session).get_by_id(request.client_id)
    if client is None:
        raise HTTPException(404, "Client not found")

    pool = await VAProfileRepository(session).list_active()
    client_ns = SimpleNamespace(
        id=str(client.id),
        required_skills=list(client.required_skills or []),
        max_hourly_rate=float(client.max_hourly_rate or 0),
        needed_hours_per_week=client.needed_hours_per_week,
        timezone=client.timezone or "UTC",
    )
    matches = await DefaultMatchingAlgorithm().find_matches(
        client_ns,
        [_orm_to_base(p) for p in pool],
        limit=request.limit,
    )

    match_repo = MatchRepository(session)
    saved: list[Match] = []
    for m in matches:
        if float(m.match_score) < request.min_score:
            continue
        row = Match(
            client_id=client.id,
            va_id=m.va_id,
            status=MatchStatus.PROPOSED,
            match_score=Decimal(str(m.match_score)),
            match_factors=dict(m.match_factors or {}),
        )
        session.add(row)
        saved.append(row)
    await session.commit()

    notifications: NotificationService = app.state.notifications
    for row in saved:
        try:
            await notifications.notify_user(
                session,
                user_id=str(client.user_id),
                email=client.email,
                kind="match_proposed",
                payload={"match_id": str(row.id), "score": float(row.match_score)},
            )
        except Exception as exc:  # noqa: BLE001 — notifications best effort
            log.warning("notify_failed: %s", exc)
    await session.commit()

    return [
        MatchResponse(
            match_id=str(row.id),
            client_id=str(row.client_id),
            va_id=str(row.va_id),
            match_score=float(row.match_score),
            match_factors=dict(row.match_factors or {}),
            status=str(row.status.value),
        )
        for row in saved
    ]


@app.get("/api/matches/client/{client_id}", response_model=list[MatchResponse])
async def client_matches(client_id: str, session: Any = Depends(db_session)):
    """List a client's matches."""
    rows = await MatchRepository(session).get_by_client(client_id)
    return [
        MatchResponse(
            match_id=str(m.id),
            client_id=str(m.client_id),
            va_id=str(m.va_id),
            match_score=float(m.match_score),
            match_factors=dict(m.match_factors or {}),
            status=str(m.status.value),
        )
        for m in rows
    ]


@app.post("/api/matches/{match_id}/accept")
async def accept_match(
    match_id: str,
    user: dict = Depends(get_current_user_with_role),
    session: Any = Depends(db_session),
):
    """Client accepts a proposed match."""
    match = await MatchRepository(session).get_by_id(match_id)
    if match is None:
        raise HTTPException(404, "Match not found")
    if match.status not in (MatchStatus.PROPOSED, MatchStatus.INTRO_SENT):
        raise HTTPException(409, f"Match is {match.status.value}, not actionable")
    match.status = MatchStatus.ACCEPTED
    match.accepted_at = datetime.now(UTC)
    await session.commit()
    return {"message": "Match accepted", "match_id": match_id}


@app.post("/api/matches/{match_id}/reject")
async def reject_match(
    match_id: str,
    reason: str = Form(...),
    user: dict = Depends(get_current_user_with_role),
    session: Any = Depends(db_session),
):
    """Client rejects a proposed match."""
    match = await MatchRepository(session).get_by_id(match_id)
    if match is None:
        raise HTTPException(404, "Match not found")
    match.status = MatchStatus.REJECTED
    match.rejected_at = datetime.now(UTC)
    match.rejection_reason = reason
    await session.commit()
    return {"message": "Match rejected", "match_id": match_id}


# ==================== BILLING (canonical provider + ledger) ====================


@app.post("/api/billing/placement-fee")
async def charge_placement_fee(match_id: str, session: Any = Depends(db_session)):
    """Charge the placement fee for an accepted match."""
    match = await MatchRepository(session).get_by_id(match_id)
    if match is None:
        raise HTTPException(404, "Match not found")
    if match.placement_fee_charged:
        raise HTTPException(409, "Placement fee already charged for this match")

    client = match.client
    payments: PaymentService = app.state.payments
    result = await payments.charge_placement_fee(
        placement_fee=Decimal(str(match.match_score)) * Decimal("0"),  # replaced below
        client_id=str(match.client_id),
        match_id=match_id,
        customer_email=client.email if client else None,
        va_id=str(match.va_id) if match.va_id else None,
    )
    del result
    raise HTTPException(501, "controlled by dedicated fee builder (see below)")


@app.post("/api/billing/placement-fee/charge")
async def charge_placement_fee_v2(payload: dict[str, Any], session: Any = Depends(db_session)):
    """Charge a placement fee with an explicit amount."""
    match_id = str(payload.get("match_id", ""))
    amount = Decimal(str(payload.get("amount", 0)))
    if not match_id:
        raise HTTPException(422, "match_id is required")
    match = await MatchRepository(session).get_by_id(match_id)
    if match is None:
        raise HTTPException(404, "Match not found")
    if match.placement_fee_charged:
        raise HTTPException(409, "Placement fee already charged for this match")

    client = match.client
    payments: PaymentService = app.state.payments
    result = await payments.charge_placement_fee(
        placement_fee=amount,
        client_id=str(match.client.user_id) if match.client else str(match.client_id),
        match_id=match_id,
        customer_email=client.email if client else None,
        va_id=str(match.va_id) if match.va_id else None,
    )
    session.add(
        PaymentIntent(
            stripe_payment_intent_id=result.payment_id,
            amount=result.amount,
            currency="usd",
            status=PaymentStatus(result.status),
            payment_type=PaymentType.PLACEMENT_FEE,
            client_id=match.client.user_id if match.client else match.client_id,
            match_id=match.id,
            va_id=match.va_id,
            description="VA placement fee",
            metadata={"sale_intent_id": result.sale_intent_id},
        )
    )
    match.placement_fee_charged = True
    await session.commit()
    return {
        "payment_id": result.payment_id,
        "sale_intent_id": result.sale_intent_id,
        "checkout_token": result.checkout_token,
        "amount": float(result.amount),
        "status": result.status,
        "duplicate": result.duplicate,
    }


@app.post("/api/billing/monthly-fee")
async def charge_monthly_fee(
    payload: MonthlyFeeRequest, session: Any = Depends(db_session)
):
    """Bill the monthly platform fee for a match (period-keyed, idempotent)."""
    payments: PaymentService = app.state.payments
    match = await MatchRepository(session).get_by_id(payload.match_id)
    if match is None:
        raise HTTPException(404, "Match not found")

    result = await payments.charge_monthly_platform_fee(
        client_id=str(match.client.user_id) if match.client else str(match.client_id),
        match_id=payload.match_id,
        period=payload.period,
        customer_email=match.client.email if match.client else None,
        va_id=str(match.va_id) if match.va_id else None,
    )
    payment = PaymentIntent(
        stripe_payment_intent_id=result.payment_id,
        amount=result.amount,
        currency="usd",
        status=PaymentStatus(result.status),
        payment_type=PaymentType.MONTHLY_SUBSCRIPTION,
        client_id=match.client.user_id if match.client else match.client_id,
        match_id=match.id,
        va_id=match.va_id,
        description="Monthly platform fee",
        metadata={"sale_intent_id": result.sale_intent_id, "period": payload.period},
    )
    session.add(payment)

    subscription = await SubscriptionRepository(session).get_active_by_match(
        payload.match_id
    )
    if subscription is None:
        now = datetime.now(UTC)
        subscription = Subscription(
            client_id=match.client.user_id if match.client else match.client_id,
            match_id=match.id,
            va_id=match.va_id,
            amount=result.amount,
            currency="usd",
            interval="month",
            status=PaymentStatus.PENDING,
            current_period_start=now,
        )
        session.add(subscription)
        payment.subscription = subscription

    match.platform_fee_charged = True
    await session.commit()
    return {
        "payment_id": result.payment_id,
        "sale_intent_id": result.sale_intent_id,
        "amount": float(result.amount),
        "status": result.status,
        "duplicate": result.duplicate,
    }


@app.post("/api/billing/refund")
async def request_refund(payload: RefundRequest, session: Any = Depends(db_session)):
    """Idempotent, capped refund through the canonical rails."""
    payments: PaymentService = app.state.payments
    outcome = await payments.refund_payment(
        sale_intent_id=payload.sale_intent_id,
        payment_id=payload.payment_id,
        amount=Decimal(str(payload.amount)) if payload.amount else None,
        reason=payload.reason,
    )
    row = await PaymentRepository(session).get_by_stripe_id(payload.payment_id)
    if row is not None:
        row.status = PaymentStatus.REFUNDED
        await session.commit()
    return outcome


# ==================== ONBOARDING / DELIVERIES ====================


@app.post("/api/onboarding/start")
async def start_onboarding(match_id: str, session: Any = Depends(db_session)):
    """Generate the canonical onboarding plan and persist it."""
    match = await MatchRepository(session).get_by_id(match_id)
    if match is None:
        raise HTTPException(404, "Match not found")

    plan = OnboardingManager().create_plan(
        match_id=match_id,
        client_id=str(match.client_id),
        va_id=str(match.va_id),
    )
    match.status = MatchStatus.ONBOARDING
    match.onboarding_started_at = datetime.now(UTC)
    session.add(
        OnboardingPlan(
            match_id=match.id,
            client_id=match.client_id,
            va_id=match.va_id,
            stage=plan.get("stage", "started"),
            tasks=list(plan.get("tasks", []) or []),
        )
    )
    await session.commit()
    return plan


@app.get("/api/onboarding/progress/{match_id}")
async def onboarding_progress(match_id: str, session: Any = Depends(db_session)):
    """Onboarding progress for a match (from persisted plan)."""
    row = (
        await session.execute(select(OnboardingPlan).where(OnboardingPlan.match_id == match_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Onboarding plan not found")
    return {
        "match_id": match_id,
        "stage": row.stage,
        "tasks": row.tasks,
        "current_task_index": row.current_task_index,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


@app.post("/api/deliveries")
async def create_delivery(
    payload: DeliveryCreate, session: Any = Depends(db_session)
):
    """Create a new delivery row."""
    row = Delivery(
        match_id=payload.match_id,
        task_id=payload.task_id,
        va_id=payload.va_id,
        client_id=payload.client_id,
        title=payload.title,
        description=payload.description,
        status="pending",
    )
    session.add(row)
    await session.commit()
    return {"delivery_id": str(row.id), "status": row.status}


@app.post("/api/deliveries/submit")
async def submit_delivery(payload: DeliverySubmit, session: Any = Depends(db_session)):
    """Record a VA delivery submission."""
    repo = DeliveryRepository(session)
    row = await repo.get_by_id(payload.delivery_id)
    if row is None:
        raise HTTPException(404, "Delivery not found")
    if row.status == "delivered":
        raise HTTPException(409, "Delivery already submitted")
    row.status = "delivered"
    row.deliverables = payload.deliverables
    row.hours_logged = Decimal(str(payload.hours_logged))
    row.submitted_at = datetime.now(UTC)
    await session.commit()
    return {"delivery_id": str(row.id), "status": row.status}


@app.post("/api/deliveries/review")
async def review_delivery(payload: DeliveryReview, session: Any = Depends(db_session)):
    """Record a client delivery review."""
    repo = DeliveryRepository(session)
    row = await repo.get_by_id(payload.delivery_id)
    if row is None:
        raise HTTPException(404, "Delivery not found")
    row.status = payload.status
    row.feedback = payload.feedback
    row.reviewed_at = datetime.now(UTC)
    await session.commit()
    return {"delivery_id": str(row.id), "status": row.status}


@app.get("/api/deliveries/{match_id}")
async def get_deliveries(match_id: str, session: Any = Depends(db_session)):
    """Get all deliveries for a match."""
    rows = await DeliveryRepository(session).get_by_match(match_id)
    return [
        {
            "delivery_id": str(d.id),
            "task_id": d.task_id,
            "va_id": str(d.va_id),
            "title": d.title,
            "status": d.status,
            "hours_logged": float(d.hours_logged or 0),
        }
        for d in rows
    ]


# ==================== NOTIFICATIONS ====================


@app.get("/api/notifications", response_model=list[NotificationOut])
async def my_notifications(
    user: dict = Depends(get_current_user_with_role),
    session: Any = Depends(db_session),
):
    """Unread in-app notifications for the current user."""
    rows = await NotificationRepository(session).get_unread(user["user_id"])
    return [
        NotificationOut(
            id=str(n.id),
            type=n.type,
            title=n.title,
            message=n.message,
            read=n.read,
            created_at=n.created_at.isoformat(),
        )
        for n in rows
    ]


@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: dict = Depends(get_current_user_with_role),
    session: Any = Depends(db_session),
):
    """Mark a notification read."""
    ok = await NotificationRepository(session).mark_read(notification_id, user["user_id"])
    await session.commit()
    return {"success": ok}


# ==================== REPORTS (canonical SalesLedger) ====================


@app.get("/api/reports/ledger")
async def get_ledger_report():
    """Ledger summary + accounting rows from the canonical SalesLedger."""
    ledger = get_market_ledger()
    return {"summary": ledger.summary(), "rows": ledger.accounting_rows(limit=100)}


@app.get("/api/reports/payments")
async def get_payment_stats(session: Any = Depends(db_session)):
    """Payment counts by status (domain table)."""
    total = int(
        (await session.execute(select(func.count()).select_from(PaymentIntent))).scalar()
        or 0
    )
    per_status: dict[str, int] = {}
    for status_value in PaymentStatus:
        count = (
            await session.execute(
                select(func.count())
                .select_from(PaymentIntent)
                .where(PaymentIntent.status == status_value)
            )
        ).scalar() or 0
        per_status[status_value.value] = int(count)
    return {"total": total, "by_status": per_status}


# ==================== STRIPE WEBHOOK (canonical gate) ====================


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Stripe webhook: canonical verify + replay gate, then domain dispatch."""
    payments: PaymentService = app.state.payments
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = await payments.admit_webhook(payload, sig_header)
    except PermissionError as exc:
        raise HTTPException(400, str(exc))

    await _dispatch_webhook(event)
    return {"received": True, "duplicate": event.get("duplicate", False)}


async def _dispatch_webhook(event: dict[str, Any]) -> None:
    """Update domain PaymentIntent rows on Stripe events."""
    event_type = str(event.get("type", ""))
    data = event.get("data", {}).get("object", {})
    payment_id = data.get("id")
    if not payment_id:
        return

    succeeded = event_type in (
        "payment_intent.succeeded",
        "charge.succeeded",
        "invoice.paid",
        "checkout.session.completed",
    )
    refunded = event_type in ("charge.refunded", "refund.created")
    if not (succeeded or refunded):
        return

    async with get_session() as session:
        row = await PaymentRepository(session).get_by_stripe_id(payment_id)
        if row is None:
            return
        if succeeded:
            row.status = PaymentStatus.SUCCEEDED
            row.succeeded_at = datetime.now(UTC)
        else:
            row.status = PaymentStatus.REFUNDED
        sale_intent_id = str((row.metadata or {}).get("sale_intent_id") or "")
        if succeeded and sale_intent_id:
            payments: PaymentService = app.state.payments
            payments.confirm_sale(
                sale_intent_id,
                source="stripe_event",
                evidence=str(event.get("id", "")),
                amount=None,
                status_hint="settled",
            )
        await session.commit()


# ==================== ADMIN ====================


@app.get("/admin/stats")
async def admin_stats(
    user: dict = Depends(require_role(UserRole.ADMIN)),
    session: Any = Depends(db_session),
):
    """Admin statistics (role-gated)."""
    clients = int(
        (
            await session.execute(select(func.count()).select_from(ClientProfile))
        ).scalar()
        or 0
    )
    active_matches = len(await MatchRepository(session).list_active_with_client())
    ledger = get_market_ledger()
    return {
        "clients": clients,
        "active_matches": active_matches,
        "ledger_summary": ledger.summary(),
        "blocked_amounts": ledger.blocked_amounts(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
