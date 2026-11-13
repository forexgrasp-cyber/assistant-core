# Deploying retention.snapford.com — exact steps

The platform is ready to ship: image builds, stack runs, tests pass, load test clean.
What remains is DNS + the box (the VPS watcher does the rest).

---

## 1. DNS — add ONE record

The estate sits behind one VPS (`201.18.210.61`) with Traefik terminating TLS.
Add a single **A record** for the subdomain:

| Type | Name | Value | TTL | Proxy |
|------|------|-------|-----|-------|
| `A` | `retention` | `201.18.210.61` | `auto` (or `300`) | **DNS only** (grey cloud) if Cloudflare — see note |

- **Cloudflare:** Dashboard → `snapford.com` → **DNS** → **Add record** → Type `A`, Name `retention`, IPv4 `201.18.210.61`, Proxy status **DNS only**, Save.
  *Why DNS only:* Cloudflare's proxy only supports certain ports/sets and would break the ACME
  DNS challenge that Traefik uses to issue the certificate. The other Snapford subdomains
  (`flowedge`, `studio`, `timefold`) are routed the same way.
- **If DNS is already on Cloudflare**, you can also add it as a CNAME to an existing
  proxied host only if that host is DNS-only too — an A record is simplest.

Verify from your machine (wait for propagation, 1–60 min):

```bash
nslookup retention.snapford.com
# or
dig +short retention.snapford.com      # -> 201.18.210.61
```

When it resolves, the certificate is issued automatically by Traefik (ACME DNS challenge).

---

## 2. The box — clone + env + deploy

SSH to the estate (`ssh vps` uses `~/.ssh/box_deployer`):

```bash
ssh vps
```

### 2.1 Clone the project (the watcher expects it at the path in the estate map)

```bash
mkdir -p /opt/sites
cd /opt/sites
git clone https://github.com/forexgrasp-cyber/retention-analytics-platform.git
cd retention-analytics-platform
git checkout main
```

The shared checkout already exists at `/opt/sites/shared-canonical-services`
(the watcher pulls it on every deploy).

### 2.2 Create the `.env` (secrets — never commit this file)

```bash
cat > /opt/sites/retention-analytics-platform/.env <<'ENV'
ENVIRONMENT=production
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<strong-random>
POSTGRES_DB=retention_analytics
REDIS_PASSWORD=<strong-random>
JWT_SECRET=<openssl rand -base64 48>
WEBHOOK_SECRET=<openssl rand -base64 32>
PII_ENCRYPTION_KEY=<python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())">
PUBLIC_API_URL=https://retention.snapford.com/api/v1
# optional — only providers with a key are offered as payment options
STRIPE_SECRET_KEY=sk_live_...
ENV
chmod 600 /opt/sites/retention-analytics-platform/.env
```

### 2.3 Deploy (the watcher runs this for you every 15 min)

```bash
ssh vps 'bash /opt/sites/scripts/deploy_watcher.sh'
```

Or deploy only this site:

```bash
ssh vps 'bash /opt/sites/retention-analytics-platform/deploy/vps/deploy.sh'
```

The script: pulls the site + shared checkouts (locked), builds the image, applies the
stack, waits for `https://retention.snapford.com/health/ready` (120 s), gates the
contract surfaces (`/robots.txt`, `/sitemap.xml`, `/api/seo/manifest`,
`/api/seo/style/tokens.css`, `/api/i18n/languages`, `/api/me`), and rolls back to the
previous image if anything fails.

### 2.4 The estate entry (already registered — verify)

```bash
python -m shared.deployment.site_inventory --list | grep -A6 retention
```

It should show `domain=retention.snapford.com`, health `https://retention.snapford.com/health/ready`,
and the six contract surfaces.

---

## 3. Verify after deploy

```bash
curl -fsS https://retention.snapford.com/health/ready | jq .
curl -fsS https://retention.snapford.com/api/me | jq .
curl -fsS https://retention.snapford.com/api/i18n/languages | jq '.count'      # 20
curl -fsS https://retention.snapford.com/api/seo/manifest | jq '.name'
python -m shared.webui.design_conformance https://retention.snapford.com
```

Then the local suites against the live deployment (mint a token first):

```bash
python scripts/mint_token.py            # HS256 token, tenant-scoped
$env:API_TOKEN = "<token>"
$env:API_URL   = "https://retention.snapford.com"
python scripts/validate_stack.py
python scripts/verify_platform.py
python scripts/verify_hiro_gaps.py
```

---

## 4. What is already done vs. what you do

| | Status |
|---|---|
| DNS record | **you add it** (1 A record, see §1) |
| Box clone + `.env` + watcher deploy | **you run it** (see §2) |
| Container image builds & runs | ✅ verified under podman (Postgres + Redis + API + worker) |
| Contract surfaces (manifest/tokens/i18n/me) | ✅ 6/6 verified |
| Tests | ✅ 223 unit + 62 e2e + 34 stack + 51 platform + 22 parity |
| Load test | ✅ 9.4k requests, 0 failures, p50 5 ms / p95 46 ms / p99 110 ms @ 100 users |
| Estate registration | ✅ `site_inventory.py` + `product_registry.py` |
| TLS | ✅ automatic (Traefik ACME DNS challenge) once DNS resolves |
