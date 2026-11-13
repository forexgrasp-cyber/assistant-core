#!/usr/bin/env bash
# Deploy the retention analytics platform to the VPS with a health gate and
# auto-rollback. Runs on the server from the VPS watcher
# (shared/deployment/deploy_watcher.sh), which owns the checkout.
#
# Contract with the watcher:
#   - exit 0 = deployed and healthy
#   - non-zero = failed; the watcher pages the alert channel
#   - the watcher records the commit only after exit 0
set -euo pipefail

REPO_DIR="/opt/sites/retention-analytics-platform"
IMAGE="retention-analytics-platform:latest"
HEALTH_URL="https://retention.snapford.com/health/ready"
HEALTH_TIMEOUT=120
HEALTH_INTERVAL=2

if [ ! -f "$REPO_DIR/deploy/vps/docker-compose.yml" ]; then
  echo "FATAL: no deploy/vps/docker-compose.yml in $REPO_DIR" >&2
  exit 1
fi
cd "$REPO_DIR"

if [ ! -f "$REPO_DIR/.env" ]; then
  echo "FATAL: no .env in $REPO_DIR - refusing to deploy" >&2
  exit 1
fi

# Always ship the committed tree. The VPS checkout is a deploy artifact, not a
# developer checkout: the app writes runtime state into the working tree, so a
# pull can refuse the deploy. reset --hard ships exactly the committed tree
# and keeps the untracked .env.
echo "==> Pulling retention-analytics-platform"
git -C "$REPO_DIR" fetch --quiet --prune origin main
git -C "$REPO_DIR" reset --hard origin/main

# Pull the canonical shared checkout (shared-canonical-services). Locked: every
# site deploy pulls the SAME checkout and site deploys run concurrently.
for SHARED_DIR in "${SHARED_REPO_DIR:-}" /opt/sites/shared-canonical-services /opt/shared-canonical-services; do
  [ -n "$SHARED_DIR" ] || continue
  [ -d "$SHARED_DIR/.git" ] || continue
  echo "==> Pull shared ($SHARED_DIR)"
  SHARED_LOCK="/tmp/$(basename "$SHARED_DIR").deploy.lock"
  exec 9>"$SHARED_LOCK"
  if ! flock -w 180 9; then
    echo "FATAL: could not lock the shared checkout ($SHARED_LOCK)" >&2
    exit 1
  fi
  SHARED_BRANCH="$(git -C "$SHARED_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  case "$SHARED_BRANCH" in
    ""|HEAD) SHARED_BRANCH="main" ;;
  esac
  if ! git -C "$SHARED_DIR" fetch --quiet --prune origin "$SHARED_BRANCH"; then
    flock -u 9; exec 9>&-
    echo "FATAL: shared checkout fetch failed ($SHARED_DIR origin/$SHARED_BRANCH)" >&2
    exit 1
  fi
  if ! git -C "$SHARED_DIR" reset --hard "origin/$SHARED_BRANCH"; then
    flock -u 9; exec 9>&-
    echo "FATAL: shared checkout reset failed ($SHARED_DIR origin/$SHARED_BRANCH)" >&2
    exit 1
  fi
  flock -u 9; exec 9>&-
  break
done

echo "==> Deploying commit: $(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo 'no git')"

COMPOSE_ARGS=(-f deploy/vps/docker-compose.yml --env-file .env)

# Snapshot the current image so a failed deploy can roll back instantly.
BASE="${IMAGE%:*}"
PREV="${BASE}:prev"
if docker image inspect "$IMAGE" >/dev/null 2>&1; then
  docker tag "$IMAGE" "$PREV"
fi

rollback() {
  echo "!! $1 - rolling back to previous image" >&2
  if docker image inspect "$PREV" >/dev/null 2>&1; then
    docker tag "$PREV" "$IMAGE"
    docker compose "${COMPOSE_ARGS[@]}" up -d --no-build
    echo "rollback complete" >&2
    if curl -fsS -o /dev/null --max-time 8 "$HEALTH_URL"; then
      echo "rollback verified: health gate OK" >&2
    else
      echo "WARN: rollback finished but $HEALTH_URL still fails - manual intervention required" >&2
    fi
  else
    echo "no previous image to roll back to" >&2
  fi
}

