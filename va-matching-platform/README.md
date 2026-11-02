# VA Matching Platform

Two-sided marketplace for VA matching — "Buy Back Your Time" implementation.

## Status: NOT_READY (Production Readiness Audit)

**Current State:** Core infrastructure complete, payment providers scaffolded, needs real credentials & external configuration.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your credentials

# Run database migrations
alembic upgrade head

# Start development server
uvicorn main:app --reload --port 8000
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI App                              │
├─────────────────────────────────────────────────────────────────┤
│  Auth (JWT)     │  Payments (Multi-provider)   │  Background   │
│  shared.auth    │  UnifiedPaymentService       │  async_jobs   │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL (asyncpg)  │  Redis (optional)  │  Alembic Mig.   │
└─────────────────────────────────────────────────────────────────┘
```

**Core Services (Canonical):**
- `shared.auth.jwt_service` — JWT auth with platform user sync
- `shared.billing.UnifiedPaymentService` — Multi-provider (Stripe, Gumroad, LemonSqueezy, PayPal)
- `shared.billing.StripeConnectService` — VA payout onboarding
- `shared.payments.SalesLedger` — Double-confirmation ledger
- `shared.async_jobs.BackgroundTaskManager` — Vetting, monthly fees, Connect onboarding
- `shared.oauth` — Upwork/Fiverr/Toptal OAuth adapters

---

## Current Status: NOT_READY

### ✅ Complete (Gates Passing)

| Gate | Status |
|------|--------|
| G0 Hygiene | ✅ Clean lint/typecheck/import-smoke |
| G1 Service Coverage | ✅ All canonical services L2-L4 |
| G2 Contract | ✅ Pydantic schemas, no collisions |
| G7 SEO/AEO | ✅ Sitemap, robots, meta tags, JSON-LD |
| G10 Competitive | ✅ Upwork/Fiverr/Toptal + Stripe Connect |
| G11 Testing | ✅ 10/10 tests passing |

### ⚠️ Blockers (P0 — Require Real Credentials)

| Gate | Issue | Action Required |
|------|-------|-----------------|
| **G3 Data & Money** | Live payment keys untested | Add Stripe/Gumroad/LS/PayPal keys; register webhooks |
| **G4 Security** | No app-level rate limiting on auth | Add `RateLimitMiddleware` to auth routes |
| **G5 Performance** | No load testing | Run Locust against staging |
| **G8 Observability** | No readiness probe, metrics, alerts | Add Prometheus + alerting |
| **G9 Deployment** | Alembic not in CI, no rollback drill | Add migrations to CI, automate rollback |

---

## Next Steps (Priority Order)

### Phase 1: Money Hardening (P0) — 2-3 weeks

```bash
# 1. Add real payment credentials to .env
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
GUMROAD_ACCESS_TOKEN=...
GUMROAD_WEBHOOK_SECRET=...
LEMONSQUEEZY_API_KEY=...
LEMONSQUEEZY_WEBHOOK_SECRET=...
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
PAYPAL_WEBHOOK_ID=...

# 2. Register webhook endpoints in provider dashboards
# Stripe:    POST https://your-domain.com/webhooks/stripe
# Gumroad:   POST https://your-domain.com/webhooks/gumroad
# LemonSqueezy: POST https://your-domain.com/webhooks/lemonsqueezy
# PayPal:    POST https://your-domain.com/webhooks/paypal

# 3. Test real payment flow
# - Create placement fee → Stripe Payment Link → Webhook → Ledger confirm
# - Create monthly subscription → Webhook → Ledger confirm
# - Test refund flow end-to-end
```

### Phase 2: Webhook Hardening (P0) — 1 week

- [ ] Test Gumroad webhook: `sale.completed` → ledger confirm
- [ ] Test LemonSqueezy webhook: `order_created` → subscription sync
- [ ] Test PayPal webhook: `PAYMENT.CAPTURE.COMPLETED` → settlement
- [ ] Verify replay/freshness gate rejects replays (WebhookGate)

### Phase 3: OAuth Hardening (P0) — 1-2 weeks

```bash
# Add real OAuth credentials
UPWORK_CLIENT_ID=...
UPWORK_CLIENT_SECRET=...
UPWORK_REDIRECT_URI=https://your-domain.com/oauth/callback/upwork

