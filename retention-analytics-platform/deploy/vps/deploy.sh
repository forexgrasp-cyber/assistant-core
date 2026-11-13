#!/usr/bin/env bash
# Deploy Snapford Retention (retention.snapford.com) on the estate VPS.
# Generated pattern per shared/deployment (render.json -> deploy.sh); the box
# runs docker and the watcher (deploy_watcher.sh) invokes this script.
#
# Pipeline: pull -> build (satellite context) -> apply -> health gate ->
# contract-surface gate -> rollback on failure -> prune build cache.
set -euo pipefail

REPO_DIR="/opt/sites/retention-analytics-platform"
CONTEXT="/opt/sites"                       # workspace root: site + shared-canonical-services
IMAGE="retention-analytics-platform:latest"
PREV="retention-analytics-platform:prev"
COMPOSE_FILE="deploy/vps/docker-compose.satellite.yml"
PROJECT="retention"
HEALTH_URL="https://retention.snapford.com/health/ready"
HEALTH_TIMEOUT=180
HEALTH_INTERVAL=3

if [ ! -f "$REPO_DIR/$COMPOSE_FILE" ]; then
  echo "FATAL: no $COMPOSE_FILE in $REPO_DIR" >&2; exit 1
fi
if [ ! -f "$REPO_DIR/.env" ]; then
  echo "FATAL: no .env in $REPO_DIR - refusing to deploy" >&2; exit 1
fi
cd "$REPO_DIR"

echo "==> Pulling retention-analytics-platform"
git fetch --quiet --prune origin main
git reset --hard origin/main

echo "==> Pull shared checkout (locked; the watcher runs sites concurrently)"
SHARED=/opt/sites/shared-canonical-services
if [ -d "$SHARED/.git" ]; then
  exec 9>/tmp/shared.deploy.lock
  flock -w 180 9 || { echo "FATAL: shared lock" >&2; exit 1; }
  git -C "$SHARED" fetch --quiet --prune origin main || true
  git -C "$SHARED" reset --hard origin/main || true
  flock -u 9; exec 9>&-
fi

echo "==> Deploying commit: $(git rev-parse --short HEAD)"
# env-file must be absolute: compose resolves relative paths against the
# compose file's directory, not the CWD.
COMPOSE_ARGS=(-p "$PROJECT" -f "$COMPOSE_FILE" --env-file "$REPO_DIR/.env")

if docker image inspect "$IMAGE" >/dev/null 2>&1; then
  docker tag "$IMAGE" "$PREV"
fi

rollback() {
  echo "!! $1 - rolling back" >&2
  if docker image inspect "$PREV" >/dev/null 2>&1; then
    docker tag "$PREV" "$IMAGE"
    docker compose "${COMPOSE_ARGS[@]}" up -d --no-build
    if curl -fsS -o /dev/null --max-time 8 "$HEALTH_URL"; then
      echo "rollback verified: health OK" >&2
    else
      echo "WARN: rollback applied but $HEALTH_URL still failing - manual intervention" >&2
    fi
  fi
}

echo "==> Build"
if ! docker compose "${COMPOSE_ARGS[@]}" build --build-arg PROJECT=retention-analytics-platform; then
  rollback "build failed"; exit 1
fi

echo "==> Apply"
docker compose "${COMPOSE_ARGS[@]}" down --remove-orphans || true
if ! docker compose "${COMPOSE_ARGS[@]}" up -d; then
  rollback "compose up failed"; exit 1
fi

echo "==> Health gate: $HEALTH_URL (timeout ${HEALTH_TIMEOUT}s)"
elapsed=0; healthy=0
while [ "$elapsed" -lt "$HEALTH_TIMEOUT" ]; do
  if curl -fsS -o /dev/null --max-time 8 "$HEALTH_URL"; then healthy=1; break; fi
  sleep "$HEALTH_INTERVAL"; elapsed=$((elapsed + HEALTH_INTERVAL))
done
if [ "$healthy" != 1 ]; then
  echo "FATAL: health gate timed out" >&2
  docker compose "${COMPOSE_ARGS[@]}" logs --tail 60 api >&2 || true
  rollback "health gate failed"; exit 1
fi
echo "health OK"

echo "==> Contract-surface gate"
for entry in \
  "https://retention.snapford.com/robots.txt|User-agent" \
  "https://retention.snapford.com/sitemap.xml|<loc>" \
  "https://retention.snapford.com/api/seo/manifest|" \
  "https://retention.snapford.com/api/seo/style/tokens.css|" \
  "https://retention.snapford.com/api/i18n/languages|" \
  "https://retention.snapford.com/api/me|"
do
  url="${entry%%|*}"; markers="${entry#*|}"
  code="$(curl -sS -o /tmp/surface.body -w '%{http_code}' --max-time 10 "$url" 2>/dev/null || true)"
  [ -n "$code" ] || code=000
  ok=1
  [ "$code" = "200" ] || ok=0
  if [ -n "$markers" ] && [ "$ok" = 1 ]; then
    for m in $markers; do
      grep -qF -- "$m" /tmp/surface.body || { ok=0; break; }
    done
  fi
  if [ "$ok" != 1 ]; then
    rollback "surface gate failed: $url (HTTP $code)"; exit 1
  fi
  echo "surface OK: $url"
done

echo "==> Prune dangling images + build cache older than 24h"
docker builder prune -f --filter "until=24h" >/dev/null 2>&1 || true
docker image prune -f >/dev/null 2>&1 || true

echo "==> Deploy complete"
exit 0
