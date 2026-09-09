#!/usr/bin/env bash
# Backend entrypoint — wait for DB/Redis, optionally migrate, exec gunicorn.
#
# Idempotent. Re-runs migrations only when RUN_MIGRATIONS=1, and only
# in non-DEBUG (DEBUG=True skips collectstatic). Exit codes propagate
# to the container so Compose / k8s can restart on failure.
set -euo pipefail

log() { echo "entrypoint: $*"; }

# --- Wait for Postgres -------------------------------------------------
# Uses /dev/tcp rather than pg_isready so we don't need psql in the
# runtime image (the alpine-slim base doesn't ship it).
if [[ -n "${PG_HOST:-}" ]]; then
    log "waiting for postgres at ${PG_HOST}:${PG_PORT:-5432}…"
    for i in {1..60}; do
        if (echo > "/dev/tcp/${PG_HOST}/${PG_PORT:-5432}") 2>/dev/null; then
            log "postgres reachable after ${i}s"
            break
        fi
        [[ $i -eq 60 ]] && { log "postgres unreachable after 60s, exiting"; exit 1; }
        sleep 1
    done
fi

# --- Wait for Redis (only if REDIS_URL is set) --------------------------
if [[ -n "${REDIS_URL:-}" ]]; then
    # Extract host:port from the URL — only needs a TCP probe.
    redis_hostport=$(echo "$REDIS_URL" | sed -E 's#^redis://##; s#/.*$##')
    log "waiting for redis at ${redis_hostport}…"
    for i in {1..30}; do
        if (echo > "/dev/tcp/${redis_hostport/:/ }") 2>/dev/null \
            || (echo > "/dev/tcp/${redis_hostport%:*}/${redis_hostport##*:}") 2>/dev/null; then
            log "redis reachable after ${i}s"
            break
        fi
        [[ $i -eq 30 ]] && { log "redis unreachable after 30s, exiting"; exit 1; }
        sleep 1
    done
fi

# --- Migrations --------------------------------------------------------
if [[ "${RUN_MIGRATIONS:-0}" == "1" ]]; then
    log "running migrations…"
    python manage.py migrate --noinput
fi

# --- collectstatic ----------------------------------------------------
# Skip when DEBUG=True (Django's autoreload-friendly mode). Force via
# RUN_COLLECTSTATIC=0 to skip in prod (e.g. mounted static volume).
if [[ "${DEBUG:-0}" == "True" ]]; then
    log "DEBUG=True; skipping collectstatic"
elif [[ "${RUN_COLLECTSTATIC:-1}" == "1" ]]; then
    log "collectstatic…"
    python manage.py collectstatic --noinput
fi

log "exec $*"
exec "$@"
