#!/usr/bin/env bash
# Deploy tutor-service with health gate + auto-rollback.
# Usage: bash deploy.sh   (run on the server, from anywhere)
set -euo pipefail

# The estate watcher checks this repo out as a monorepo (assistant-core) and
# runs tutor-service/deploy.sh - resolve the site root from the script location
# so the deploy works regardless of the checkout layout.
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="docker-compose.languages.yml"
IMAGE="tutor-service:latest"
HEALTH_TIMEOUT=120

# The shared canonical library is a private wheel. It is vendored in the
# shared checkout that the watcher keeps up to date, and staged into the
# build context before the image is built.
SHARED_DIR="${DEPLOY_SHARED_DIR:-/opt/sites/shared-canonical-services}"
WHEELS_DIR="$REPO_DIR/wheels"

# The public domain is served by the estate edge (Traefik). The loopback
# probe checks the container itself; the public probe checks the whole
# chain (edge, certificate, routing).
DOMAIN="${TUTOR_DOMAIN:-languages.snapford.com}"
HEALTH_URLS=(
  "http://127.0.0.1:8147/health"
  "https://${DOMAIN}/health"
  "https://${DOMAIN}/"
)

all_healthy() {
  local url
  for url in "${HEALTH_URLS[@]}"; do
    curl -fsS -o /dev/null --max-time 8 "$url" || return 1
  done
}

if [ ! -f "$REPO_DIR/$COMPOSE_FILE" ]; then
  echo "FATAL: no $COMPOSE_FILE in $REPO_DIR" >&2
  exit 1
fi
cd "$REPO_DIR"

# Secrets and env must exist
if [ ! -f "$REPO_DIR/.env" ]; then
  echo "FATAL: no .env in $REPO_DIR - refusing to deploy" >&2
  exit 1
fi
if [ ! -f "$REPO_DIR/.postgres_password" ]; then
  echo "FATAL: no .postgres_password in $REPO_DIR - refusing to deploy" >&2
  exit 1
fi
if ! grep -q '^TUTOR_DB_PASSWORD=' "$REPO_DIR/.env"; then
  echo "FATAL: no TUTOR_DB_PASSWORD in $REPO_DIR/.env - refusing to deploy" >&2
  exit 1
fi

echo "==> Deploying commit: $(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo 'no git')"

# -----------------------------------------------------------------------------
# Stage the private shared wheel into the build context
# -----------------------------------------------------------------------------
stage_shared_wheel() {
  if [ ! -d "$SHARED_DIR/wheels" ]; then
    echo "FATAL: no shared checkout at $SHARED_DIR - cannot stage the shared wheel" >&2
    exit 1
  fi

  # The newest wheel wins: the shared checkout may carry more than one
  # version and only the latest matches the checkout the watcher pulled.
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

# Cloudflare cache purge (optional)
CF_TOKEN="$(grep -E '^CLOUDFLARE_API_TOKEN=' "$REPO_DIR/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true)"
CF_ZONE="$(grep -E '^CLOUDFLARE_ZONE_ID=' "$REPO_DIR/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true)"
if [ -n "$CF_TOKEN" ] && [ -n "$CF_ZONE" ]; then
  echo "==> Cloudflare cache purge"
  if curl -fsS -m 15 -X POST -H "Authorization: Bearer $CF_TOKEN" \
    -H "Content-Type: application/json" -d '{"purge_everything":true}' \
    "https://api.cloudflare.com/client/v4/zones/$CF_ZONE/purge_cache" >/dev/null; then
    echo "cache purged"
  else
    echo "WARN: Cloudflare cache purge failed (continuing)" >&2
  fi
else
  echo "==> Cloudflare cache purge skipped (CLOUDFLARE_API_TOKEN/CLOUDFLARE_ZONE_ID not in .env)"
fi

echo "==> Deploy OK (commit: $(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo 'no git'))"
docker compose -f "$COMPOSE_FILE" ps

# Prune dangling images/build cache older than 24h
echo "==> Prune (dangling images + build cache, older than 24h)"
docker image prune -f --filter "until=24h" >/dev/null || true
docker builder prune -f --filter "until=24h" >/dev/null || true
