#!/bin/sh
# Container entrypoint: prepare writable runtime dirs, then drop privileges to
# the unprivileged app user (the app itself never runs as root).
set -e

DATA_DIR="${DATA_DIR:-/data}"
mkdir -p "$DATA_DIR" /app/logs /app/data /app/out 2>/dev/null || true
chown -R appuser:appuser "$DATA_DIR" /app/logs /app/data /app/out 2>/dev/null || true

if command -v gosu >/dev/null 2>&1; then
  exec gosu appuser "$@"
fi
exec su -s /bin/sh -c 'exec "$@"' appuser "$@"
