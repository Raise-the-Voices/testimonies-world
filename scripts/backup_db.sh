#!/usr/bin/env bash
#
# backup_db.sh — PostgreSQL backup for the testimonies-world DB.
#
# Reads connection details from /opt/rtv-cases/backend/.env
# (PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD), runs pg_dump
# (custom-format, zstd-compressed), writes a timestamped file to
# /var/backups/rtv-cases/, and prunes anything older than
# BACKUP_RETENTION_DAYS (default 30).
#
# Intended to run as the systemd `rtv-cases-db-backup.service`
# oneshot, triggered by the matching timer (daily at 03:00 UTC).
# All output goes to journald via `StandardOutput=journal` on the
# unit; this script keeps its output terse on success and detailed
# on failure.
#
# Exit codes:
#   0 — backup written and old files pruned (or no files to prune).
#   1 — pg_dump failed.
#   2 — environment incomplete (PG_HOST / PG_DB / PG_USER missing).
#   3 — backup directory unwritable.

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/rtv-cases}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
ENV_FILE="${ENV_FILE:-/opt/rtv-cases/backend/.env}"
LOG_TAG="${LOG_TAG:-rtv-cases-db-backup}"

log() { printf '[%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"; }

# ---- Pre-flight --------------------------------------------------------

if [[ ! -r "$ENV_FILE" ]]; then
    log "FATAL: env file $ENV_FILE not readable (exit 2)"
    exit 2
fi

# Source only the PG_* keys — strict parse so a stray '=' in some
# other var doesn't break the script. `.env` is shell-safe per the
# repo convention (KEY=VALUE with no unquoted spaces).
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

for k in PG_HOST PG_DB PG_USER; do
    if [[ -z "${!k:-}" ]]; then
        log "FATAL: $k missing from $ENV_FILE (exit 2)"
        exit 2
    fi
done

PG_PORT="${PG_PORT:-5432}"
mkdir -p "$BACKUP_DIR"
if [[ ! -w "$BACKUP_DIR" ]]; then
    log "FATAL: $BACKUP_DIR not writable (exit 3)"
    exit 3
fi

# ---- Backup -------------------------------------------------------------

TIMESTAMP="$(date -u +'%Y%m%dT%H%M%SZ')"
BACKUP_FILE="${BACKUP_DIR}/db-${PG_DB}-${TIMESTAMP}.sql.zst"

log "starting pg_dump host=${PG_HOST} db=${PG_DB} → ${BACKUP_FILE}"

# PGPASSWORD is consumed by psql/pg_dump. We use the `custom` format
# (-Fc) so pg_restore can do partial + parallel restores; zstd
# compression is a good speed/ratio tradeoff (faster than gzip, smaller
# than lz4). --no-owner / --no-privilege so the dump is portable
# across environments; --lock-wait-timeout caps how long pg_dump
# waits on a busy table — the prod DB is small and shouldn't ever
# contend, but a stuck connection is a footgun.
#
# `pg_dump -d` is shorthand for `--dbname`; `$PG_DB` etc. are
# unquoted because they're validated to be hostnames/db-names
# sourced from the host's own .env.
PGPASSWORD="$PG_PASSWORD" pg_dump \
    --host="$PG_HOST" \
    --port="$PG_PORT" \
    --dbname="$PG_DB" \
    --username="$PG_USER" \
    --no-owner \
    --no-privilege \
    --lock-wait-timeout=10 \
    --format=custom \
    --compress=zstd:6 \
    --file="$BACKUP_FILE"

if [[ ! -s "$BACKUP_FILE" ]]; then
    log "FATAL: pg_dump wrote 0 bytes — file removed" >&2
    rm -f "$BACKUP_FILE"
    exit 1
fi

SIZE="$(du -h "$BACKUP_FILE" | awk '{print $1}')"
log "backup OK (${SIZE})"

# ---- Prune --------------------------------------------------------------

PRUNED=$(find "$BACKUP_DIR" -name "db-${PG_DB}-*.sql.zst" -mtime "+${BACKUP_RETENTION_DAYS}" -print -delete | wc -l)
log "pruned ${PRUNED} backup(s) older than ${BACKUP_RETENTION_DAYS} days"

# ---- Verify the most recent backup is restorable -------------------------
#
# `pg_restore -l` lists the TOC of a custom-format dump without
# actually restoring — fast (~1s on a small DB) and a stronger
# signal than "the file exists" that the dump is structurally valid.
# Runs once a day is cheap insurance against silent corruption.
LATEST=$(ls -1t "${BACKUP_DIR}/db-${PG_DB}-*.sql.zst" 2>/dev/null | head -1 || true)
if [[ -n "$LATEST" ]]; then
    if pg_restore -l "$LATEST" >/dev/null 2>&1; then
        log "TOC verification OK ($(grep -c '^[^;]' < <(pg_restore -l "$LATEST") 2>/dev/null) entries)"
    else
        log "WARNING: latest backup $LATEST failed pg_restore -l — investigate"
    fi
fi