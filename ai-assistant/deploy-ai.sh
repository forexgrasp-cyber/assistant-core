#!/usr/bin/env bash
# =============================================================================
# Deploy AI Assistant to ai.snapford.com (Traefik-native) with health gate
# and auto-rollback.
#
# Usage (VPS, via the estate watcher):
#   cd /opt/sites/ai-assistant && bash ai-assistant/deploy-ai.sh
# or standalone:  bash deploy-ai.sh   (from anywhere)
#
# The estate edge (infra-edge Traefik) owns TLS for *.snapford.com, so this
# script ships no proxy: the app joins the external `web` network, is routed
# by Docker labels and publishes only a loopback port (127.0.0.1:8000) for
# the health gate. The runtime files are synced to /opt/ai-assistant.
# =============================================================================
set -euo pipefail

# The estate watcher checks this repo out as a monorepo (assistant-core) and
# runs ai-assistant/deploy-ai.sh - resolve the site root from the script
# location so the deploy works regardless of the checkout layout.
SITE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="${AI_ASSISTANT_RUNTIME_DIR:-/opt/ai-assistant}"
COMPOSE_FILE="docker-compose.ai.yml"
IMAGE="aiassistant-ai-assistant:latest"
HEALTH_TIMEOUT=180

# The shared canonical library is a private wheel, vendored in the shared
# checkout that the watcher keeps up to date; stage it into the build context.
SHARED_DIR="${DEPLOY_SHARED_DIR:-/opt/sites/shared-canonical-services}"
WHEELS_DIR="$SITE_DIR/wheels"

# The public domain is served by the estate edge (Traefik). The loopback
# probe checks the container itself; the public probes check the whole chain
# (edge, certificate, routing).
DOMAIN="${AI_ASSISTANT_DOMAIN:-ai.snapford.com}"
HEALTH_URLS=(
  "http://127.0.0.1:8000/health"
  "https://${DOMAIN}/health"
  "https://${DOMAIN}/"
)

all_healthy() {
  local url
  for url in "${HEALTH_URLS[@]}"; do
    curl -fsS -o /dev/null --max-time 8 "$url" || return 1
  done
}

# -----------------------------------------------------------------------------
# Pre-flight: secrets must exist in the site dir (untracked files)
# -----------------------------------------------------------------------------
for f in "$SITE_DIR/.env" "$SITE_DIR/.postgres_password"; do
  if [ ! -f "$f" ]; then
    echo "FATAL: no $f - refusing to deploy" >&2
    exit 1
  fi
done
if ! grep -q '^AI_DB_PASSWORD=' "$SITE_DIR/.env"; then
  echo "FATAL: no AI_DB_PASSWORD in $SITE_DIR/.env - refusing to deploy" >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# Stage the private shared wheel into the build context
# -----------------------------------------------------------------------------
stage_shared_wheel() {
  if [ ! -d "$SHARED_DIR/wheels" ]; then
    echo "FATAL: no shared checkout at $SHARED_DIR - cannot stage the shared wheel" >&2
    exit 1
  fi
  local wheel
  wheel="$(ls -1t "$SHARED_DIR"/wheels/shared_canonical_services-*.whl 2>/dev/null | head -1 || true)"
  if [ -z "$wheel" ]; then
    echo "FATAL: no shared_canonical_services wheel in $SHARED_DIR/wheels" >&2
    exit 1
  fi
  mkdir -p "$WHEELS_DIR"
  rm -f "$WHEELS_DIR"/shared_canonical_services-*.whl
  cp "$wheel" "$WHEELS_DIR/"
  echo "==> Staged shared wheel: $(basename "$wheel")"
}

stage_shared_wheel

# -----------------------------------------------------------------------------
# Sync the deploy files to the runtime dir (/opt/ai-assistant)
# -----------------------------------------------------------------------------
echo "==> Syncing deploy files to $RUNTIME_DIR"
mkdir -p "$RUNTIME_DIR"
rsync -a --delete \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'node_modules' \
  --exclude '.venv' \
  --exclude 'dist' \
  --exclude 'data' \
  --exclude 'logs' \
  --exclude 'deploy' \
  --exclude '.pytest_cache' \
  "$SITE_DIR/" "$RUNTIME_DIR/"

cd "$RUNTIME_DIR"

if [ ! -f "$COMPOSE_FILE" ]; then
  echo "FATAL: no $COMPOSE_FILE in $RUNTIME_DIR" >&2
  exit 1
fi

echo "==> Deploying ai-assistant (site commit: $(git -C "$SITE_DIR/.." rev-parse --short HEAD 2>/dev/null || echo 'no git'))"

# Snapshot current image for rollback
PREV="${IMAGE%:*}:prev"
if docker image inspect "$IMAGE" >/dev/null 2>&1; then
  docker tag "$IMAGE" "$PREV"
fi

echo "==> Build"
docker compose -f "$COMPOSE_FILE" build

echo "==> Start"
docker compose -f "$COMPOSE_FILE" up -d

echo "==> Health gate: ${HEALTH_URLS[*]} (timeout ${HEALTH_TIMEOUT}s)"
deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
until all_healthy; do
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "!! health check failed - rolling back to previous image" >&2
    if docker image inspect "$PREV" >/dev/null 2>&1; then
      docker tag "$PREV" "$IMAGE"
      docker compose -f "$COMPOSE_FILE" up -d --no-build
      echo "rollback complete" >&2
      if all_healthy; then
        echo "rollback verified: health gate OK" >&2
      else
        echo "WARN: rollback finished but health gate still fails - manual intervention required" >&2
      fi
    else
      echo "no previous image to roll back to" >&2
    fi
    docker compose -f "$COMPOSE_FILE" ps >&2 || true
    docker compose -f "$COMPOSE_FILE" logs --tail=80 >&2 || true
    exit 1
  fi
  sleep 3
done

echo "==> Deploy OK"
docker compose -f "$COMPOSE_FILE" ps

# Prune dangling images/build cache older than 24h
echo "==> Prune (dangling images + build cache, older than 24h)"
docker image prune -f --filter "until=24h" >/dev/null || true
docker builder prune -f --filter "until=24h" >/dev/null || true
