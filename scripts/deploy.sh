#!/bin/bash
set -e

cd /opt/rtv-cases

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

# Sync the static asset bundle into the nginx document root so the
# newly-hashed CSS and JS files actually become reachable on the
# public site. The previous bundle is moved aside as `_app.prev` for
# a one-command rollback if this deploy turns out to be broken:
#   sudo mv /var/www/cases/_app.prev /var/www/cases/_app
#   sudo nginx -s reload
sudo mkdir -p /var/www/cases
if [ -d /var/www/cases/_app ]; then
    sudo rm -rf /var/www/cases/_app.prev
    sudo mv /var/www/cases/_app /var/www/cases/_app.prev
fi
sudo rsync -a --delete build/client/_app/ /var/www/cases/_app/
sudo chown -R www-data:www-data /var/www/cases
sudo chmod -R u+rwX,g+rX,o+rX /var/www/cases

# Reload nginx so it picks up the new assets without dropping
# connections. The systemctl path is kept as a fallback for hosts that
# run nginx under systemd; the explicit nginx -s reload works on any
# nginx install.
if command -v nginx >/dev/null 2>&1; then
    sudo nginx -t && sudo nginx -s reload
else
    sudo systemctl reload nginx || sudo systemctl restart nginx
fi

echo 'Deploy complete'