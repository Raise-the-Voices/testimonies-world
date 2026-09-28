#!/bin/bash
set -eo pipefail

# rtv-cases deploy — run by .github/workflows/deploy.yml over SSH.
#
# Architecture:
#   - The frontend SvelteKit build runs in GitHub Actions (Node 22) and
#     arrives at $INCOMING_FRONTEND via `appleboy/scp-action@v0.1.4`
#     before this script runs. We do NOT run `npm ci` or `npm run build`
#     here.
#   - The source refresh below is a NARROW `git checkout origin/main
#     -- <paths>` — never `git reset --hard`. Untracked host files
#     (backend/.env, vetted per-host tweaks) survive.
#   - backend/testimonies/    — IS in the checkout list. Per-host
#     configuration belongs in backend/.env (read by the systemd
#     unit's EnvironmentFile=), not in settings.py. The directory
#     checkout will refuse to overwrite a tracked-modified
#     settings.py without `-f` — that refusal is the operator's
#     signal to move any hand-edit into .env and re-run.
#   - The 6-attempt smoke test at the end (entry-asset hash on disk
#     must match what's served) catches the half-deployed class of
#     failures that were the recurring cause of recent 500/502s.

cd /opt/rtv-cases
PROJECT_ROOT="$(pwd)"

# Mark the deploy checkout as a safe.directory. Git 2.35.2+ refuses to
# operate on a repo owned by a different UID unless explicitly
# allowlisted — the deploy user (typically `deploy`) doesn't own
# /opt/rtv-cases on prod, so `git fetch` would otherwise fail with
# "detected dubious ownership" (run #216, 2026-09-21). Targeted path
# keeps the allowlist as narrow as possible.
git config --global --add safe.directory /opt/rtv-cases

SITE="https://cases.raisethevoices.org"

# Inbound frontend build directory. The GitHub Actions `deploy` job
# scp's `frontend/build/` to this exact path before invoking this
# script. Override via env var to test locally (e.g. with a manual
# `npm run build`).
INCOMING_FRONTEND="${INCOMING_FRONTEND:-/opt/rtv-cases-deploy/frontend-build}"

# Verify the inbound artifact looks right. Without this check, a
# partial scp or stale path silently deploys an empty /var/www/cases —
# every /testimonies/_app/ request 404s.
if [ ! -d "$INCOMING_FRONTEND/client/testimonies/_app" ]; then
    echo "DEPLOY FAILED: $INCOMING_FRONTEND/client/testimonies/_app is missing." >&2
    echo "  The deploy workflow scps frontend/build/ here before running deploy.sh." >&2
    echo "  Re-run the deploy workflow, or set INCOMING_FRONTEND to a directory containing the build." >&2
    exit 1
fi

# Verify backend/.env exists — the systemd unit's EnvironmentFile=
# silently degrades to a partial config if the file is missing, and
# gunicorn then refuses to start. Fail loudly here, not at the smoke
# test.
if [ ! -f "$PROJECT_ROOT/backend/.env" ]; then
    echo "DEPLOY FAILED: $PROJECT_ROOT/backend/.env is missing." >&2
    echo "  The systemd unit EnvironmentFile= this; without it gunicorn cannot start." >&2
    exit 1
fi

# --- Source refresh — narrow, NEVER `git reset --hard` ---
# Pulls latest tracked files for the paths we actually deploy. The
# narrow list excludes:
#   - frontend/build/         — gitignored, overwritten by the artifact
#   - backend/.env            — gitignored, OS-level source of truth
#   - backend/testimonies/    — see note at file top: this directory IS
#     in the checkout list, so settings.py propagates from main. Any
#     operator hand-edit to settings.py will be REJECTED by `git
#     checkout` (no `-f`); move the change to backend/.env (the
#     supported surface) and re-run.
# `git checkout` refuses to overwrite tracked-modified files unless
# `-f` is passed. That's intentional: we will NOT silently clobber an
# operator's hand-edit. The owner of that hand-edit resolves the
# conflict (commit, stash, or drop the local change and re-run).
git fetch origin main
git checkout origin/main -- \
    backend/requirements.txt \
    backend/cases/ \
    backend/testimonies/ \
    backend/manage.py \
    scripts/deploy.sh \
    scripts/nginx/rtv-cases \
    scripts/systemd/

