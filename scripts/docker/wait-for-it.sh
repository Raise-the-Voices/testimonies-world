#!/usr/bin/env bash
# wait-for-it — block until a TCP port is open (or timeout).
#
# Used by entrypoints to gate the gunicorn boot on postgres / redis
# coming up. /dev/tcp is a bash builtin so we don't need netcat or
# pg_isready in the runtime image.
#
# Usage: wait-for-it.sh <host> <port> [timeout_seconds] [label]
# Exits 0 on success, 1 on timeout.
set -euo pipefail

HOST=${1:?host required}
PORT=${2:?port required}
TIMEOUT=${3:-60}
LABEL=${4:-"$HOST:$PORT"}

echo "wait-for-it: waiting up to ${TIMEOUT}s for ${LABEL}…"

for i in $(seq 1 "$TIMEOUT"); do
    if (echo > "/dev/tcp/${HOST}/${PORT}") 2>/dev/null; then
        echo "wait-for-it: ${LABEL} reachable after ${i}s"
        exit 0
    fi
    sleep 1
done

echo "wait-for-it: ${LABEL} unreachable after ${TIMEOUT}s" >&2
exit 1
