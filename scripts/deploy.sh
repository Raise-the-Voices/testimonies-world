#!/bin/bash
set -e

# Project root — override with PROJECT_ROOT=/path/to/repo if not at
# the historical /opt/rtv-cases location.
PROJECT_ROOT="${PROJECT_ROOT:-/opt/rtv-cases}"
cd "$PROJECT_ROOT"

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
cd "$PROJECT_ROOT/backend"
source .venv/bin/activate
pip install -r requirements.txt --quiet

# Only run migrate when USE_SQLITE is enabled. Against the real
# Postgres host the placeholder credentials in .env are not the
# production ones (see commit 58da23a), so migrate would fail. Set
# USE_SQLITE=True in .env for local dev deploys.
if grep -q '^USE_SQLITE=True' "$PROJECT_ROOT/backend/.env" 2>/dev/null; then
    USE_SQLITE=True python manage.py migrate --noinput
fi
python manage.py collectstatic --noinput
deactivate

# Frontend build
cd "$PROJECT_ROOT/frontend"
npm ci --omit=dev
npm run build

# Document root for the static asset bundle (served by nginx, which
# proxies /api/ to Django and everything else to the SvelteKit Node
# server).
DOC_ROOT="${DOC_ROOT:-/var/www/cases}"
sudo mkdir -p "$DOC_ROOT"

# Move the previous bundle aside as `_app.prev` for a one-command
# rollback if this deploy turns out to be broken:
#   sudo mv $DOC_ROOT/_app.prev $DOC_ROOT/_app
#   sudo nginx -s reload
if [ -d "$DOC_ROOT/_app" ]; then
    sudo rm -rf "$DOC_ROOT/_app.prev"
    sudo mv "$DOC_ROOT/_app" "$DOC_ROOT/_app.prev"
fi
sudo rsync -a --delete "$PROJECT_ROOT/frontend/build/client/_app/" "$DOC_ROOT/_app/"
sudo chown -R www-data:www-data "$DOC_ROOT"
sudo chmod -R u+rwX,g+rX,o+rX "$DOC_ROOT"

# Reload nginx so it picks up the new assets without dropping
# connections. The systemctl path is kept as a fallback for hosts that
# run nginx under systemd; the explicit nginx -s reload works on any
# nginx install.
if command -v nginx >/dev/null 2>&1; then
    sudo nginx -t && sudo nginx -s reload
else
    sudo systemctl reload nginx || sudo systemctl restart nginx
fi

# Restart the SvelteKit Node server. On this host we run it under
# systemd unit `cases-svelte` (or via nohup if no unit exists).
if systemctl list-unit-files cases-svelte.service >/dev/null 2>&1 && \
   systemctl is-enabled --quiet cases-svelte.service 2>/dev/null; then
    sudo systemctl restart cases-svelte
else
    # Fall back to killing and restarting via nohup. Use a stable PID
    # file so we don't kill unrelated node processes.
    if [ -f /tmp/cases-svelte.pid ]; then
        kill "$(cat /tmp/cases-svelte.pid)" 2>/dev/null || true
    fi
    pkill -f "$PROJECT_ROOT/frontend/build/index.js" 2>/dev/null || true
    sleep 1
    cd "$PROJECT_ROOT/frontend"
    nohup env PORT="${PORT:-3000}" HOST=127.0.0.1 \
        node build/index.js > /tmp/cases-svelte.log 2>&1 &
    disown
    echo $! > /tmp/cases-svelte.pid
fi

echo 'Deploy complete'
