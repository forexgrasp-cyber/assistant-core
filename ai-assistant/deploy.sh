#!/bin/bash
# ============================================================================
# LEGACY local-dev deploy script - DO NOT RUN ON THE VPS.
#
# The VPS deploy of ai.snapford.com is Traefik-native and goes through the
# estate watcher:
#
#     cd /opt/sites/ai-assistant && bash ai-assistant/deploy-ai.sh
#
# This script's nginx + certbot stack fought the estate edge
# (infra-edge Traefik) for ports 80/443, so it is kept only for local
# development. See deploy-ai.sh + docker-compose.ai.yml for production.
# ============================================================================

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────
VPS_HOST="${VPS_HOST:-201.18.210.61}"
VPS_USER="${VPS_USER:-root}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/ai-assistant}"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANONICAL_REPO="${CANONICAL_REPO:-$(cd "$PROJECT_ROOT/.." && pwd)/shared-canonical-services}"
WHEEL_DIR="$PROJECT_ROOT/dist"
PACKAGE="$PROJECT_ROOT/deploy/ai-assistant.tar.gz"

DB_USER="ai_assistant"
DB_NAME="ai_assistant"

# ── Colors (ASCII only: Windows shells are cp1252) ────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail()    { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}Deploying AI Assistant to ${VPS_HOST}${NC}"
echo -e "${BLUE}=================================================${NC}"

# ── 1. Pre-flight checks ──────────────────────────────────────────────────
cd "$PROJECT_ROOT"

[ -f "$COMPOSE_FILE" ] || fail "$COMPOSE_FILE not found"
[ -f "Dockerfile" ]    || fail "Dockerfile not found"
[ -f "nginx.conf" ]    || fail "nginx.conf not found"
[ -f "init-db.sh" ]    || fail "init-db.sh not found"

if [ ! -f "$ENV_FILE" ]; then
    warn "$ENV_FILE not found, creating from .env.example"
    cp .env.example "$ENV_FILE"
    fail "Please edit $ENV_FILE with your credentials, then re-run"
fi

# Load env (best effort - values with spaces are not supported)
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

for var in SECRET_KEY POSTGRES_PASSWORD PII_ENCRYPTION_KEY CREDENTIAL_ENCRYPTION_KEY; do
    [ -n "${!var:-}" ] || fail "Required variable $var is not set in $ENV_FILE"
done
success "Environment validated"

# ── 2. Build the private shared wheel ─────────────────────────────────────
if [ ! -d "$CANONICAL_REPO" ]; then
    fail "Canonical repo not found: $CANONICAL_REPO"
fi

info "Building shared-canonical-services wheel from $CANONICAL_REPO"
cd "$CANONICAL_REPO"
python -m pip install --upgrade pip build >/dev/null
python -m build --wheel
cd "$PROJECT_ROOT"

# Guard against the nested-repo pitfall (empty wheel)
WHEEL=$(ls -1t "$CANONICAL_REPO"/dist/shared_canonical_services-*.whl 2>/dev/null | head -n1 || true)
[ -n "$WHEEL" ] || fail "No wheel produced in $CANONICAL_REPO/dist"
WHEEL_SIZE=$(stat -c%s "$WHEEL" 2>/dev/null || echo 0)
[ "$WHEEL_SIZE" -gt 100000 ] || fail "Wheel is only ${WHEEL_SIZE} bytes - nested build pitfall?"
success "Built $(basename "$WHEEL") ($((WHEEL_SIZE / 1024 / 1024)) MB)"

mkdir -p "$WHEEL_DIR"
rm -f "$WHEEL_DIR"/*.whl
cp "$WHEEL" "$WHEEL_DIR/"

# ── 3. Package ────────────────────────────────────────────────────────────
info "Creating deployment package"
mkdir -p deploy
tar -czf "$PACKAGE" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='node_modules' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='app/static' \
    "$COMPOSE_FILE" \
    Dockerfile \
    nginx.conf \
    init-db.sh \
    dist \
    "$ENV_FILE"

success "Package: $PACKAGE"

# ── 4. Upload ─────────────────────────────────────────────────────────────
info "Uploading to ${VPS_USER}@${VPS_HOST}:${DEPLOY_PATH}"
ssh "${VPS_USER}@${VPS_HOST}" "mkdir -p ${DEPLOY_PATH}"
scp "$PACKAGE" "${VPS_USER}@${VPS_HOST}:/root/ai-assistant.tar.gz"

# ── 5. Deploy ─────────────────────────────────────────────────────────────
ssh "${VPS_USER}@${VPS_HOST}" << ENDSSH
set -euo pipefail

DEPLOY_PATH="${DEPLOY_PATH}"
COMPOSE_FILE="${COMPOSE_FILE}"
DB_USER="${DB_USER}"
DB_NAME="${DB_NAME}"

cd "\${DEPLOY_PATH}"

echo "Extracting package..."
tar -xzf /root/ai-assistant.tar.gz
cp .env .env

echo "Starting PostgreSQL and Redis..."
docker compose -f \${COMPOSE_FILE} up -d postgres redis

echo "Waiting for PostgreSQL..."
for i in \$(seq 1 30); do
    if docker compose -f \${COMPOSE_FILE} exec -T postgres pg_isready -U \${DB_USER} -d \${DB_NAME} >/dev/null 2>&1; then
        echo "PostgreSQL ready"
        break
    fi
    echo "  waiting for PostgreSQL... (\$i/30)"
    sleep 2
done

echo "Waiting for Redis..."
for i in \$(seq 1 15); do
    if docker compose -f \${COMPOSE_FILE} exec -T redis redis-cli ping >/dev/null 2>&1; then
        echo "Redis ready"
        break
    fi
    echo "  waiting for Redis... (\$i/15)"
    sleep 2
done

echo "Building ai-assistant image..."
docker compose -f \${COMPOSE_FILE} build ai-assistant

echo "Starting ai-assistant..."
docker compose -f \${COMPOSE_FILE} up -d ai-assistant

echo "Waiting for the app to be healthy..."
for i in \$(seq 1 40); do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        echo "ai-assistant healthy"
        break
    fi
    echo "  waiting for ai-assistant... (\$i/40)"
    sleep 3
done

echo "Starting Nginx..."
docker compose -f \${COMPOSE_FILE} up -d nginx

echo "Requesting TLS certificates..."
docker compose -f \${COMPOSE_FILE} run --rm --entrypoint "" certbot \\
    certonly --webroot -w /var/www/certbot \\
    -d ai.snapford.com -d app.ai.snapford.com -d api.ai.snapford.com \\
    --email admin@snapford.com --agree-tos --no-eff-email \\
    || echo "Certbot will retry on the next run"

docker compose -f \${COMPOSE_FILE} restart nginx

echo ""
echo "Deployment complete."
echo "  Landing:  https://ai.snapford.com"
echo "  Dashboard: https://app.ai.snapford.com"
echo "  API:      https://api.ai.snapford.com"
echo "  Health:   https://ai.snapford.com/health"
ENDSSH

success "AI Assistant deployed to ${VPS_HOST}:${DEPLOY_PATH}"
echo ""
echo "  Landing:  https://ai.snapford.com"
echo "  Dashboard: https://app.ai.snapford.com"
echo "  API:      https://api.ai.snapford.com"
echo "  Health:   https://ai.snapford.com/health"
