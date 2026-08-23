#!/bin/bash
set -eo pipefail

cd /opt/rtv-cases

SITE="https://cases.raisethevoices.org"

# Tag before deploy for rollback
git tag deploy-$(date +%Y%m%d-%H%M%S)

# Stash any locally-modified tracked files and untracked files so the
# pull can apply cleanly. Some files (settings.py, .env) are managed
# per-host by design — see commit 58da23a. If there's nothing to stash,
# this is a no-op.
git stash push -u -m "deploy-autostash-$(date +%s)" || true

# Pull latest
git pull origin main

# Re-apply local customizations. If there are real merge conflicts
# (rare, only when both local and upstream changed the same lines),
# log a warning and continue — better than aborting the deploy.
git stash pop || echo "WARNING: stash pop had conflicts — manual review needed"

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

# --- Backend fallback: nohup gunicorn if systemd didn't bring it up -----
# We only fire this if neither systemd says the service is active nor :8040
# is listening. Without this, a broken systemd unit on prod keeps the
# site 502'd indefinitely.
backend_up=0
if curl -s -o /dev/null --max-time 2 http://127.0.0.1:8040/api/persons/; then
    backend_up=1
elif sudo systemctl is-active --quiet rtv-cases-backend 2>/dev/null \
      && curl -s -o /dev/null --max-time 2 http://127.0.0.1:8040/api/persons/; then
    backend_up=1
fi
if [ "$backend_up" != 1 ]; then
    echo "  systemd restart did not bring up the backend; falling back to nohup gunicorn"
    cd /opt/rtv-cases/backend
    if [ -f .venv/bin/activate ]; then
        # shellcheck disable=SC1091
        source .venv/bin/activate
    fi
    nohup .venv/bin/gunicorn testimonies.wsgi:application \
        --bind 127.0.0.1:8040 \
        --workers 2 \
        --access-logfile - \
        --error-logfile - \
        > /tmp/cases-backend.log 2>&1 &
    disown
    echo $! > /tmp/cases-backend.pid
    cd "$PROJECT_ROOT"
fi

# --- Frontend fallback: nohup node if systemd didn't bring it up ------
frontend_up=0
if curl -s -o /dev/null --max-time 2 http://127.0.0.1:3000/; then
    frontend_up=1
elif sudo systemctl is-active --quiet rtv-cases-frontend 2>/dev/null \
      && curl -s -o /dev/null --max-time 2 http://127.0.0.1:3000/; then
    frontend_up=1
fi
if [ "$frontend_up" != 1 ]; then
    echo "  systemd restart did not bring up the frontend; falling back to nohup node"
    cd /opt/rtv-cases/frontend
    nohup env PORT="${PORT:-3000}" HOST=127.0.0.1 \
        node build/index.js \
        > /tmp/cases-frontend.log 2>&1 &
    disown
    echo $! > /tmp/cases-frontend.pid
    cd "$PROJECT_ROOT"
fi

# Reload nginx so it picks up the new bundle without dropping connections.
sudo nginx -t && sudo nginx -s reload

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
        if [ "$code" = 200 ] && [ "$api" = 200 ]; then
            echo "  entry asset OK: $asset_url"
            echo "  api OK"
            ok=1
            break
        fi
    fi
    echo "  attempt $attempt: not ready yet"
    sleep 3
done

if [ "$ok" != 1 ]; then
    echo "DEPLOY FAILED: the site is serving pages but its assets do not resolve." >&2
    echo "Check:  systemctl status rtv-cases-frontend" >&2
    echo "        ls -la /opt/rtv-cases/frontend/build/server/chunks/client" >&2
    echo "        ls /var/www/cases/_app/immutable/entry/" >&2
    echo "Roll back with:  git checkout \$(git tag -l 'deploy-*' | tail -2 | head -1)" >&2
    exit 1
fi

echo 'Deploy complete'
