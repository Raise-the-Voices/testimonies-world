#!/bin/bash
set -eo pipefail

cd /opt/rtv-cases
PROJECT_ROOT="$(pwd)"   # Used by the nohup fallbacks below to return here
                        # after `cd`ing into backend/ or frontend/.

SITE="https://cases.raisethevoices.org"

# Tag before deploy for rollback
git tag deploy-$(date +%Y%m%d-%H%M%S)

# Stash any locally-modified tracked files and untracked files so the
# pull can apply cleanly. Some files (settings.py, .env) are managed
# per-host by design — see commit 58da23a. If there's nothing to stash,
# this is a no-op.
git stash push -u -m "deploy-autostash-$(date +%s)" || true

# Pull latest. Use `fetch + reset --hard` rather than `pull` so this
# stays correct after a force-push (pull would error with "divergent
# branches" if origin/main was rewritten). Local-only files (settings.py,
# .env, etc.) are preserved by the autostash above.
git fetch origin main
git reset --hard origin/main

# Re-apply local customizations. ABORT on conflict — better than
# shipping half-merged source. The old code did `git stash pop ||
# echo "WARNING: ..."` which masked the failure: under `set -e`,
# the `||` defang made the script continue into `pip install` /
# `migrate` / `npm run build` against a half-merged tree, which is
# the worst-case failure mode (a successful-looking deploy that's
# silently inconsistent).
#
# Failure-recovery path: `git checkout --theirs backend/.env` is the
# only known-good resolution — `.env` is per-host (see commit 58da23a)
# and never wants upstream's copy. Operators who hit a real conflict
# should resolve it manually and re-run deploy.
if ! git stash pop; then
    echo "DEPLOY FAILED: 'git stash pop' had conflicts — refusing to deploy half-merged code." >&2
    echo "Inspect with: git status" >&2
    echo "Clean up with: git checkout --theirs backend/.env && git stash drop && bash scripts/deploy.sh" >&2
    exit 1
fi

# Backend
cd backend
source .venv/bin/activate
pip install -r requirements.txt --quiet
python manage.py migrate --noinput
python manage.py collectstatic --noinput
deactivate

# Frontend
cd ../frontend
npm ci --omit=dev
npm run build

# @sveltejs/adapter-node 5.5.x under @sveltejs/kit 2.66 / vite 7 emits the
# server runtime into build/server/chunks/ rather than build/. The runtime
# locates its static asset directory relative to its own module URL, so it
# looks for build/server/chunks/client, finds nothing, and mounts no static
# middleware at all — every /_app/* and /robots.txt request falls through to
# SSR and 404s. The symlink puts the real client bundle where the runtime
# expects it. Harmless once a future adapter release fixes the layout.
if [ -d build/server/chunks ] && [ -d build/client ]; then
    ln -sfn ../../client build/server/chunks/client
fi

# Publish the client bundle to the nginx document root. nginx serves /_app/
# and /robots.txt straight off disk from here and falls back to the node
# service if a file is missing — see /etc/nginx/sites-available/rtv-cases.
sudo mkdir -p /var/www/cases
sudo rsync -a --delete build/client/ /var/www/cases/
sudo chown -R www-data:www-data /var/www/cases
sudo chmod -R u+rwX,g+rX,o+rX /var/www/cases

# Sync the canonical nginx site config from the repo to the host. Without
# this, the deployed config drifts from `scripts/nginx/rtv-cases` and every
# Django route that isn't explicitly listed in the on-disk file falls
# through to the SvelteKit catch-all — which is how /media/ 404s for local
# profile images and /admin/ sometimes lands on the wrong upstream.
#
# Back up any existing file before overwriting, only install + reload if
# the config actually changed, and validate with `nginx -t` before
# applying so a syntax error doesn't take the whole site down.
SITE_CONF_SRC="$PROJECT_ROOT/scripts/nginx/rtv-cases"
SITE_CONF_DST="/etc/nginx/sites-available/rtv-cases"
SITE_LINK="/etc/nginx/sites-enabled/rtv-cases"
SITE_BAK="/etc/nginx/sites-available/rtv-cases.bak-$(date +%Y%m%d-%H%M%S)"

if [ ! -f "$SITE_CONF_SRC" ]; then
    echo "  WARN: $SITE_CONF_SRC not found in repo — skipping nginx sync"
