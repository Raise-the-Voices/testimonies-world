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
  cases/               Person, Report, Media, CaseCategory, FamilyRelationship,
                       AuditLog, Testimonial, TestimonialTag
  cases/testimonials/  Testimonials subpackage — encryption.py, permissions.py,
                       serializers.py, views.py, export.py, tests.py,
                       export_schema.json
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
- **Testimonial** + **TestimonialTag**: publication-facing wrappers around cases (separate from raw casework). See "Testimonials" below.

## Permissions
- Public: browse published persons, public reports/media
- Volunteer: enter/edit reports, upload media, **submit testimonial drafts**
- Advocate: casework, contacts, restricted media, **review / publish testimonials, decrypt source identities**
- Admin: everything including sensitive media and audit logs

## Privacy model
- Fields marked PRIVATE in models are excluded from public API responses
- `is_private` on Report hides entire report from unauthenticated users
- Media.visibility controls access tier
- Sensitive files served through Django, never direct URL

## Testimonials

Testimonials are publication artifacts (separate from casework) that
present case narratives for public / website / partner use. They have
their own lifecycle, encryption posture, and export contract.

### Encryption

The `source` and `precise_location` columns are field-level-encrypted
via Fernet (AES-128-CBC + HMAC). Key in `settings.TESTIMONIALS_FERNET_KEY`
as urlsafe-base64(32 bytes).

```bash
# Generate a production key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Place in /etc/testimonies-world/testimonials.key (mode 0600)
# Reference from the gunicorn systemd unit's EnvironmentFile=
```

Local dev with `DEBUG=True` falls back to a hardcoded test key in
`cases/testimonials/encryption.py` (`TESTIMONIALS_DEV_FALLBACK_KEY`) and
emits a one-shot `RuntimeWarning` at first use. Production must set the
real key — `ImproperlyConfigured` is raised if `DEBUG=False` and no key
is configured.

### Workflow

```
DRAFT ──submit──> UNDER_REVIEW ──approve──> APPROVED ──publish──> PUBLISHED
                     │                                               
                     └──reject──> REJECTED ──edit──> DRAFT           
PUBLISHED ──archive──> ARCHIVED
```

Only Advocate / Admin can approve, reject, publish, or archive —
volunteers submit drafts and wait. Every transition writes an
`AuditLog` row with `target_type='testimonial'`.

### Schema versioning

`Testimonial.schema_version` is a `PositiveSmallIntegerField=1` that
pins the export contract. **Bump manually** when changing
`TestimonialExportSerializer` or `EXPORT_SCHEMA`. Bumps must happen
atomically with:

1. Update `TestimonialExportSerializer.Meta.fields` in `cases/testimonials/export.py`.
2. Update the matching JSON Schema at `$id` ...v{N}.json.
3. Add a README / CLAUDE.md changelog entry.
4. Re-export any downstream consumers pinned to the previous
   `$id` (they'll start failing validation).

The first version is **v1** and is current as of the initial
testimonials rollout. The JSON Schema lives at:
```
backend/cases/testimonials/export_schema.json
```
The on-disk JSON Schema and the Python `EXPORT_SCHEMA` dict must
match — `cases/testimonials/tests.py` pins this contract via
`SchemaVersionPinTests`.

### Endpoints

```
GET    /api/testimonials/                 — public list (PUBLISHED only for anon)
GET    /api/testimonials/{id}/           — public detail
POST   /api/testimonials/                — create draft (auth required)
PATCH  /api/testimonials/{id}/           — update own draft (auth)
POST   /api/testimonials/{id}/submit/    — draft → under_review
POST   /api/testimonials/{id}/approve/   — under_review → approved (Advocate+)
POST   /api/testimonials/{id}/reject/    — under_review → rejected (Advocate+)
POST   /api/testimonials/{id}/publish/   — approved → published (Advocate+)
POST   /api/testimonials/{id}/archive/   — published → archived (Advocate+)
GET    /api/testimonials/{id}/source/         — decrypted source (Advocate+)
GET    /api/testimonials/{id}/precise_location/  — decrypted precise location (Advocate+)
```

The `/source/` and `/precise_location/` endpoints NEVER appear in the
public serializer; they're separate routes so the URL itself is the
security boundary. Every read leaves an `AuditLog` row.
