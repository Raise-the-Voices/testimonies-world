#!/bin/bash
set -eo pipefail

cd /opt/rtv-cases
PROJECT_ROOT="$(pwd)"   # Used by the nohup fallbacks below to return here
                        # after `cd`ing into backend/ or frontend/.

# Mark the deploy checkout as a safe.directory for whatever user the
# appleboy/ssh-action runs as. Git 2.35.2+ refuses to operate on a
# repo owned by a different UID unless explicitly allowlisted — the
# SSH-action user (typically `runner` or `deploy`) doesn't own
# /opt/rtv-cases on prod, so `git fetch`/`git reset` would otherwise
# fail with "detected dubious ownership" and the deploy aborts in 1s
# (run #216, 2026-09-21). Targeted path instead of `*` keeps the
# allowlist as narrow as possible.
git config --global --add safe.directory /opt/rtv-cases

SITE="https://cases.raisethevoices.org"

# --- Ensure Node >= 22.18.0 is available before `npm ci` ---
# orval@7.21.0 is a devDependency, but `npm ci --omit=dev` on npm 10.x
# still validates engine metadata for ALL lockfile entries during the
# resolution phase, before --omit is applied. With engine-strict=true
# in frontend/.npmrc, this means a target VM with Node 20 aborts the
# deploy even though orval is never executed here (`npm run build` is
# just `vite build`). The CI fix in commit 4d27f0d bumped the runner to
# Node 22; this block brings the deploy target into the same state.
#
# Idempotent: if node is already >=22.18.0, do nothing. Otherwise
# install Node 22 LTS via NodeSource (apt-based, requires sudo).
# NodeSource is the only channel that ships Node 22 on Ubuntu 24.04 —
# the universe `nodejs` package is still on Node 20 LTS.
if command -v node >/dev/null 2>&1; then
    current_node=$(node -v 2>/dev/null | sed 's/^v//' || echo "0")
else
    current_node="0"
