# Testimonies.world

> Person-centered casework platform for people facing oppression —
> enforced disappearances, arbitrary detention, restricted rights,
> statelessness, and more. Modeled after [shahit.biz][shahit], expanded globally.

[shahit]: https://shahit.biz/

This repository is the **single source of truth** for the platform: a Django
backend + SvelteKit frontend, deployed together.

---

## Table of contents

1. [What it is](#what-it-is)
2. [Quick start](#quick-start)
3. [Architecture & stack](#architecture--stack)
4. [Project layout](#project-layout)
5. [Data model](#data-model)
6. [Roles & permissions](#roles--permissions)
7. [Privacy model](#privacy-model)
8. [Design system & UI](#design-system--ui)
9. [Development workflow](#development-workflow)
10. [Deployment](#deployment)
11. [Repository conventions](#repository-conventions)
12. [Further reading](#further-reading)

---

## What it is

Testimonies.world documents individual cases of oppression and links them to
the advocacy actions taken on each person's behalf. Each person has:

- A **profile** with identifying metadata (name, country, location, status,
  medical condition).
- A **timeline** of dated reports from various sources (firsthand testimony,
  news, documents).
- **Media** (photos, documents, videos, external links) attached at either
  the person or report level, with three visibility tiers.
- **Family relationships** to other documented persons.
- **Casework records** of advocacy actions (letters, campaigns, legal filings).
- **Contacts** — always-private notes about people involved in the case.

---

## Quick start

### Access the running demo

| Surface | URL |
|---|---|
| App | https://demos.linkedtrust.us/testimonies/ |
| Django admin | https://demos.linkedtrust.us/testimonies/admin/ |
| API root | https://demos.linkedtrust.us/testimonies/api/ |

Django admin credentials (demo only):

```
user: admin
pass: tw-admin-2026
```

### Run it locally

```bash
# Backend (Django on :8040)
cd /opt/shared/repos/testimonies-world
backend/.venv/bin/python backend/manage.py runserver 127.0.0.1:8040

# Backend migrations
backend/.venv/bin/python backend/manage.py makemigrations
backend/.venv/bin/python backend/manage.py migrate

# Frontend (SvelteKit on :3040, dev proxy to backend)
cd /opt/shared/repos/testimonies-world/frontend
PUBLIC_BASE_PATH=/testimonies npm run dev -- --host 0.0.0.0 --port 3040

# Both via systemd (if installed on the host)
sudo systemctl start tmp-testimonies-backend tmp-testimonies-frontend
```

The dev frontend proxies API calls to `localhost:8000` — start the backend
first.

---

## Architecture & stack

| Layer | Tech | Where it runs |
|---|---|---|
| Frontend | **SvelteKit** (`adapter-node`) | `:3040` (dev) / port `3000` behind nginx (prod) |
| Backend | **Django 6.0** + **Django REST Framework**, gunicorn | `:8040` |
| Database | **PostgreSQL** `testimonies_world` | VM `100` (`10.0.0.100:5432`) — remote, shared |
| Auth | django-allauth (Google OAuth in production) | — |
| Static assets | whiteNoise (Django) + nginx (frontend) | nginx doc roots `/var/www/cases/` and `/var/www/marten/`-style paths |
| Deployment | **Ansible** to a dedicated VM (TBD) | `scripts/deploy.sh` runs in the meantime |

Production URL: **https://cases.raisethevoices.org**

---

## Project layout

```
testimonies-world/
├── backend/                  Django project
│   ├── testimonies/          Settings, URLs, WSGI
│   ├── cases/                Person, Report, Media, CaseCategory,
│   │                         FamilyRelationship, AuditLog
│   ├── casework/             CaseworkRecord
│   ├── contacts/             Contact
│   ├── .venv/                Python virtualenv (not in git)
│   ├── .env                  Environment config (not in git)
│   ├── requirements.txt
│   └── manage.py
│
├── frontend/                 SvelteKit project
│   ├── src/routes/           Pages
│   ├── src/lib/              Components, stores, API client
│   ├── src/app.css           Global styles + design system tokens
│   ├── static/               Static assets
│   ├── svelte.config.js
│   ├── vite.config.ts
│   └── package.json
│
├── scripts/
│   └── deploy.sh             Production deploy (SSH + systemd + nginx + smoke test)
│
├── .github/
│   └── workflows/
│       └── deploy.yml        CI: triggers deploy on push to main
│
├── CLAUDE.md                 Project facts for Claude Code (project overlay)
├── SYSTEM_RULES.md           Engineer-role protocol (diff/PR/deploy discipline)
└── README.md                 ← You are here
```

---

## Data model

The central entity is `Person`. Everything else hangs off a person (or, for
`Media`/`Report`, off a person or another report).

### Person

- **Identifying**: `name`, `legal_name`, `aliases`, `country`, `ethnicity`,
  `gender`, `date_of_birth`
- **Status**: `current_status` (detained / disappeared / restricted_movement /
  released / deceased / unknown / stateless / rights_restricted),
  `medical_status` (unknown / healthy / health_concerns / critical /
  deceased)
- **Location**: `rough_location` (public), `precise_location` (PRIVATE)
- **Dates**: `last_known_date`, `date_of_birth`
- **Profile**: `summary_narrative`, `profile_image`, `authoritative_source`,
  `authoritative_url`
- **Quality**: `quality_tier` (1–5), `is_published`

### Report (chronological updates on a Person)

- `source_type`: firsthand / secondhand / news / document
- `source_attribution` (public), `reporter_name` + `reporter_contact` (PRIVATE)
- `date_start`, `date_end`
- `rough_location` (public), `precise_location` (PRIVATE)
- `narrative` (the body)
- `suspected_reason`, `official_reason`
- `is_private` — hides entire report from unauthenticated users

### Media (attached to a Person or a Report)

- `media_type`: photo / document / video / link
- `file` (upload) **or** `url` (external link)
- `visibility`: **public** / **restricted** (authenticated) /
  **sensitive** (advocates + admin)
- `description` (≤500 chars)

### Other

- **CaseworkRecord** — advocacy actions linked to a person (letter sent,
  campaign launched, legal filing, etc.)
- **Contact** — people involved in cases; always private
- **FamilyRelationship** — links between two `Person` records
- **AuditLog** — tracks access to sensitive data

---

## Roles & permissions

Four role tiers, in increasing privilege:

| Role | Can do |
|---|---|
| **Public** | Browse published persons + public reports + public media |
| **Volunteer** | Enter/edit reports, upload media |
| **Advocate** | All of Volunteer + casework records + contacts + restricted media |
| **Admin** | Everything, including sensitive media + audit logs |

Authentication in production uses Google OAuth via django-allauth.

---

## Privacy model

Three layers of protection — implemented at every layer of the stack:

1. **Field-level** (`PRIVATE` flag on Django models): the field is omitted
   from the API response entirely when the requester lacks permission.
   Example: `Person.precise_location`, `Report.reporter_name`,
   `Contact.*`.
2. **Record-level** (`Report.is_private`, `Person.is_published`): the
   entire record is hidden, not just fields within it.
3. **Media tier** (`Media.visibility`): `public` / `restricted` /
   `sensitive`. Sensitive files are **always served through Django** —
   they are never exposed at a direct URL.

Sensitive uploads live under `backend/sensitive_media/` (separate from the
regular `backend/media/` directory) and require an authenticated
advocate/admin to access.

---

## Design system & UI

The Case Details page (the most-trafficked surface) has been polished into a
single, unified design system. See **[`frontend/README.md`](frontend/README.md)**
for the full reference: design tokens (`--radius-card`, `--shadow-card`,
`--card-padding`, etc.), card rules, entrance animations, hover transitions,
and per-component manual verification checklists for:

- Reports section (single-open accordion, source-type badges, URL buttonification)
- Summary section (paragraphs, bold dates, source footer)
- Profile sidebar (rounded photo, label/value rows, source footer)
- Media section (vertical stack, "View Source" action buttons)
- Sidebar metadata cards (Categories / Evidence Tier / dates)
- Design system (tokens, animation, hover)

---

## Development workflow

### Conventions

- **Feature branches** — never work on `main` directly. Branch names:
  `feat/<feature>`, `fix/<issue>`, `chore/<task>`.
- **Conventional commits** — `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`,
  optionally scoped: `feat(persons): …`.
- **PRs are required** for merge into `main`. Delete the branch after merge.
- **Build before pushing** to avoid CI failures (see `Development` below).

### Commands cheat sheet

```bash
# Frontend
cd frontend
npm install                # first time / after package.json changes
npm run dev                # vite dev server
npm run build              # production build → ./build/
npm run check              # type-check (svelte-check)
npm run test               # vitest unit tests
npm run preview            # preview the production build locally

# Backend
cd backend
source .venv/bin/activate
python manage.py runserver 127.0.0.1:8040
python manage.py makemigrations
python manage.py migrate
python manage.py test       # pytest-style via Django test runner
```

### Pre-deploy checklist (SvelteKit)

Per `SYSTEM_RULES.md` §3, every production build must:

1. Use `PUBLIC_BASE_PATH=""` and `ORIGIN=https://cases.raisethevoices.org`
   (or the live equivalent) so path-drifting doesn't 404 assets.
2. `rsync build/client/_app/` to the nginx doc root (`/var/www/cases/`).
3. **Restart the Node server process** — it caches HTML in memory and
   will keep serving stale asset hashes otherwise. The deploy script
   (`scripts/deploy.sh`) does this defensively, with a nohup fallback if
   systemd fails.

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
    AND the API returns 200. Retries up to 10× with 3s backoff.

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

Both are group-writable. Update them when the project changes; new Claude
sessions will pick up the changes immediately.

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
- **Production builds**: `PUBLIC_BASE_PATH=""` + `ORIGIN` set + restart the
  Node server.
- **No secrets in diffs or chat.** If a secret leaks, alert immediately.

When in doubt, read `CLAUDE.md` + `SYSTEM_RULES.md` first.
