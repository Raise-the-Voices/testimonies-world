# Testimonies.world

> **Person-centered casework platform for people facing oppression** —
> enforced disappearances, arbitrary detention, restricted rights,
> statelessness, and more. Modeled after [shahit.biz][shahit], expanded
> globally. Operated by [Raise the Voices][rtv].

[shahit]: https://shahit.biz/
[rtv]: https://raisethevoices.org/

Testimonies.world documents individual cases of oppression and links them to
the advocacy actions taken on each person's behalf — so that no case is
forgotten, and a partial or uncertain report today can grow into a complete
record tomorrow.

---

## Contents

1. [Live demo](#live-demo)
2. [Stack at a glance](#stack-at-a-glance)
3. [Quick start](#quick-start)
4. [Repository layout](#repository-layout)
5. [Data model](#data-model)
6. [REST API surface](#rest-api-surface)
7. [Frontend routes](#frontend-routes)
8. [Roles & permissions](#roles--permissions)
9. [Privacy model](#privacy-model)
10. [Email & notifications](#email--notifications)
11. [Design system](#design-system)
12. [Development workflow](#development-workflow)
13. [Deployment](#deployment)
14. [Repository conventions](#repository-conventions)
15. [Further reading](#further-reading)
16. [Contributing](#contributing)

---

## Live demo

| Surface | URL |
|---|---|
| Public app | https://demos.linkedtrust.us/testimonies/ |
| Django admin | https://demos.linkedtrust.us/testimonies/admin/ |
| API root | https://demos.linkedtrust.us/testimonies/api/ |
| Production (live) | https://cases.raisethevoices.org |

Demo admin credentials (non-production):

```
user: admin
pass: tw-admin-2026
```

---

## Stack at a glance

| Layer | Tech | Notes |
|---|---|---|
| Frontend | **SvelteKit 2** + Svelte 5 (`adapter-node`) | TypeScript, Vite 7, design tokens in `app.css` |
| Backend | **Django 6.0** + **DRF 3.15** + **django-filter** + **django-allauth** | gunicorn in prod |
| Database | **PostgreSQL** (`testimonies_world`) | remote at `10.0.0.100:5432`, shared with other VM tenants |
| Auth | django-allauth (Google OAuth in production) | role info surfaced via `/api/session/` |
| Static assets | whiteNoise (Django) + nginx (frontend) | built `frontend/build/client/_app/` served at the doc root |
| CI / CD | GitHub Actions → `scripts/deploy.sh` | single-host prod, Ansible migration planned |

Dev port map:

| Service | Port |
|---|---|
| Django dev server | `8040` |
| SvelteKit dev server | `3040` (proxies `/api` → `:8040` via Vite) |
| SvelteKit prod server | `3000` (behind nginx) |
| Postgres | `5432` on VM `100` (remote) |

---

## Quick start

### Run it locally

```bash
# Backend (Django on :8040)
cd backend
source .venv/bin/activate           # or backend/.venv/bin/python ...
python manage.py migrate
python manage.py runserver 127.0.0.1:8040

# Frontend (SvelteKit on :3040) — in a second shell
cd frontend
npm install                          # first time / after package.json changes
PUBLIC_BASE_PATH=/testimonies npm run dev -- --host 0.0.0.0 --port 3040
```

The Vite dev server proxies `/api` → `http://localhost:8040/api`, so the
backend must be running first. For a different backend, set
`VITE_API_URL` in `frontend/.env` before `npm run dev`.

### Run both via systemd (on the demo VM)

```bash
sudo systemctl start tmp-testimonies-backend tmp-testimonies-frontend
sudo journalctl -u tmp-testimonies-backend -f
```

### First-time setup checklist

- [ ] `backend/.venv/` created and `pip install -r backend/requirements.txt`
- [ ] `backend/.env` populated from a teammate (DB creds, secret key, OAuth creds)
- [ ] `npm install` in `frontend/`
- [ ] Postgres reachable at `10.0.0.100:5432`, DB `testimonies_world` exists

---

## Repository layout

```
testimonies-world/
├── backend/                          Django project
│   ├── manage.py
│   ├── requirements.txt              asgiref, Django 6.0, allauth, DRF,
│   │                                 cors-headers, filter, pillow,
│   │                                 psycopg2-binary, python-decouple,
│   │                                 sqlparse, whitenoise
│   ├── .env                          Environment config (not in git)
│   ├── .venv/                        Python virtualenv (not in git)
│   │
│   ├── testimonies/                  Project package
│   │   ├── settings.py               Django settings + DRF + allauth wiring
│   │   ├── urls.py                   /api/* router + /api/session/ + /admin + /accounts
│   │   ├── asgi.py / wsgi.py
│   │
│   ├── cases/                        Person, Report, Media, CaseCategory,
│   │                                 FamilyRelationship, AuditLog
│   ├── casework/                     CaseworkRecord
│   ├── contacts/                     Contact (always-private)
│   └── sensitive_media/              Sensitive uploads (PRIVATE tier; not gitignored)
│
├── frontend/                         SvelteKit project
│   ├── src/
│   │   ├── routes/                   Pages (file-based routing — see below)
│   │   ├── lib/                      Components, stores, API client
│   │   ├── app.css                   Design system tokens (single source of truth)
│   │   ├── app.d.ts
│   │   └── hooks.server.ts
│   ├── static/                       Static assets
│   ├── svelte.config.js              adapter-node config
│   ├── vite.config.ts                dev proxy → :8040
│   ├── tsconfig.json
│   └── package.json
│
├── scripts/
│   └── deploy.sh                     Production deploy (tag + autostash + rsync +
│                                     systemctl restart + nginx reload + smoke test)
│
├── .github/
│   └── workflows/
│       └── deploy.yml                CI: triggers deploy on push to main
│
├── CLAUDE.md                         Project facts for Claude Code (project overlay)
├── SYSTEM_RULES.md                   Engineer-role protocol (workflow + safety)
└── README.md                         ← You are here
```

---

## Data model

The central entity is **`Person`**. Everything else hangs off a person
(or, for `Media` / `Report`, off a person or another report).

### `Person`

| Group | Fields |
|---|---|
| Identity | `name`, `legal_name`, `aliases`, `country`, `ethnicity`, `gender`, `date_of_birth` |
| Status | `current_status` ∈ {`detained`, `disappeared`, `restricted_movement`, `released`, `deceased`, `unknown`, `stateless`, `rights_restricted`} |
| Medical | `medical_status` ∈ {`unknown`, `healthy`, `health_concerns`, `critical`, `deceased`}; `medical_notes` (PRIVATE) |
| Location | `rough_location` (public), `precise_location` (PRIVATE), `last_known_date` |
| Narrative | `summary_narrative`, `profile_image` |
| Source | `authoritative_source`, `authoritative_url` (for cases imported from external databases) |
| Classification | `categories` (M2M `CaseCategory`), `quality_tier` ∈ {1, 2, 3}, `is_published` |
| Meta | `created_by`, `created_at`, `updated_at` |

### `Report` — chronological updates on a Person

| Group | Fields |
|---|---|
| Source | `source_type` ∈ {`firsthand`, `secondhand`, `news`, `document`}; `source_attribution` (public), `reporter_name` + `reporter_contact` (PRIVATE) |
| Dates | `date_start`, `date_end` (range or single date) |
| Location | `rough_location` (public), `precise_location` (PRIVATE) |
| Content | `narrative` (required), `suspected_reason`, `official_reason` |
| Visibility | `is_private` (hides entire report from unauthenticated users) |

### `Media` — attached to a Person or a Report

| Group | Fields |
|---|---|
| Source | `file` (upload) **or** `url` (external link); `media_type` ∈ {`photo`, `document`, `video`, `link`} |
| Access | `visibility` ∈ {`public`, `restricted`, `sensitive`} |
| Meta | `description` (≤500 chars), `uploaded_by`, `created_at` |

### Adjacent models

- **`CaseCategory`** — taxonomy many-to-many with `Person`
- **`FamilyRelationship`** — links two `Person` records (`parent`, `child`, `sibling`, `spouse`, `other`)
- **`CaseworkRecord`** — advocacy actions on a person (letters, campaigns, legal filings)
- **`Contact`** — people involved in cases; always private
- **`AuditLog`** — every access/edit of sensitive data is recorded (`viewed` / `downloaded` / `edited` / `deleted`)

---

## REST API surface

All endpoints are registered via DRF's `DefaultRouter` in `backend/testimonies/urls.py`.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/persons/` | List persons (filterable: `country`, `status`, `category`, `quality`, `gender`, `is_published`, `name__icontains`) |
| `GET` | `/api/persons/{id}/` | Person detail (read serializer uses `PersonDetailSerializer`) |
| `POST` / `PATCH` / `DELETE` | `/api/persons/{id}/` | Write (auth required) — `PersonWriteSerializer` |
| `GET` | `/api/persons/watchdog/` | Cases needing attention (stale + active) |
| `GET` | `/api/persons/statistics/` | Aggregate counts (used by home page + `/statistics`) |
| `GET` | `/api/persons/countries/` | Distinct countries with counts |
| `GET` / `POST` | `/api/reports/`, `/api/reports/{id}/` | Report CRUD |
| `GET` / `POST` | `/api/media/`, `/api/media/{id}/` | Media CRUD (visibility enforced server-side) |
| `GET` | `/api/categories/` | Read-only category list |
| `GET` / `POST` | `/api/relationships/`, `/api/relationships/{id}/` | Family relationships |
| `GET` / `POST` | `/api/casework/`, `/api/casework/{id}/` | Casework records |
| `GET` / `POST` | `/api/contacts/`, `/api/contacts/{id}/` | Contacts (always private) |
| `GET` | `/api/session/` | Current user info (groups, `is_staff`, email) — drives nav |
| — | `/admin/` | Django admin |
| — | `/accounts/` | django-allauth (Google OAuth + social account mgmt) |

**Country normalization** — the country dropdown collapses
`'Pakistan'` / `'PAKISTAN'` / `'pakistan'` to one canonical label, with
allowlisted multi-word / abbreviation forms (`USA`, `UAE`, `UK`, `DRC`,
`DPRK`, `South Korea`). Implemented in `cases.views._normalize_country`.

**Filtering** uses `django-filter`; the same `PersonFilter` powers the
`/persons` page facets and the API.

---

## Frontend routes

| Path | Page | Notes |
|---|---|---|
| `/` | Landing | Stats counters, intro, "Browse Cases" / "View Statistics" |
| `/persons` | Case list | Search, facets (country/status/category/quality), pagination |
| `/persons/[id]` | Case details | Unified design system: Reports accordion, Summary, Media, Sidebar metadata |
| `/persons/[id]/edit` | Edit person | Auth required (volunteer+) |
| `/persons/[id]/report` | Add report | Auth required (volunteer+) |
| `/submit` | Submit a case | Auth required (volunteer+) |
| `/statistics` | Aggregate statistics | Charts + breakdown by status / country |
| `/watchdog` | Watchdog | Cases needing attention (calls `/api/persons/watchdog/`) |
| `/casework` | Casework list | Auth required (advocate+) |
| `/casework/new` | New casework record | Auth required (advocate+) |
| `/contacts` | Contacts | Auth required (advocate+) |

The landing and Case Details are the most-trafficked surfaces; both have
been unified into a single design system — see below.

---

## Roles & permissions

Four tiers, in increasing privilege:

| Role | Capabilities |
|---|---|
| **Public** | Browse published persons + public reports + public media |
| **Volunteer** | All of Public + enter/edit reports, upload media |
| **Advocate** | All of Volunteer + casework records + contacts + restricted media |
| **Admin** | All of Advocate + sensitive media + audit logs + user mgmt |

Role enforcement lives in three layers:

1. **Django** — `is_authenticated` / `is_staff` / `is_superuser` checks in views.
2. **DRF** — `permission_classes` per viewset; private fields are stripped at the serializer level when the requester lacks the right group.
3. **Frontend** — nav items are gated by `isVolunteer()` / `isAdvocate()` from `$lib/session.ts`; the `/api/session/` response carries the user's groups.

Authentication in production uses **Google OAuth** via `django-allauth`.

---

## Privacy model

Three concentric layers of protection — implemented at every level of the stack:

### 1. Field-level (`PRIVATE` comment on Django model fields)

A field marked `# PRIVATE` is **omitted from the API response entirely** when
the requester lacks permission. Examples:

- `Person.precise_location`
- `Person.medical_notes`
- `Report.reporter_name`, `Report.reporter_contact`
- `Report.precise_location`
- `Contact.*` (all fields)

### 2. Record-level (`is_private`, `is_published`)

- `Report.is_private` — entire report is hidden from public listings.
- `Person.is_published` — entire person record is hidden from public listings.

### 3. Media tier (`Media.visibility`)

| Visibility | Who can access |
|---|---|
| `public` | Anyone |
| `restricted` | Authenticated users (volunteer+) |
| `sensitive` | Advocates + admins only |

Sensitive files are **always served through Django** (they're never exposed
at a direct URL); they live under `backend/sensitive_media/` (separate from
the public `backend/media/` directory) and require an authenticated advocate
or admin to retrieve.

Every access to sensitive data should be recorded in `AuditLog`
(`viewed` / `downloaded` / `edited` / `deleted`) with `user`, `target_type`,
`target_id`, and `ip_address`.

---

## Email & notifications

Casework actions (create, update, "marked done", "seen by") generate
both a Django in-app notification row and (by default) an email to
eligible advocates + staff, with a per-record 24h anti-spam rule
described inline in [`backend/casework/notifications.py`](backend/casework/notifications.py).
The dispatch is wrapped in `transaction.on_commit` and pushed onto a
daemon thread so the HTTP request never blocks on the SMTP handshake.

### Provider: Migadu

Production routes email through **Migadu**, an external transactional
mailer chosen over a self-hosted Postfix to avoid deliverability /
spam-classification risk on our IP range. See `backend/.env.example` for
the canonical env var template.

| Setting | Default | Purpose |
|---|---|---|
| `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` | Dev prints emails to stdout. Set to `django.core.mail.backends.smtp.EmailBackend` in prod. |
| `EMAIL_HOST` | `''` | `smtp.migadu.com` in prod |
| `EMAIL_PORT` | `587` | `465` recommended for Migadu (implicit SSL) |
| `EMAIL_USE_TLS` | `True` | STARTTLS — pick *one* of `EMAIL_USE_TLS` / `EMAIL_USE_SSL` |
| `EMAIL_USE_SSL` | `False` | Implicit TLS (port 465) |
| `EMAIL_HOST_USER` | `''` | Full mailbox email address (e.g. `noreply@<migadu-domain>`) |
| `EMAIL_HOST_PASSWORD` | `''` | Mailbox password — never commit |
| `EMAIL_TIMEOUT` | `15` | Seconds; defensive cap on SMTP handshakes |
| `DEFAULT_FROM_EMAIL` | `Testimonies.world <noreply@linkedtrust.us>` | The from-address must live on the same domain as the Migadu mailbox or recipients see "Sent on behalf of" and it looks phishy. |
| `SITE_URL` | `https://demos.linkedtrust.us/testimonies` | Used for in-email links to records |

### Migrating the from-address

If the production mailbox is set up on a different domain than
`linkedtrust.us`, both `EMAIL_HOST_USER` and `DEFAULT_FROM_EMAIL` must
be updated together — keep them in lock-step or recipients will see a
mismatched "on behalf of" stamp that looks like a phishing attempt.

### Testing locally

In dev, `EMAIL_BACKEND` defaults to the console backend — no setup
needed. Trigger a casework create/update as an advocate and watch stdout
for a `Subject:` line. The Django test runner overrides
`EMAIL_BACKEND` to `locmem`, so unit tests can assert on
`mail.outbox` (see `casework/tests.py`).

### Required DNS for prod

When the Migadu mailbox domain goes live, the ops team needs to publish
SPF + DKIM + DMARC records (Migadu provides them in the admin panel).
Without these, major receivers (Gmail, Outlook, etc.) will silently
deliver the notification to spam.

---

## Design system

The Case Details page (the most-trafficked surface) and the landing page
share a single, unified design system. The single source of truth is
**[`frontend/src/app.css`](frontend/src/app.css)**, which defines:

| Token | Value | Used by |
|---|---|---|
| `--color-primary` | `#25646a` | Buttons, headings, stat numbers |
| `--color-primary-light` | `#477c81` | Hover state on primary surfaces |
| `--color-bg` | `#f4f7f6` | Page background |
| `--color-bg-white` | `#fff` | Card surfaces |
| `--color-text` | `#1a1a1a` | Body copy |
| `--color-text-muted` | `#666` | Secondary copy, labels |
| `--color-border-light` | `#e2e8f0` | Card borders |
| `--radius-card` | `8px` | All cards |
| `--shadow-card` | `0 1px 2px rgba(0,0,0,.04), 0 1px 3px rgba(0,0,0,.06)` | Default elevation |
| `--shadow-card-hover` | `0 4px 12px rgba(0,0,0,.08), 0 2px 4px rgba(0,0,0,.04)` | Hover elevation |
| `--transition-card` | `0.2s ease` | All card transitions |
| `--card-padding` | `1.25rem 1.5rem` | Standard card padding |

**Animations** — `@keyframes fadeSlideUp` (and `fadeSlideUpSmall`) are reused
by the Summary, Media, Reports accordion, Sidebar, and now the landing page
cards, with staggered delays on repeated-item lists (`fade-in-stagger`).
All animations honor `prefers-reduced-motion: reduce`.

The full per-component polish history + verification checklists live in
[`frontend/README.md`](frontend/README.md).

---

## Development workflow

### Branch & commit conventions

- **Feature branches** — never work on `main` directly. Branch names:
  `feat/<feature>`, `fix/<issue>`, `chore/<task>`, `docs/<doc>`.
- **Conventional commits** — `feat:`, `fix:`, `docs:`, `refactor:`,
  `chore:`, optionally scoped: `feat(persons): …`.
- **PRs are required** for merge into `main`. Delete the branch after
  merge (this repo convention keeps the branch list short).
- **Build before pushing** to avoid CI failures.

### Command cheat sheet

```bash
# Frontend
cd frontend
npm install                # first time / after package.json changes
npm run dev                # vite dev (default :5173)
npm run dev -- --host 0.0.0.0 --port 3040
PUBLIC_BASE_PATH=/testimonies npm run dev -- --host 0.0.0.0 --port 3040
npm run check              # type-check (svelte-check)
npm run test               # vitest unit tests
npm run build              # production build → ./build/
npm run preview            # preview the production build locally

# Backend
cd backend
source .venv/bin/activate
python manage.py runserver 127.0.0.1:8040
python manage.py makemigrations
python manage.py migrate
python manage.py test
python manage.py createsuperuser
```

### Pre-deploy checklist (SvelteKit)

Per `SYSTEM_RULES.md` §3, every production build **must**:

1. Use `PUBLIC_BASE_PATH=""` and
   `ORIGIN=https://cases.raisethevoices.org` (or the live equivalent) so
   path-drifting doesn't 404 assets.
2. Sync built assets to the nginx doc root:
   `rsync build/client/_app/ /var/www/cases/_app/`.
3. **Restart the Node server process.** It caches HTML in memory and
   will keep serving stale asset hashes otherwise. The deploy script
   (`scripts/deploy.sh`) does this defensively, with a `nohup` fallback
   if systemd fails.

### Common gotchas

- **Stale asset 404s after deploy** — the Node server is still caching
  the previous build. Restart it (`sudo systemctl restart
  rtv-cases-frontend`).
- **Path-drifted assets in subpath deploys** — `PUBLIC_BASE_PATH` was
  non-empty during build. Rebuild with `PUBLIC_BASE_PATH=""` for the
  root domain, or with `/testimonies` for the demo subpath.
- **Empty DB on first run** — `python manage.py migrate` against the
  remote PG; the `getStatistics()` call on the landing page handles an
  empty DB by returning `{ total: 0 }` and the stats bar is suppressed.

---

## Deployment

Single-host production deployment, orchestrated by `scripts/deploy.sh`:

1. Tag the current commit for rollback.
2. Autostash local-only files (`.env`, `settings.py`).
3. `git fetch + reset --hard origin/main` (handles force-push cleanly).
4. `pip install -r requirements.txt`, `python manage.py migrate`,
   `collectstatic`.
5. `npm ci --omit=dev && npm run build` for the frontend.
6. Symlink workaround for `@sveltejs/adapter-node 5.5.x` server-asset layout.
7. `rsync build/client/` to `/var/www/cases/`.
8. `systemctl restart rtv-cases-backend rtv-cases-frontend` with
   `reset-failed` + nohup fallback.
9. `nginx -t && nginx -s reload`.
10. **Smoke test**: fetch the homepage, extract the entry-script asset
    hash from the rendered HTML, confirm that exact asset returns 200
    AND the API returns 200. Retries up to 10× with 3 s backoff.

CI (`.github/workflows/deploy.yml`) triggers this on push to `main`.

Future direction: convert to an **Ansible playbook** (referenced in
`CLAUDE.md`, not yet built).

---

## Repository conventions

This repo has two policy documents that are **read by Claude Code sessions**
on every interaction:

- **[`CLAUDE.md`](CLAUDE.md)** — project facts (stack, dev URLs, commands,
  data model, permissions, privacy). Read this first.
- **[`SYSTEM_RULES.md`](SYSTEM_RULES.md)** — engineer-role protocol: diff
  dumps, git/PR workflow, SvelteKit deployment safety, scope discipline.
  Read this before any code change.

Both are group-writable. Update them when the project changes; new
Claude sessions will pick up the changes immediately.

---

## Further reading

| Doc | Purpose |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Concise project facts for Claude Code |
| [`SYSTEM_RULES.md`](SYSTEM_RULES.md) | Engineer-role protocol (workflow + safety) |
| [`frontend/README.md`](frontend/README.md) | Design system reference + per-component polish docs |
| [`scripts/deploy.sh`](scripts/deploy.sh) | Production deploy script (heavily commented) |
| [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) | CI pipeline |
| [Testimonies.world demo](https://demos.linkedtrust.us/testimonies/) | Live running app |
| [Testimonies.world prod](https://cases.raisethevoices.org) | Production |
| [shahit.biz](https://shahit.biz/) | Inspiration / model for case structure |
| [Raise the Voices](https://raisethevoices.org/) | Parent organization |

---

## Contributing

This project follows the `SYSTEM_RULES.md` discipline. The short version:

- **Plan** complex work before implementing.
- **Diff + why** for every change.
- **Conventional commits** on a **feature branch**.
- **PR** for merge to `main`.
- **Strict scope** — don't bundle unrelated changes; flag follow-ups separately.
- **Production builds**: `PUBLIC_BASE_PATH=""` + `ORIGIN` set + restart
  the Node server.
- **No secrets in diffs or chat.** If a secret leaks, alert immediately
  and follow the rotation steps in `SYSTEM_RULES.md` §5.

When in doubt, read `CLAUDE.md` + `SYSTEM_RULES.md` first.