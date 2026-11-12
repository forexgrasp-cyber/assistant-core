# How to test everything correctly

## Is Postgres in the image?

**No.** The API image (`infra/docker/Dockerfile.api`) is `python:slim` + the app only — no database inside. Postgres runs as a **separate container** (`postgres:16-alpine`) in `docker-compose.yml` / `docker-compose.prod.yml`, and in production as **RDS** via `infra/terraform`. The API connects over the network using `DATABASE_URL`. Same for Redis (`redis:7-alpine`) and ClickHouse.

## Test layers (run in this order)

### 1. Unit + integration (no infra needed)
```bash
cd retention-analytics-platform
python -m pytest -q                    # 159 tests: services, workflows, campaigns, pain coverage
```
Stores are file-backed / in-memory, so this is fast and hermetic.

### 2. Real Postgres (preferred — the suite runs against it automatically)

If a local Postgres 16 is running, create a test DB once:

```bash
psql -U postgres -c "CREATE DATABASE retention_test;"
psql -U postgres -c "CREATE USER retention WITH PASSWORD 'retention'; GRANT ALL ON DATABASE retention_test TO retention;"
```

Then run the whole suite against it — entity CRUD and persistence tests will use
real Postgres (they fall back to aiosqlite only when DATABASE_URL is unset):

```bash
$env:DATABASE_URL = "postgresql+asyncpg://retention:retention@localhost:5432/retention_test"
python -m pytest -q                       # 164 tests
python scripts/validate_stack.py          # 33 live checks against the API
```

Verify the DB was actually used:
```bash
psql -U postgres -d retention_test -c "SELECT count(*) FROM entity_schemas;"
```

### 2b. Full stack via Docker (real Postgres + Redis + API + workers + frontends)
```bash
cd infra/docker
$env:POSTGRES_PASSWORD="..."; $env:REDIS_PASSWORD="..."; $env:JWT_SECRET="..."; $env:WEBHOOK_SECRET="..."
docker compose -f docker-compose.prod.yml up -d --build
# wait for health
curl http://localhost/health/ready
# then run the whole suite against the live stack:
cd ../..
$env:DATABASE_URL = "postgresql+asyncpg://postgres:$env:POSTGRES_PASSWORD@localhost:47323/retention_analytics"
python -m pytest -q
python scripts/validate_stack.py       # live endpoint sweep (below)
```

### 4. Browser e2e (Playwright) — runs in CI
```bash
playwright install chromium
python -m pytest tests/e2e/test_journeys.py -m e2e -q
```

### 4b. Comprehensive live e2e (against the running API — services, workflows, pipelines, persistence)

`tests/e2e/test_live_e2e.py` (63 tests) runs against the live server and covers:
every service action via the generic proxy, all 37 workflows run to completion,
event→workflow→service→persistence pipeline, file-store + Postgres entity
persistence round-trips, full campaign lifecycle, CSV import/export round-trip,
tenancy isolation, webhook idempotency, security headers, demo, pains, help.

```bash
# start the API with a high rate limit for the e2e burst (limit is unit-tested separately)
$env:DATABASE_URL = "postgresql+asyncpg://retention:retention@localhost:5432/retention_test"
$env:RATE_LIMIT_PER_MINUTE = "100000"
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 47319 &
POST /api/v1/demo/run   # seed data first
$env:API_URL = "http://127.0.0.1:47319"
python -m pytest tests/e2e/test_live_e2e.py -m e2e -q     # 62 passed, 1 skipped
```


### 5. Load test (locust) — smoke in CI, staging profile for real load
```bash
locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 30s --host http://localhost
locust -f tests/load/locustfile_staging.py --headless -u 100 -r 10 -t 5m --host https://staging.example.com
```

### 6. Security scan — runs in CI
```bash
pip-audit; bandit -r packages apps -ll -ii; python scripts/security_scan.py
```

## One-command live validation

`scripts/validate_stack.py` hits every endpoint group against the running API
and prints PASS/FAIL per check. Run it whenever the API is up:

```bash
python scripts/validate_stack.py            # defaults to http://127.0.0.1:47319
API_URL=http://localhost python scripts/validate_stack.py
```

It covers: root/health/metrics, all service groups, campaigns lifecycle,
workflows run, events, reports, customers 360, service-due, pains catalog,
help, demo, compliance, security headers.
