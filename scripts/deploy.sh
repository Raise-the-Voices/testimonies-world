#!/bin/bash
set -e

cd /opt/rtv-cases

# Tag before deploy for rollback
git tag deploy-$(date +%Y%m%d-%H%M%S)

# Pull latest
git pull origin main

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