fi
required_major=22
required_minor=18
node_major=$(printf '%s' "$current_node" | cut -d. -f1)
node_minor=$(printf '%s' "$current_node" | cut -d. -f2)
if [ "${node_major:-0}" -lt "$required_major" ] \
   || { [ "${node_major:-0}" -eq "$required_major" ] && [ "${node_minor:-0}" -lt "$required_minor" ]; }; then
    echo "Node ${current_node:-missing} is below ${required_major}.${required_minor}; installing Node ${required_major} LTS via NodeSource."
    # Pin the distro so the bootstrap script picks the right repo even
    # if $lsb_release is unavailable (e.g. inside containers). The
    # setup_22.x script is idempotent — re-running on an already-pinned
    # host is a no-op aside from a `Hit:` apt line.
    sudo -E bash -c '
        if ! command -v node >/dev/null 2>&1 || [ "$(node -v | sed "s/^v//" | cut -d. -f1)" -lt 22 ]; then
            curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
            apt-get install -y nodejs
        fi
    '
    # Refresh PATH so the just-installed nodejs is picked up by the
    # `npm ci` later in this script. /usr/bin is already on PATH, but
    # NodeSource also installs into /etc/profile.d and we want the new
    # /usr/bin/node to win regardless of how the ssh-action injected
    # the original PATH.
    hash -r
    if ! command -v node >/dev/null 2>&1 || [ "$(node -v | sed 's/^v//' | cut -d. -f1)" -lt 22 ]; then
        echo "DEPLOY FAILED: NodeSource bootstrap did not yield Node >=22 on PATH ($PATH)" >&2
        exit 1
    fi
    echo "Node bootstrap complete: $(node -v), npm $(npm -v)"
else
    echo "Node $(node -v) satisfies >=${required_major}.${required_minor}; no upgrade needed."
fi

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
# Auto-recovery for settings.py only: when the hotfix (commit
# bff87fd) lifted LOGGING/CACHES/Sentry out of settings.py into
# testimonies/ops.py, the VM's locally-tweaked settings.py could
# no longer auto-merge with the new minimal settings.py. Take
# main's version (theirs) and warn the operator — any
# per-host setting the operator wants must be in .env (which is
# gitignored), not settings.py. The .env recovery (manual)
# stays as the fallback.
if ! git stash pop; then
    # `git stash pop` returns non-zero in two cases:
    #   1. There's no stash to pop ("No stash entries found.")
    #      The VM had nothing to autostash, so this is a no-op —
    #      the deploy can continue with main's tree.
    #   2. The pop hit a real conflict. Auto-recover if it's the
    #      known-safe settings.py-only kind, otherwise bail.
    conflicted=$(git diff --name-only --diff-filter=U 2>/dev/null || true)
    if [ -z "$conflicted" ]; then
        # No unmerged paths = no real conflict. The non-zero exit
        # was "no stash to pop", which is fine — the VM had no
        # local customizations to preserve.
        echo "deploy.sh: no stash to pop — continuing." >&2
    elif [ "$(echo "$conflicted" | wc -l)" = "1" ] && [ "$conflicted" = "backend/testimonies/settings.py" ]; then
        # AUTO-RECOVERY for the known settings.py-only path. The
        # hotfix (commit bff87fd) lifted LOGGING/CACHES/Sentry
        # out of settings.py into testimonies/ops.py, so the VM's
        # locally-tweaked settings.py can't auto-merge with the
        # new minimal settings.py. Take main's version and warn the
        # operator — per-host tweaks should be in .env anyway.
        echo "deploy.sh: auto-resolving settings.py conflict by taking main's version." >&2
        echo "  (per-host tweaks should be in backend/.env, which is gitignored.)" >&2
        # In `git stash pop`, --ours = HEAD/main (the new minimal
        # settings.py that uses ops.py), --theirs = the stash (the
        # old inline-LOGGING version). We want main's version.
        git checkout --ours backend/testimonies/settings.py
        # Mark the file resolved and finish the merge. The
        # remaining bits of the stash (if any) drop silently —
        # we only care about .env and the deploy proceeds with
        # main's settings.py.
        git add backend/testimonies/settings.py
        git stash drop || true
    else
        echo "DEPLOY FAILED: 'git stash pop' had conflicts - refusing to deploy half-merged code." >&2
        echo "Conflicted paths:" >&2
        echo "$conflicted" | sed 's/^/  /' >&2
        echo "Inspect with: git status" >&2
        echo "Recovery:  git checkout --theirs backend/.env && git stash drop && bash scripts/deploy.sh" >&2
        exit 1
    fi
fi

# Backend
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
sudo rsync -a --delete build/client/testimonies/ /var/www/cases/
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
# Two checks in series: systemd says active AND :3000 actually responds.
# We do NOT trust a `curl :3000` test alone — a stale node from a previous
# deploy can satisfy it, masking a missed restart. The smoke test below
# catches stale-node + fresh-bundle mismatches at the very end.
#
# Run as the deploying user (who has read access to /opt/rtv-cases/frontend).
# Don't `sudo -u deploy` — that user may not have read access on this
# host and the failure is silent (we hit this on 2026-09-21).
frontend_up=0
if sudo systemctl is-active --quiet rtv-cases-frontend 2>/dev/null \
   && curl -s -o /dev/null --max-time 2 http://127.0.0.1:3000/; then
    frontend_up=1
fi
if [ "$frontend_up" != 1 ]; then
    echo "  systemd did not bring up the frontend; restarting node directly"

    # Kill any stragglers from previous deploys — must do this BEFORE the
    # :3000 reachability check below, otherwise a stale node satisfies it.
    pkill -f 'node.*build/index' 2>/dev/null || true
    sleep 1

    cd /opt/rtv-cases/frontend
    nohup env PORT="${PORT:-3000}" HOST=127.0.0.1 \
        PUBLIC_BASE_PATH=/testimonies \
        ORIGIN=https://cases.raisethevoices.org \
        node build/index.js > /tmp/cases-frontend.log 2>&1 &
    disown

    sleep 3
    if curl -s -o /dev/null --max-time 3 http://127.0.0.1:3000/; then
        echo "  fallback node up on :3000 (PID=$(pgrep -f 'node.*build/index' | head -1))"
    else
        echo "  ERROR: fallback node did not bind :3000" >&2
        echo "  See /tmp/cases-frontend.log:" >&2
        tail -20 /tmp/cases-frontend.log >&2 2>/dev/null || true
        exit 1
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

# Smoke test. Verifies five things atomically — each catches a different
# failure mode we hit on 2026-09-21:
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
# All six must pass on the same attempt, otherwise the deploy is rejected
# (the script exits 1 and the operator must roll back to the last good
# deploy-* — see the "Roll back" line at the bottom).

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