# --- Backend ---
cd backend
source .venv/bin/activate
pip install -r requirements.txt --quiet
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Move any profile images still sitting under the auth-gated MEDIA_ROOT
# into PUBLIC_MEDIA_ROOT, where nginx serves them off disk. Idempotent —
# on a host that has already been migrated this reports 'already public'
# and changes nothing, so it is safe on every deploy. Needed on each host
# separately because backend/media/ is gitignored: the file move can't
# travel in a commit the way the migration does.
python manage.py publish_profile_images
deactivate

# nginx (running as www-data) reads the public media tree directly, so it
# needs traverse + read on the directory. Files written by gunicorn land
# with the backend user's umask; normalize them here rather than relying
# on whatever umask the service happened to start with.
sudo chmod -R u+rwX,g+rX,o+rX "$PROJECT_ROOT/backend/public_media"

# --- Frontend ---
# Apply the adapter-node 5.5.x symlink workaround to the inbound build.
# @sveltejs/adapter-node 5.5.x under @sveltejs/kit 2.50+ / vite 7 emits
# the server runtime into build/server/chunks/ rather than build/. The
# runtime locates its static asset directory relative to its own module
# URL, so it looks for build/server/chunks/client, finds nothing, and
# mounts no static middleware at all — every /_app/* and /robots.txt
# request falls through to SSR and 404s. The symlink puts the real
# client bundle where the runtime expects it. Pinning the adapter
# version in package.json is the long-term fix; this carve-out survives
# until then.
if [ -d "$INCOMING_FRONTEND/server/chunks" ] && [ -d "$INCOMING_FRONTEND/client" ]; then
    ln -sfn ../../client "$INCOMING_FRONTEND/server/chunks/client"
fi

# Refresh the on-disk frontend/build/ from the inbound artifact.
# frontend/build/ is gitignored, so this rsync is the *only* way
# frontend assets land on the VM. --delete keeps stale hashed chunks
# from accumulating across deploys.
sudo rsync -a --delete "$INCOMING_FRONTEND/" "$PROJECT_ROOT/frontend/build/"

# Publish the client bundle to the nginx document root. nginx serves
# /_app/ and /robots.txt straight off disk from here and falls back to
# the node service if a file is missing — see /etc/nginx/sites-available/rtv-cases.
sudo mkdir -p /var/www/cases
sudo rsync -a --delete "$INCOMING_FRONTEND/client/testimonies/" /var/www/cases/
sudo chown -R www-data:www-data /var/www/cases
sudo chmod -R u+rwX,g+rX,o+rX /var/www/cases

# --- Sync canonical nginx site config from the repo ---
# Without this, the deployed config drifts from `scripts/nginx/rtv-cases`
# and every Django route that isn't explicitly listed in the on-disk
# file falls through to the SvelteKit catch-all — which is how
# /media/ 404s for local profile images and /admin/ sometimes lands on
# the wrong upstream. Idempotent: install only if the on-disk file is
# stale, validate with `nginx -t` before reloading so a syntax error
# doesn't take the whole site down.
SITE_CONF_SRC="$PROJECT_ROOT/scripts/nginx/rtv-cases"
SITE_CONF_DST="/etc/nginx/sites-available/rtv-cases"
SITE_LINK="/etc/nginx/sites-enabled/rtv-cases"
SITE_BAK="/etc/nginx/sites-available/rtv-cases.bak-$(date +%Y%m%d-%H%M%S)"

if [ ! -f "$SITE_CONF_SRC" ]; then
    echo "  WARN: $SITE_CONF_SRC not found in repo — skipping nginx sync"