else
    # Back up the existing file if it differs from what we'd install.
    if [ -f "$SITE_CONF_DST" ] && ! sudo cmp -s "$SITE_CONF_SRC" "$SITE_CONF_DST"; then
        sudo cp -a "$SITE_CONF_DST" "$SITE_BAK"
        echo "  backed up existing config to $SITE_BAK"
    fi

    if [ ! -f "$SITE_CONF_DST" ] || ! sudo cmp -s "$SITE_CONF_SRC" "$SITE_CONF_DST"; then
        sudo install -m 644 "$SITE_CONF_SRC" "$SITE_CONF_DST"
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

# Restart the app services. This is not optional: both processes hold their
# build in memory, so without a restart the node service keeps emitting HTML
# that references the *previous* build's asset hashes, and every one of those
# assets 404s. Django likewise keeps running the old code.
#
# Defensive restart sequence: systemd may have the unit in a failed state
# from earlier deploys, or the unit file may have drifted on the host.
# `reset-failed` clears the failure flag; if the unit still won't come
# up, we fall back to nohup so the deploy can self-heal instead of
# leaving prod 502.
sudo systemctl reset-failed rtv-cases-backend 2>/dev/null || true
sudo systemctl reset-failed rtv-cases-frontend 2>/dev/null || true

# Kill any stray gunicorn / Node processes from previous deploys that
# might be holding port 8040 / 3000.
pkill -f 'gunicorn.*testimonies.wsgi' 2>/dev/null || true
pkill -f 'node .*build/index.js' 2>/dev/null || true
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
    # Activate the venv in a subshell so PATH leaks don't propagate, and
    # exec gunicorn under sudo -u deploy (the systemd unit's User=).
    sudo -u deploy /opt/rtv-cases/backend/.venv/bin/gunicorn \
        testimonies.wsgi:application \
        --bind 127.0.0.1:8040 \
        --workers 2 \
        --daemon \
        --pid /tmp/cases-backend.pid \
        --access-logfile /tmp/cases-backend.access.log \
        --error-logfile /tmp/cases-backend.err.log
    cd "$PROJECT_ROOT"

    # Verify it actually came up before declaring victory.
    sleep 3
    if curl -s -o /dev/null --max-time 3 http://127.0.0.1:8040/api/persons/; then
        echo "  fallback gunicorn up on :8040"
    else
        echo "  ERROR: fallback gunicorn did not bind :8040" >&2
        echo "  See /tmp/cases-backend.err.log" >&2
        tail -20 /tmp/cases-backend.err.log >&2 2>/dev/null || true
    fi
fi

# --- Frontend fallback: detached node if systemd didn't bring it up ----
# Same pattern as the backend: --daemon-equivalent (nohup here is fine
# because node doesn't fork like gunicorn), with stderr/stdout captured.
frontend_up=0
if curl -s -o /dev/null --max-time 2 http://127.0.0.1:3000/; then
    frontend_up=1
elif sudo systemctl is-active --quiet rtv-cases-frontend 2>/dev/null \
      && curl -s -o /dev/null --max-time 2 http://127.0.0.1:3000/; then
    frontend_up=1
fi
if [ "$frontend_up" != 1 ]; then
    echo "  systemd restart did not bring up the frontend; falling back to detached node"
    cd /opt/rtv-cases/frontend
    sudo -u deploy env PORT="${PORT:-3000}" HOST=127.0.0.1 \
        setsid node build/index.js \
            < /dev/null > /tmp/cases-frontend.log 2>&1 &
    disown
    cd "$PROJECT_ROOT"

    sleep 3
    if curl -s -o /dev/null --max-time 3 http://127.0.0.1:3000/; then
        echo "  fallback node up on :3000"
    else
        echo "  ERROR: fallback node did not bind :3000" >&2
        echo "  See /tmp/cases-frontend.log" >&2
        tail -20 /tmp/cases-frontend.log >&2 2>/dev/null || true
    fi
fi

# Install the canonical nginx site config from the repo. This is the file
# that was missing the /accounts/ block on 2026-08-27, locking admins out.
# Writing directly to sites-enabled so the typical `include sites-enabled/*;`
# directive picks it up regardless of whether sites-available is also used.
sudo install -d -m 0755 /etc/nginx/sites-enabled
sudo install -m 0644 "$PROJECT_ROOT/scripts/nginx/rtv-cases" /etc/nginx/sites-enabled/rtv-cases

