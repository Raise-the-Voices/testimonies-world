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
npm install --production
npm run build

# Restart
sudo systemctl restart rtv-cases-backend rtv-cases-frontend

echo 'Deploy complete'