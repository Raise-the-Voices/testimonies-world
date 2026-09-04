# Testimonies.world

Person-centered casework platform for people facing oppression — enforced disappearances, arbitrary detention, restricted rights, statelessness, and more. Modeled after shahit.biz, expanded globally.

## Stack
- **Backend**: Django 6.0 + DRF, gunicorn on :8040
- **Frontend**: SvelteKit (adapter-node) on :3040
- **Database**: PostgreSQL `testimonies_world` on VM 100 (10.0.0.100:5432)
- **Deployment**: Ansible to dedicated VM (TBD)

## Backup policy
- **RPO (Recovery Point Objective)**: 24 hours — `rtv-cases-db-backup.timer` runs `pg_dump` daily at 03:00 UTC; `Persistent=true` on the timer catches up missed runs after VM downtime.
- **RTO (Recovery Time Objective)**: ~30 minutes — restore is `pg_restore -d testimonies_world db-<timestamp>.sql.zst`. Custom-format dumps support parallel restore if the dataset grows.
- **Retention**: 30 days, in `/var/backups/rtv-cases/db-*.sql.zst` (pruned by `mtime +30` on every run).
- **Verify**: every successful backup is sanity-checked with `pg_restore -l` (TOC validation) — silent corruption would otherwise pass the size check.
- **Audit**: the script logs every run to journald via `StandardOutput=journal` on the unit. Check `journalctl -u rtv-cases-db-backup.service --since='-7 days'`.

## Dev access
- URL: `demos.linkedtrust.us/testimonies/`
- Django admin: `demos.linkedtrust.us/testimonies/admin/` (admin / tw-admin-2026)
- API root: `demos.linkedtrust.us/testimonies/api/`

## Project structure
```
backend/               Django project
  testimonies/         Settings, URLs, WSGI
  cases/               Person, Report, Media, CaseCategory, FamilyRelationship, AuditLog
  casework/            CaseworkRecord
  contacts/            Contact
  .venv/               Python virtualenv
  .env                 Environment config (not in git)
frontend/              SvelteKit project
  src/routes/          Pages
  src/lib/             Components, stores, API client
ansible/               Deployment playbooks (TBD)
```

## Key commands
```bash
# Backend
cd /opt/shared/repos/testimonies-world
backend/.venv/bin/python backend/manage.py runserver 127.0.0.1:8040
backend/.venv/bin/python backend/manage.py makemigrations
backend/.venv/bin/python backend/manage.py migrate

# Frontend
cd /opt/shared/repos/testimonies-world/frontend
PUBLIC_BASE_PATH=/testimonies npm run dev -- --host 0.0.0.0 --port 3040

# Both via systemd
sudo systemctl start tmp-testimonies-backend tmp-testimonies-frontend
```

## Data model
- **Person**: the central record — name, country, status, medical status, location (rough=public, precise=private)
- **Report**: chronological updates on a person — source type, narrative, suspected/official reason, privacy flags
- **Media**: files/links with 3 visibility tiers (public, restricted, sensitive)
- **CaseworkRecord**: advocacy actions linked to persons
- **Contact**: people involved in cases (always private, access-controlled)
- **AuditLog**: tracks access to sensitive data

## Permissions
- Public: browse published persons, public reports/media
- Volunteer: enter/edit reports, upload media
- Advocate: casework, contacts, restricted media
- Admin: everything including sensitive media and audit logs

## Privacy model
- Fields marked PRIVATE in models are excluded from public API responses
- `is_private` on Report hides entire report from unauthenticated users
- Media.visibility controls access tier
- Sensitive files served through Django, never direct URL
