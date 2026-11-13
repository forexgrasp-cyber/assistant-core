# Retention Analytics Platform

Retention analytics for subscription businesses: automated campaigns, dunning and
payment recovery, churn prediction, health scores, NPS loops and cohort analytics —
measured before and after, not guessed.

One loop connects everything:

```
Customer records -> Segments -> Campaigns -> Flows -> Services -> Outcomes -> Analytics -> Reports
```

- **Customer records** — your data (plan, MRR, LTV, health, next service due, churn risk).
- **Segments** — live filters over those records (computed fields included: days
  until due, health/LTV/value tier, churn risk, RFM segment).
- **Campaigns** — goal + target segment + flows + schedule + success metrics, run
  against a group and measured before/after.
- **Flows** — reusable automation recipes (event -> steps -> services). 37 built in.
- **Services** — 74 registered services, 270+ callable actions.
- **Analytics & reports** — retention, churn, MRR/ARR/GRR/NRR/LTV, cohorts, RFM,
  NPS, benchmarks, per-campaign attribution.

## Run it

```bash
# API + customer portal + dev console (local)
python -m uvicorn apps.api.main:app --port 47319
cd apps/web-customer && npm run dev     # :47320
cd apps/web-dev && npm run dev         # :47321

# containers
cd infra/docker && podman compose up -d --build
```

## Test it

```bash
python -m pytest -q                              # unit + integration
python scripts/validate_stack.py                 # live endpoint sweep
python scripts/verify_platform.py                # full platform behaviour
python scripts/verify_hiro_gaps.py               # competitor parity
python -m pytest tests/e2e/test_live_e2e.py -m e2e -q   # live e2e
```

Full procedure: [docs/TESTING.md](docs/TESTING.md).

## Deploy

`retention.snapford.com` — DNS + box steps in
[DEPLOYMENT_DNS.md](DEPLOYMENT_DNS.md). The estate watcher runs
`deploy/vps/deploy.sh` (health gate + contract-surface gate + rollback).

## Docs

| Doc | What |
|-----|------|
| [docs/TESTING.md](docs/TESTING.md) | how to test everything locally |
| [docs/COMPETITOR_FEATURE_MATRIX.md](docs/COMPETITOR_FEATURE_MATRIX.md) | feature parity across the retention platform market |
| [docs/HIRO_COMPETITOR_ANALYSIS.md](docs/HIRO_COMPETITOR_ANALYSIS.md) | agency-analytics competitor, feature by feature |
| [docs/UI_COVERAGE_AUDIT.md](docs/UI_COVERAGE_AUDIT.md) | API surface vs customer-portal coverage |
| [docs/SHARED_SERVICES_WIRING.md](docs/SHARED_SERVICES_WIRING.md) | what comes from shared-canonical-services |
| [DEPLOYMENT.md](DEPLOYMENT.md) | deployment model |

## Stack

FastAPI · PostgreSQL · Redis · Celery · Next.js (customer portal + dev console) ·
MCP server · shared-canonical-services (secrets, idempotency, audit, rate limiting,
metrics, payments, feature flags, sessions, notifications, …).
