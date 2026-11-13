#!/usr/bin/env bash
# Nightly backup for the retention platform: Postgres dump + runtime data.
# The deploy script installs this into cron (03:23) and keeps it refreshed.
set -euo pipefail

REPO_DIR="/opt/sites/retention-analytics-platform"
BACKUP_DIR="${BACKUP_DIR:-/opt/backups/retention}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"

cd "$REPO_DIR"
if [ -f .env ]; then
  set -a; . ./.env; set +a
fi

# Postgres dump (no password on the command line - PGPASSFILE/env only).
if [ -n "${POSTGRES_PASSWORD:-}" ]; then
  export PGPASSWORD="$POSTGRES_PASSWORD"
  if docker compose -f deploy/vps/docker-compose.yml --env-file .env exec -T postgres \
       pg_dump -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-retention_analytics}" \
       > "$BACKUP_DIR/db-$STAMP.sql" 2>"$BACKUP_DIR/db-$STAMP.err"; then
    gzip -f "$BACKUP_DIR/db-$STAMP.sql"
    echo "db backup ok: db-$STAMP.sql.gz"
  else
    echo "WARN: db backup failed" >&2
    cat "$BACKUP_DIR/db-$STAMP.err" >&2 || true
  fi
fi

# Runtime data (customer profiles, workflows, reports, audit exports).
if [ -d data ]; then
  tar -czf "$BACKUP_DIR/data-$STAMP.tar.gz" data
  echo "data backup ok: data-$STAMP.tar.gz"
fi

# Retention: keep N days.
find "$BACKUP_DIR" -type f -mtime "+$KEEP_DAYS" -delete 2>/dev/null || true
echo "backup complete (keep ${KEEP_DAYS}d)"
