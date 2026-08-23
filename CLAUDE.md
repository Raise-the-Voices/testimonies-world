# Testimonies.world

Person-centered casework platform for people facing oppression — enforced disappearances, arbitrary detention, restricted rights, statelessness, and more. Modeled after shahit.biz, expanded globally.

## Stack
- **Backend**: Django 6.0 + DRF, gunicorn on :8040
- **Frontend**: SvelteKit (adapter-node) on :3040
- **Database**: PostgreSQL `testimonies_world` on VM 100 (10.0.0.100:5432)
- **Deployment**: Ansible to dedicated VM (TBD)

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
- `Media.visibility` controls access tier (`public` / `restricted` / `sensitive`):
  - Files are uploaded into `MEDIA_ROOT/{visibility}/` by `cases.storage.VisibilityRouterStorage`
    via the `upload_to` callable `cases.models._media_upload_to`.
  - Downloads go through `cases.views.MediaDownloadView` (route `/media/<path>`),
    which resolves the path to a `Media` row, enforces visibility, and writes
    an `AuditLog(action=DOWNLOADED)` row for every sensitive fetch.
  - **Production nginx MUST proxy `/media/` to Django (gunicorn).** It must not
    serve files directly from disk — doing so bypasses the permission gate.
    The view replaces Django's `static()` helper (which was removed in the same
    commit because it served files with no check).
  - Visibility rules (mirrors `MediaViewSet.get_queryset`):
    - `public`      — anyone, including anonymous
    - `restricted`  — any authenticated user
    - `sensitive`   — `is_staff=True` OR member of `Advocate` / `Admin` group
- Existing media uploaded before this change still live under the old
  flat `MEDIA_ROOT/uploads/` prefix; they remain reachable only until their
  `Media.file` row is updated to the new `{visibility}/` layout. A data
  migration can re-key old paths if needed.
- Sensitive files served through Django, never direct URL

## Error handling
- `testimonies/urls.py` defines `handler404` / `handler500` so unhandled
  errors don't leak Django's default HTML pages (which expose template
  variables, request paths, and (in `DEBUG=True`) full stack traces).
- `/api/*` paths return JSON: `{"detail": "...", "path": "..."}` for 404,
  `{"detail": "Internal server error"}` for 500. Stack traces are
  **never** included in the 500 body — they go to the logs (see `LOGGING`).
- Everything else (`/admin/`, `/accounts/`, the SvelteKit frontend, etc.)
  keeps Django's default HTML behavior so admin and browser-driven flows
  work unchanged.
- Custom handlers are tested at `backend/testimonies/tests.py` with
  `override_settings(DEBUG=False)` since Django only invokes them when
  `DEBUG=False`.

## Production settings
- `backend/testimonies/settings.py` is the base module. Defaults are
  dev-friendly but `DEBUG=False` raises `ImproperlyConfigured` if
  `SECRET_KEY` is empty or `ALLOWED_HOSTS` contains `*` — fails loud
  rather than silently insecure.
- `backend/testimonies/settings_prod.py` is the **strict production
  module**. Import with `DJANGO_SETTINGS_MODULE=testimonies.settings_prod`
  in the gunicorn invocation (or systemd unit, or wherever the prod
  process is launched). It forces `DEBUG=False`, requires `ALLOWED_HOSTS`
  to be set explicitly (no default), and asserts the secure-cookie /
  HSTS / `SECURE_PROXY_SSL_HEADER` block.
- Local dev keeps using `testimonies.settings`; values come from
  `backend/.env` (auto-read by `python-decouple` when the cwd is
  `backend/`).
- Required env vars in production: `SECRET_KEY` (strong random),
  `ALLOWED_HOSTS` (CSV, no wildcards), `PG_*`, plus `DJANGO_SETTINGS_MODULE=testimonies.settings_prod`.
- Generate a strong `SECRET_KEY` with
  `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`.
- `.gitignore` ignores `backend/.env`, `**/.env`, `.env`, `.env.*` —
  do not commit secrets even if the file was renamed.

## Nginx
- `deploy/nginx/rtv-cases.conf` is the version-controlled site config.
  `scripts/deploy.sh` rsyncs it to `/etc/nginx/sites-available/rtv-cases`
  on every deploy (same bootstrap pattern as `scripts/deploy.sh` itself),
  then runs `nginx -t && nginx -s reload`.
- **Media protection** uses `auth_request`: nginx sends an internal
  sub-request to Django's `/media/_auth_check` (handled by
  `cases.views.media_auth_check`) which returns 200 (allowed) or 403
  (denied). On 200, nginx serves the file body from
  `MEDIA_ROOT/<visibility>/` directly via `alias` — the bytes
  never traverse Django.
- The previous `MediaDownloadView` stays as a safety net for direct
  Django access (local dev, when nginx is bypassed).
- Validate the config locally before merging:
  `sudo nginx -t -c <(echo "events{}http{include $(pwd)/deploy/nginx/rtv-cases.conf;}")`.