# Reload nginx so it picks up the new bundle without dropping connections.
# `nginx -t` validates the config first — if the file we just installed has
# a syntax error, this aborts before the reload and the smoke test below
# will catch the issue.
sudo nginx -t && sudo nginx -s reload

# Sanity check that the installed nginx site config exposes the routes
# Django actually serves. We check the file we just installed rather than
# running `sudo nginx -T`, because `nginx -T` on a host where the master
# is already bound to :80 can race against the master for the port — its
# internal bind test fails, nothing is written to stdout, and (without
# 2>/dev/null) you'd see the real error instead of a misleading
# "missing location block" report. With the previous 2>/dev/null, the
# failure mode was: deploy aborts with the wrong message even though the
# config is fine.
#
# The file we just installed IS the source of truth on disk: `nginx -t`
# above already validated that the include chain parses, and
# `nginx -s reload` already applied it. The smoke test below curl-checks
# the routes against the live URL — that's what catches real routing
# problems (e.g. someone editing /etc/nginx/nginx.conf to drop the
# sites-enabled include). This check is just an early guard against the
# deploy script itself installing a broken file.
if ! grep -qE 'location[[:space:]]+/(accounts|admin|api)/[[:space:]]' /etc/nginx/sites-enabled/rtv-cases; then
    echo "DEPLOY FAILED: /etc/nginx/sites-enabled/rtv-cases is missing a location block for /accounts/, /admin/, or /api/." >&2
    echo "See scripts/nginx/rtv-cases for the canonical site config." >&2
    exit 1
fi

# Smoke test. Fetch the homepage, extract the entry script hash from the HTML
# the server just rendered, and confirm that exact asset resolves. This is what
# catches the failure modes above — a stale process or broken static serving
# both leave the site returning 200 for pages while every asset 404s, which
# otherwise exits 0 and reports "Deploy complete".
echo 'Verifying deploy...'
ok=0
for attempt in 1 2 3 4 5 6 7 8 9 10; do
    html=$(curl -fsS --max-time 15 "$SITE/" || true)
    # `|| true` swallows grep's exit-1 on no match — without it, set -eo
    # pipefail would abort the script on the first 502 and the retry loop
    # would only ever run once.
    entry=$(printf '%s' "$html" \
        | grep -o '[./]*_app/immutable/entry/start\.[A-Za-z0-9_-]*\.js' \
        | head -1 || true)
    if [ -n "$entry" ]; then
        asset_url="$SITE/$(printf '%s' "$entry" | sed 's|^[./]*||')"
        code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$asset_url" || true)
        api=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$SITE/api/" || true)
        # /accounts/google/login/ returns 200 once allauth is wired through nginx;
        # a 404 here means the nginx site config is missing the /accounts/ block
        # and admins are about to be locked out. Accept 200 or 302 (redirect).
        accounts=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$SITE/accounts/google/login/" || true)
        if [ "$code" = 200 ] && [ "$api" = 200 ] \
           && { [ "$accounts" = 200 ] || [ "$accounts" = 302 ]; }; then
            echo "  entry asset OK: $asset_url"
            echo "  api OK"
            echo "  /accounts/google/login/ OK ($accounts)"
            ok=1
            break
        fi
        echo "  attempt $attempt: assets=$code api=$api accounts=$accounts"
    fi
    echo "  attempt $attempt: not ready yet"
    sleep 3
done

if [ "$ok" != 1 ]; then
    echo "DEPLOY FAILED: the site is serving pages but its assets do not resolve." >&2
    echo "Check:  systemctl status rtv-cases-frontend" >&2
    echo "        ls -la /opt/rtv-cases/frontend/build/server/chunks/client" >&2
    echo "        ls /var/www/cases/_app/immutable/entry/" >&2
    echo "        sudo nginx -T | grep -E 'location /(accounts|admin|api)/'  # missing /accounts/ = 404 on login" >&2
    echo "Roll back with:  git checkout \$(git tag -l 'deploy-*' | tail -2 | head -1)" >&2
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
    for unit in rtv-cases-backend-watchdog.service rtv-cases-backend-watchdog.timer; do
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
    echo "  watchdog timer enabled: $(sudo systemctl is-active rtv-cases-backend-watchdog.timer)"
else
    echo "  WARN: $WD_SRC_DIR not found — skipping watchdog install"
fi

echo 'Deploy complete'