FIVERR_CLIENT_ID=...
FIVERR_CLIENT_SECRET=...
FIVERR_REDIRECT_URI=https://your-domain.com/oauth/callback/fiverr

TOPTAL_CLIENT_ID=...
TOPTAL_CLIENT_SECRET=...
TOPTAL_REDIRECT_URI=https://your-domain.com/oauth/callback/toptal
```

- [ ] Test PKCE flow end-to-end for each provider
- [ ] Verify token refresh works (TokenRefreshService)
- [ ] Verify token encryption/storage (TokenStore + CREDENTIAL_ENCRYPTION_KEY)

### Phase 3: Observability & Deployment (P1) — 1 week

- [ ] Add readiness probe: `GET /ready` (DB + schema check)
- [ ] Add Prometheus metrics: `/metrics` (requests, latency, DB, business)
- [ ] Add alerting: budget exceeded, webhook failures, auth failures
- [ ] Add correlation IDs to logs (X-Correlation-ID header)
- [ ] Add Alembic to CI pipeline (done)
- [ ] Automate rollback drill script (done)
- [ ] Automate backup/restore scripts (done)

### Phase 4: Load Testing & UX Polish (P2) — 1-2 weeks

```bash
# Run load test against staging
cd load_tests
locust -f locustfile.py --host=https://staging.your-domain.com \
  --headless -u 100 -r 10 --run-time 5m
```

- [ ] Run Locust load test against staging
- [ ] Measure CWV (LCP, FID, CLS) on intake/dashboard
- [ ] Accessibility audit (axe-core)
- [ ] i18n scaffold for future locales

---

## Development Commands

```bash
# Run tests
pytest tests -v --tb=short

# Run linting
ruff check .

# Database operations
alembic upgrade head          # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
alembic downgrade -1          # Rollback one migration

# Database backup/restore
python scripts/backup_db.py --output-dir ./backups
python scripts/restore_db.py ./backups/backup_full_20260101_120000.sql.gz

# Rollback drill
python scripts/rollback_drill.py --steps 2

# Load testing
cd load_tests
locust -f locustfile.py --host=http://localhost:8000

# Docker
docker-compose -f deployment/docker-compose.yml up -d
```

---

## Environment Variables

See `.env.example` for all required variables. Key categories:

| Category | Variables |
|----------|-----------|
| **Database** | `DATABASE_URL`, `AUTH_DATABASE_URL`, `PAYMENT_LEDGER_DB` |
| **Auth** | `SECRET_KEY`, `CREDENTIAL_ENCRYPTION_KEY` |
| **Stripe** | `STRIPE_SECRET_KEY`, `STRIPE_PUBLIC_KEY`, `STRIPE_WEBHOOK_SECRET` |
| **Gumroad** | `GUMROAD_ACCESS_TOKEN`, `GUMROAD_APPLICATION_ID`, `GUMROAD_APPLICATION_SECRET`, `GUMROAD_WEBHOOK_SECRET` |
| **LemonSqueezy** | `LEMONSQUEEZY_API_KEY`, `LEMONSQUEEZY_STORE_ID`, `LEMONSQUEEZY_WEBHOOK_SECRET` |
| **PayPal** | `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`, `PAYPAL_SANDBOX` |
| **OAuth** | `UPWORK_*`, `FIVERR_*`, `TOPTAL_*` (ID, SECRET, REDIRECT_URI) |
| **Email** | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`, `EMAIL_FROM_NAME` |
| **Connect** | `CONNECT_RETURN_URL`, `CONNECT_REFRESH_URL` |

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| **Multi-provider payments** | Avoid vendor lock-in; support creator economy platforms |
| **Canonical services** | Single source of truth for auth, billing, async jobs |
| **Alembic migrations** | Versioned schema evolution, CI/CD integration |
| **WebhookGate (replay protection)** | Prevents duplicate processing, financial safety |
| **SalesLedger (multi-confirmation)** | Webhook + API poll + reconciliation = triple verification |
| **BackgroundTaskManager** | In-process async jobs, no Celery/Redis dependency |

---

## Links

- **Production Readiness Audit:** `docs/PRODUCTION_READINESS_AUDIT.md`
- **API Documentation:** `http://localhost:8000/docs` (when running)
- **Health Check:** `GET /health`
- **Readiness Probe:** `GET /ready`
- **Metrics:** `GET /metrics`

---

## License

Proprietary — VA Matching Platform