# -- Build ------------------------------------------------------------------
echo "==> Building images"
if ! docker compose "${COMPOSE_ARGS[@]}" build; then
  rollback "build failed"
  exit 1
fi

# -- Apply ------------------------------------------------------------------
echo "==> Applying stack"
docker compose "${COMPOSE_ARGS[@]}" down --remove-orphans
if ! docker compose "${COMPOSE_ARGS[@]}" up -d; then
  rollback "compose up failed"
  exit 1
fi

# -- Health gate ------------------------------------------------------------
echo "==> Health gate: $HEALTH_URL (timeout ${HEALTH_TIMEOUT}s)"
elapsed=0
healthy=0
while [ "$elapsed" -lt "$HEALTH_TIMEOUT" ]; do
  if curl -fsS -o /dev/null --max-time 8 "$HEALTH_URL"; then
    healthy=1
    break
  fi
  sleep "$HEALTH_INTERVAL"
  elapsed=$((elapsed + HEALTH_INTERVAL))
done
if [ "$healthy" != 1 ]; then
  echo "FATAL: health gate timed out after ${HEALTH_TIMEOUT}s" >&2
  docker compose "${COMPOSE_ARGS[@]}" logs --tail 80 >&2 || true
  rollback "health gate failed"
  exit 1
fi
echo "health OK"

# -- Contract-surface gate --------------------------------------------------
# What crawlers and the conformance auditor fetch at the root. Requires a
# direct 200 (no redirect follow) plus the body markers.
SURFACE_URLS=(
  "https://retention.snapford.com/robots.txt|User-agent"
  "https://retention.snapford.com/sitemap.xml|<loc>"
  "https://retention.snapford.com/api/seo/manifest|"
  "https://retention.snapford.com/api/seo/style/tokens.css|"
  "https://retention.snapford.com/api/i18n/languages|"
  "https://retention.snapford.com/api/me|"
)
for entry in "${SURFACE_URLS[@]}"; do
  [ -n "$entry" ] || continue
  url="${entry%%|*}"
  markers="${entry#*|}"
  if [ "$url" = "$entry" ]; then markers=""; fi
  code=000
  body="$(mktemp)"
  code="$(curl -sS -o "$body" -w '%{http_code}' --max-time 10 "$url" 2>/dev/null || true)"
  [ -n "$code" ] || code=000
  surface_ok=1
  if [ "$code" != "200" ]; then
    surface_ok=0
  elif [ -n "$markers" ]; then
    for m in $markers; do
      if ! grep -qF -- "$m" "$body"; then
        surface_ok=0
        break
      fi
    done
  fi
  rm -f "$body"
  if [ "$surface_ok" != 1 ]; then
    rollback "surface gate failed: $url (HTTP $code)"
    exit 1
  fi
  echo "surface OK: $url"
done

# -- Ops maintenance --------------------------------------------------------
ensure_cron() {
  local marker="$1" line="$2" cleaned
  cleaned="$( (crontab -l 2>/dev/null || true) | awk -v m="# $marker" '$0 == m {getline; next} {print}' )"
  printf '%s\n%s\n%s\n' "$cleaned" "# $marker" "$line" | crontab - || echo "WARN: could not update the crontab" >&2
}
OPS_DIR="$REPO_DIR/deploy/vps"
CRON_SITE="retention"
if [ -f "$OPS_DIR/backup.sh" ]; then
  ensure_cron "$CRON_SITE-backup" "23 3 * * * $OPS_DIR/backup.sh >> /var/log/site-backups.log 2>&1"
fi
if [ -f "$OPS_DIR/uptime.sh" ]; then
  ensure_cron "$CRON_SITE-uptime" "*/5 * * * * $OPS_DIR/uptime.sh >> /var/log/site-uptime.log 2>&1"
fi

echo "==> Deploy complete"
exit 0