else
    if [ -f "$SITE_CONF_DST" ] && ! sudo cmp -s "$SITE_CONF_SRC" "$SITE_CONF_DST"; then
        sudo cp -a "$SITE_CONF_DST" "$SITE_BAK"
        echo "  backed up existing config to $SITE_BAK"
    fi

    if [ ! -f "$SITE_CONF_DST" ] || ! sudo cmp -s "$SITE_CONF_SRC" "$SITE_CONF_DST"; then
        sudo install -m 644 "$SITE_CONF_SRC" "$SITE_CONF_DST"
        sudo install -d -m 0755 /etc/nginx/sites-enabled
        sudo ln -sfn "$SITE_CONF_DST" "$SITE_LINK"

        if sudo nginx -t; then
            sudo nginx -s reload
            echo "  nginx config synced and reloaded"
        else
            echo "  nginx -t FAILED — restoring backup $SITE_BAK"
            if [ -f "$SITE_BAK" ]; then
                sudo cp -a "$SITE_BAK" "$SITE_CONF_DST"
                sudo nginx -t && sudo nginx -s reload
            fi
            exit 1
        fi
    fi
fi

# --- Sync canonical systemd unit files from the repo ---
# The backend + frontend unit files live in scripts/systemd/ so they
# can't drift. Without this, a typo (e.g. 127.0.0.1:8000 instead of
# :8040 on 2026-08-30) survives across deploys and the site 502s.
# Idempotent: copies only when the on-disk file is stale (cmp -s).
UNIT_SRC_DIR="$PROJECT_ROOT/scripts/systemd"
UNIT_DST_DIR="/etc/systemd/system"

for unit in rtv-cases-backend.service rtv-cases-frontend.service; do
    src="$UNIT_SRC_DIR/$unit"
    dst="$UNIT_DST_DIR/$unit"
    if [ ! -f "$src" ]; then
        echo "  WARN: $src missing — skipping $unit" >&2
        continue
    fi
    if [ ! -f "$dst" ] || ! sudo cmp -s "$src" "$dst"; then
        sudo install -m 0644 "$src" "$dst"
        echo "  installed $unit"
    fi
done
sudo systemctl daemon-reload

# Restart the app services. This is not optional: both processes hold
# their build in memory, so without a restart the node service keeps
# emitting HTML that references the *previous* build's asset hashes,
# and every one of those assets 404s. Django likewise keeps running
# the old code.
sudo systemctl reset-failed rtv-cases-backend 2>/dev/null || true
sudo systemctl reset-failed rtv-cases-frontend 2>/dev/null || true

# Kill any stray gunicorn / Node processes from previous deploys that
# might be holding port 8040 / 3000. The patterns are tightened to
# match only THIS project's processes — `pkill -f 'node'` is far too
# broad and has been removed.
pkill -f 'gunicorn.*testimonies\.wsgi.*--bind 127\.0\.0\.1:8040' 2>/dev/null || true
pkill -f 'node .*/frontend/build/index\.js' 2>/dev/null || true
sleep 1

sudo systemctl restart rtv-cases-backend 2>/dev/null || true
sudo systemctl restart rtv-cases-frontend 2>/dev/null || true
sleep 3

# --- Backend fallback: detached gunicorn if systemd didn't bring it up -----
# We only fire this if neither systemd says the service is active nor :8040
# is listening. Without this, a broken systemd unit on prod keeps the
# site 502'd indefinitely.
#
# Run as the `deploy` user (matching the systemd unit's User=) so file
# ownership matches the rest of the install. --daemon tells gunicorn to
# fully background itself and write its pidfile — no shell-trick needed
# to survive the appleboy/ssh-action session teardown that would
# otherwise kill a plain nohup child.
backend_up=0
if curl -s -o /dev/null --max-time 2 http://127.0.0.1:8040/api/persons/; then
    backend_up=1
elif sudo systemctl is-active --quiet rtv-cases-backend 2>/dev/null \
      && curl -s -o /dev/null --max-time 2 http://127.0.0.1:8040/api/persons/; then
    backend_up=1
