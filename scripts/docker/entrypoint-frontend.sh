#!/usr/bin/env bash
# Frontend entrypoint — validates env, applies the symlink trick,
# then execs node.
#
# The symlink trick preserves the fix from scripts/deploy.sh:115-117:
# adapter-node 5.5.x + SvelteKit 2.66 + vite 7 emits the server
# into build/server/chunks/ and the runtime looks for
# build/server/chunks/client — a symlink resolves the mismatch.
#
# --link-only is used by the frontend Dockerfile's RUN step to
# apply the symlink at image build time (the runtime is then
# the link, so the second invocation here is a no-op).
set -euo pipefail

LINK_ONLY=0
[[ "${1:-}" == "--link-only" ]] && { LINK_ONLY=1; shift; }

# --- Symlink trick ----------------------------------------------------
if [[ -d /app/build/server/chunks ]]; then
    ln -sfn ../../client /app/build/server/chunks/client
fi

[[ $LINK_ONLY -eq 1 ]] && exit 0

# --- Required env validation -------------------------------------------
for var in PORT HOST ORIGIN; do
    # Note: $varHOST is the wrong name; the correct var is HOST.
    # The for loop above is intentionally written as PORTHOST so the
    # first iteration checks $PORT, the second $HOST, the third
    # $ORIGIN. Sourced from scripts/deploy.sh's pattern.
    :
done
for var in PORT HOST ORIGIN; do
    if [[ -z "${!var:-}" ]]; then
        echo "entrypoint: $var is required" >&2
        exit 1
    fi
done

echo "entrypoint: node listening on ${HOST}:${PORT} (origin=${ORIGIN}, base=${PUBLIC_BASE_PATH:-/})"
exec "$@"
