# Deployment — retention.snapford.com

The retention platform deploys into the **shared Snapford VPS estate** like every
other Snapford product. The estate map (`shared-canonical-services/shared/deployment/site_inventory.py`)
is the source of truth; the VPS watcher owns the deploy.

## What is where

| Piece | Location |
|-------|----------|
| Public domain | `retention.snapford.com` |
| Repo | `forexgrasp-cyber/retention-analytics-platform` |
| VPS clone | `/opt/sites/retention-analytics-platform` |
| Deploy script | `deploy/vps/deploy.sh` (health gate + contract-surface gate + rollback) |
| Stack | `deploy/vps/docker-compose.yml` (postgres, redis, api, workers, beat, portal, nginx) |
| Edge | `deploy/vps/nginx.conf`; TLS terminated by the shared Traefik edge |
| Ops | `deploy/vps/backup.sh` (nightly), `deploy/vps/uptime.sh` (every 5 min) |
| Product registry | `shared/branding/product_registry.py` → `id=retention`, `subdomain=retention` |
| Estate entry | `shared/deployment/site_inventory.py` → `domain=retention.snapford.com` |

## Deploy flow (the VPS watcher does it)

```
git push (main)  →  watcher notices the moved remote (every 15 min)
                  →  git fetch/reset --hard origin/main (site + shared checkout, locked)
                  →  docker compose build + up
                  →  health gate:  https://retention.snapford.com/health/ready  (120s)
                  →  contract-surface gate: robots.txt, sitemap.xml,
                        /api/seo/manifest, /api/seo/style/tokens.css,
                        /api/i18n/languages, /api/me  (direct 200 + markers)
                  →  any gate fails: roll back to the :prev image and re-verify
                  →  success: the watcher records the commit
```

A push is **not** a deploy. GitHub Actions in this repo is `workflow_dispatch`
only (manual) — the shared standard forbids consumer workflows from starting
on a push, because the watcher owns deployment.

## Manual deploy (operator)

```bash
ssh vps 'bash /opt/sites/scripts/deploy_watcher.sh'      # whole estate
ssh vps 'bash /opt/sites/retention-analytics-platform/deploy/vps/deploy.sh'  # this site only
```

## First-time setup on the box

1. **DNS**: `retention` → the VPS address (201.18.210.61) — A record.
2. **Traefik**: add a router for `Host(\`retention.snapford.com\`)` → the
   retention compose project (`docker-compose.saas-platform.yml` on the box).
3. **Clone + env**:
   ```bash
   mkdir -p /opt/sites/retention-analytics-platform
   cd /opt/sites/retention-analytics-platform
   git clone https://github.com/forexgrasp-cyber/retention-analytics-platform.git
   git checkout main
   cp .env.example .env   # then fill it:
   ```
   Required `.env` values:
   ```dotenv
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=<strong>
   POSTGRES_DB=retention_analytics
   REDIS_PASSWORD=<strong>
   JWT_SECRET=<openssl rand -base64 48>
   WEBHOOK_SECRET=<openssl rand -base64 32>
   PII_ENCRYPTION_KEY=<Fernet.generate_key()>
   PUBLIC_API_URL=https://retention.snapford.com/api/v1
   ```
   Optional payment keys (only providers with a key are offered in the UI):
   `STRIPE_SECRET_KEY`, `PAYPAL_CLIENT_ID`, `PADDLE_API_KEY`, `ADYEN_API_KEY`, …
4. **Deploy**: `bash deploy/vps/deploy.sh` (or let the watcher pick it up).

## Verifying a deployment

```bash
curl -fsS https://retention.snapford.com/health/ready
curl -fsS https://retention.snapford.com/api/me | jq .
curl -fsS https://retention.snapford.com/api/i18n/languages | jq '.count'   # 20
curl -fsS https://retention.snapford.com/api/seo/manifest | jq '.name'
python -m shared.webui.design_conformance https://retention.snapford.com
```

The conformance auditor (`shared/webui/design_conformance.py`) is the gate:
robots, sitemap, manifest, tokens.css, i18n (≥20 locales), `/api/me`.

## Local production-shaped run

```bash
cd deploy/vps
cp ../../.env.example .env    # fill the secrets
docker compose --env-file .env up -d --build
curl -fsS http://127.0.0.1:47318/health/ready
```

## Rollback

Automatic: any failed gate restores the `:prev` image and re-checks health. If a
rollback also fails health, the deploy script says so loudly and the incident is
for manual intervention.

## Ports

| Service | Port |
|---------|------|
| API | 47319 |
| Customer portal | 47320 |
| Dev console | 47321 |
| MCP server | 47322 |
| Postgres | 47323 |
| Redis | 47324 |
| ClickHouse | 47325 |
| nginx (box-local) | 47318 |