fi
if [ "$backend_up" != 1 ]; then
    echo "  systemd restart did not bring up the backend; falling back to detached gunicorn"
    cd /opt/rtv-cases/backend
    sudo -u deploy /opt/rtv-cases/backend/.venv/bin/gunicorn \
        testimonies.wsgi:application \
        --bind 127.0.0.1:8040 \
        --workers 2 \
        --daemon \
        --pid /tmp/cases-backend.pid \
        --access-logfile /tmp/cases-backend.access.log \
        --error-logfile /tmp/cases-backend.err.log
    cd "$PROJECT_ROOT"

    sleep 3
    if curl -s -o /dev/null --max-time 3 http://127.0.0.1:8040/api/persons/; then
        echo "  fallback gunicorn up on :8040"
    else
        echo "  ERROR: fallback gunicorn did not bind :8040" >&2
        echo "  See /tmp/cases-backend.err.log:" >&2
        tail -20 /tmp/cases-backend.err.log >&2 2>/dev/null || true
    fi
fi

# --- Frontend: rely on systemd + Restart=always ---
# The systemd unit (scripts/systemd/rtv-cases-frontend.service) already
# carries the production env (PUBLIC_BASE_PATH, ORIGIN, HOST, PORT) and
# `Restart=always` with `RestartSec=5` + `StartLimitBurst=10`. The old
# nohup/disown fallback ran node under /tmp/cases-frontend.log with
# env vars duplicated from the unit — when the unit's env drifted, the
# fallback served a different (often 404'd) response than the unit.
# Removing the fallback eliminates that drift; if systemd genuinely
# fails to bring the unit back, the smoke test below will reject the
# deploy and the operator investigates the unit.

# Sanity check that the installed nginx site config exposes the routes
# Django actually serves. We check the file we just installed rather
# than running `sudo nginx -T`, because `nginx -T` on a host where the
# master is already bound to :80 can race against the master for the
# port — its internal bind test fails, nothing is written to stdout,
# and (without 2>/dev/null) you'd see the real error instead of a
# misleading "missing location block" report. With the previous
# 2>/dev/null, the failure mode was: deploy aborts with the wrong
# message even though the config is fine.
#
# The file we just installed IS the source of truth on disk: `nginx -t`
# above already validated that the include chain parses, and
# `nginx -s reload` already applied it. The smoke test below curl-checks
# the routes against the live URL — that's what catches real routing
# problems. This check is just an early guard against the deploy
# script itself installing a broken file.
if ! grep -qE 'location[[:space:]]+/(accounts|admin|api)/[[:space:]]' /etc/nginx/sites-enabled/rtv-cases; then
    echo "DEPLOY FAILED: /etc/nginx/sites-enabled/rtv-cases is missing a location block for /accounts/, /admin/, or /api/." >&2
    echo "See scripts/nginx/rtv-cases for the canonical site config." >&2
    exit 1
fi

# --- Smoke test. Verifies five things atomically — each catches a
# different failure mode we hit on 2026-09-21:
#
#   1. node is bound on :3000 (not the OLD node from a previous deploy)
#   2. /testimonies/ returns 200 (or 308 redirect — both = node responding)
#   3. the HTML's referenced entry script is non-empty (no 404 page from
#      a stale node serving an error route)
#   4. the HTML's entry hash MATCHES the on-disk bundle (catches the
#      stale-node + fresh-bundle class of failures we hit today)
#   5. the asset actually returns 200
#   6. bare-host root redirects (302) — proves fix/nginx-root-redirect
#      is in the deployed nginx config
#
# All six must pass on the same attempt, otherwise the deploy is
# rejected.

