#!/usr/bin/env bash
# Uptime probe for the retention platform. Cron every 5 minutes; pages the
# shared alert channel on repeated failure.
set -uo pipefail

URL="${UPTIME_URL:-https://retention.snapford.com/health/ready}"
STATE_FILE="${UPTIME_STATE:-/var/lib/retention-uptime.state}"
THRESHOLD="${UPTIME_THRESHOLD:-3}"
ALERT="/opt/sites/alert.sh"

mkdir -p "$(dirname "$STATE_FILE")"

code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "$URL" 2>/dev/null || true)"
count=0
[ -f "$STATE_FILE" ] && count="$(cat "$STATE_FILE" 2>/dev/null || echo 0)"

if [ "$code" = "200" ]; then
  echo "0" > "$STATE_FILE"
  exit 0
fi

count=$((count + 1))
echo "$count" > "$STATE_FILE"
echo "uptime probe failed: $URL -> HTTP ${code:-000} (${count}/${THRESHOLD})" >&2

if [ "$count" -ge "$THRESHOLD" ] && [ -x "$ALERT" ]; then
  "$ALERT" "Retention platform down: $URL -> HTTP ${code:-000} (${count} consecutive failures)" || true
fi
exit 0
