#!/bin/bash
set -eo pipefail

cd /opt/rtv-cases

# Recover from a previous deploy that left the working tree mid-merge
# (or with unmerged index entries from a partial reset). Without this,
# the next `git stash` silently no-ops (stash refuses unmerged paths)
# and `git pull` aborts with "Pulling is not possible because you have
# unmerged files" — every deploy hits the same wall.
#
# Three layers of recovery, in order:
#   1. Abort any in-progress merge (MERGE_HEAD set).
#   2. Abort any in-progress rebase (REBASE_HEAD / .git/rebase-{merge,apply}).
#   3. Sweep any remaining unmerged files via `git ls-files --unmerged`.
#
# For each unmerged path we take HEAD's version (`git checkout HEAD --`),
# which on a deploy is main. The per-host customizations in settings.py /
# .env are uncommitted local edits and get re-stashed by the regular
# stash/pop dance below regardless.

# 1) In-progress merge?
if [ -f .git/MERGE_HEAD ]; then
    echo "Aborting in-progress merge from previous deploy..."
    git merge --abort 2>/dev/null || true
fi

# 2) In-progress rebase?
if [ -f .git/REBASE_HEAD ] || [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then
    echo "Aborting in-progress rebase from previous deploy..."
    git rebase --abort 2>/dev/null || true
fi

# 3) Any leftover unmerged index entries (can exist even without the
#    MERGE_HEAD/REBASE_HEAD markers, e.g. after a partial `git reset`).
unmerged=$(git ls-files --unmerged 2>/dev/null | awk '{print $4}' | sort -u || true)
if [ -n "$unmerged" ]; then
    echo "Clearing unmerged files from previous deploy (taking HEAD's version):"
    echo "$unmerged" | sed 's/^/  /'
    echo "$unmerged" | xargs git checkout HEAD -- 2>/dev/null || true
    echo "$unmerged" | xargs git add 2>/dev/null || true
fi

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

# Install the version-controlled nginx site config from deploy/nginx/
# to /etc/nginx/sites-available/rtv-cases. Bootstrap pattern: pull the
# file from origin/main first so the host's working tree has it (same
# idea as the deploy.sh self-bootstrap in the workflow).
git checkout origin/main -- deploy/nginx/rtv-cases.conf
sudo install -m 644 "$PROJECT_ROOT/deploy/nginx/rtv-cases.conf" \
    /etc/nginx/sites-available/rtv-cases
sudo ln -sf /etc/nginx/sites-available/rtv-cases \
    /etc/nginx/sites-enabled/rtv-cases

# Restart the app services. This is not optional: both processes hold their
# build in memory, so without a restart the node service keeps emitting HTML
# that references the *previous* build's asset hashes, and every one of those
# assets 404s. Django likewise keeps running the old code.
sudo systemctl restart rtv-cases-backend
sudo systemctl restart rtv-cases-frontend

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
    entry=$(printf '%s' "$html" \
        | grep -o '[./]*_app/immutable/entry/start\.[A-Za-z0-9_-]*\.js' \
        | head -1)
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