echo 'Verifying deploy...'
ok=0
for attempt in 1 2 3 4 5 6 7 8 9 10; do
    # 1. node bound on :3000 — empty port is an instant fail (don't retry)
    PID=$(ss -tlnpH 2>/dev/null | awk '/:3000/ {match($0,/pid=([0-9]+)/,a); print a[1]; exit}')
    if [ -z "$PID" ]; then
        echo "  attempt $attempt: nothing listening on :3000"
        sleep 3
        continue
    fi

    # 2. /testimonies/ responds — empty body means node is down or 404'd
    html=$(curl -fsS --max-time 15 "$SITE/testimonies/" || true)
    if [ -z "$html" ]; then
        echo "  attempt $attempt: /testimonies/ returned empty (node not responding)"
        sleep 3
        continue
    fi

    # 3. extract entry script hash from rendered HTML
    entry=$(printf '%s' "$html" \
        | grep -oE 'start\.[A-Za-z0-9_-]+\.js' \
        | head -1 || true)
    if [ -z "$entry" ]; then
        echo "  attempt $attempt: HTML has no entry script (node serving 404 page)"
        sleep 3
        continue
    fi

    # 4. HTML's entry hash must exist on disk under /var/www/cases/
    disk_entry=$(ls /var/www/cases/_app/immutable/entry/ 2>/dev/null \
        | grep -oE 'start\.[A-Za-z0-9_-]+\.js' \
        | head -1 || true)
    if [ "$entry" != "$disk_entry" ]; then
        echo "  attempt $attempt: HTML refs $entry but disk has $disk_entry — node stale, restart needed"
        sleep 3
        continue
    fi

    # 5. fetch the asset
    asset_url="$SITE/_app/immutable/entry/$entry"
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$asset_url" || true)

    # 6. bare-host root must redirect to /testimonies/ (proves nginx
    # config from fix/nginx-root-redirect is live, not the old 404 page)
    root=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$SITE/" || true)

    if [ "$code" = 200 ] && [ "$root" = 302 ]; then
        echo "  entry asset OK: $asset_url"
        echo "  HTML/disk hash match: $entry"
        echo "  bare-host redirects: $root"
        ok=1
        break
    fi
    echo "  attempt $attempt: asset=$code root=$root"
    sleep 3
done

if [ "$ok" != 1 ]; then
    echo "DEPLOY FAILED: the site is serving pages but its assets do not resolve." >&2
    echo "Check:  systemctl status rtv-cases-frontend" >&2
    echo "        ls -la /opt/rtv-cases/frontend/build/server/chunks/client" >&2
    echo "        ls /var/www/cases/_app/immutable/entry/" >&2
    echo "        sudo journalctl -u rtv-cases-frontend -n 30" >&2
    exit 1
fi

# --- Install + enable the backend watchdog (safety net) ---
# rtv-cases-backend-watchdog.{service,timer} runs a one-shot healthcheck
# every 60s: if /api/persons/ is down on :8040, it starts gunicorn as
# the deploy user with --daemon. This catches the case where systemd
# rtv-cases-backend silently fails (which has happened) AND the case
# where an admin kills gunicorn manually — the site auto-heals within
# 60s without operator intervention.
#
# Idempotent: install copies only if the on-disk file is stale
# (cmp -s), reloads the daemon, enables+starts the timer.
WD_SRC_DIR="$PROJECT_ROOT/scripts/systemd"
WD_DST_DIR="/etc/systemd/system"

if [ -d "$WD_SRC_DIR" ]; then
    for unit in rtv-cases-backend-watchdog.service rtv-cases-backend-watchdog.timer \
               rtv-cases-db-backup.service rtv-cases-db-backup.timer; do
        src="$WD_SRC_DIR/$unit"
        dst="$WD_DST_DIR/$unit"
        if [ ! -f "$src" ]; then
            echo "  WARN: $src missing — skipping $unit" >&2
            continue
        fi
        if [ ! -f "$dst" ] || ! sudo cmp -s "$src" "$dst"; then
            sudo install -m 0644 "$src" "$dst"
            echo "  installed $unit"
        fi
    done

    sudo systemctl daemon-reload
    sudo systemctl enable rtv-cases-backend-watchdog.timer >/dev/null 2>&1 || true
    sudo systemctl restart rtv-cases-backend-watchdog.timer >/dev/null 2>&1 || true
    sudo systemctl enable rtv-cases-db-backup.timer >/dev/null 2>&1 || true
    sudo systemctl restart rtv-cases-db-backup.timer >/dev/null 2>&1 || true
    echo "  watchdog timer enabled: $(sudo systemctl is-active rtv-cases-backend-watchdog.timer)"
    echo "  db-backup timer enabled: $(sudo systemctl is-active rtv-cases-db-backup.timer)"
else
    echo "  WARN: $WD_SRC_DIR not found — skipping watchdog install"
fi

echo 'Deploy complete'
