# Frontend — Testimonies.world

SvelteKit 2 + Svelte 5 SPA-style app. Lives at `/testimonies/` behind nginx on the demo VM and at the domain root in production.

The main project README is at [`../README.md`](../README.md) — stack, data model, deployment live there. This README covers frontend-only concerns: setup, scripts, environment, architecture, and the API client.

---

## Requirements

- **Node 22.18+** (`.npmrc` sets `engine-strict=true`; npm refuses to install otherwise). `scripts/deploy.sh` bootstraps Node 22 via NodeSource on a fresh VM.
- **npm** (ships with Node 22).

No Python, Postgres, or Redis needed for frontend-only work — the dev server proxies `/testimonies/api/*` and `/testimonies/accounts/*` to the backend.

---

## Install

```bash
cd frontend
npm install
```

First install, or after any change to `package.json` / `package-lock.json`.

---

## Run locally

```bash
PUBLIC_BASE_PATH=/testimonies npm run dev -- --host 0.0.0.0 --port 3040
```

- `PUBLIC_BASE_PATH=/testimonies` — matches the demo VM path so the dev server emits the same asset layout nginx expects in production. Leave off only if you are debugging the root-path build.
- `--host 0.0.0.0 --port 3040` — listen on all interfaces (for sharing with the VM) on a non-default port (Vite's `:5173` collides with other dev tools).
- Open <http://localhost:3040/testimonies/>.

The dev server proxies API traffic to `https://cases.raisethevoices.org` (the live prod backend) by default. See [Environment variables](#environment-variables) for `VITE_API_PROXY_TARGET`.

The backend must be reachable for `/api/*` calls — either the live backend or your local one (`http://127.0.0.1:8040`). To run against a local backend, see the E2E setup below.

---

## Environment variables

| Variable | Used at | Default | Purpose |
|---|---|---|---|
| `PUBLIC_BASE_PATH` | build (`svelte.config.js`) | `""` | SvelteKit `paths.base`. Set to `/testimonies` for the demo VM deploy, leave empty for the production root deploy. |
| `ORIGIN` | prod server (`build/index.js`) | — | CSRF / cookie scoping. Must match the public origin (`https://cases.raisethevoices.org` in prod). |
| `VITE_API_PROXY_TARGET` | dev (`vite.config.ts`) | `https://cases.raisethevoices.org` | Where the dev server proxies `/testimonies/api/*` and `/testimonies/accounts/*`. Set to `http://127.0.0.1:8040` to run against a local backend. |
| `PUBLIC_SENTRY_DSN` | runtime (`hooks.server.ts`, `hooks.client.ts`) | `""` | Sentry project DSN. Empty disables Sentry (no-op init). |
| `PUBLIC_SENTRY_ENV` | runtime | `development` | Sentry environment tag. |
| `PUBLIC_SENTRY_RELEASE` | runtime | — | Sentry release tag. |
| `PUBLIC_SENTRY_TRACES_SAMPLE_RATE` | runtime | `0` | Performance trace sampling. `0` disables; `0.0–1.0` enables for that fraction of sessions. |

`PUBLIC_*` vars are inlined into the client bundle at build time. Non-`PUBLIC` server-only vars go through `$env/dynamic/private`.

PII is **never** sent to Sentry (`sendDefaultPii: false`) — the project handles sensitive human-rights data.

---

## Scripts

```bash
npm run dev              # vite dev server
npm run build            # production build → ./build/
npm run preview          # serve ./build/ locally for smoke testing
npm start                # node build/index.js — prod server (used by systemd rtv-cases-frontend)
npm run check            # svelte-check (TypeScript + Svelte diagnostics)
npm run test             # vitest unit tests
npm run test:watch       # vitest in watch mode
npm run gen:api          # regenerate src/lib/api/generated/ from ../openapi.yml
npm run gen:api:check    # CI drift gate — fails if regen would change a committed file
npm run audit:lh         # lighthouse against running dev server
npm run audit:lh:build   # lighthouse against built bundle (preview server)
```

E2E tests live in `tests/` and run via Playwright separately — see [`playwright.config.ts`](playwright.config.ts).

---

## Architecture

```
frontend/
├── src/
│   ├── routes/              File-based routing (SvelteKit)
│   ├── lib/                 Components, stores, API client, helpers
│   ├── app.css              Design system tokens (single source of truth)
│   ├── app.html             HTML shell
│   ├── app.d.ts             Type ambient declarations
│   ├── hooks.server.ts      Server-side Sentry init + handleError
│   └── hooks.client.ts      Client-side Sentry init
├── static/                  Static assets (favicon, etc.)
├── tests/                   Playwright E2E specs
├── playwright.config.ts
├── svelte.config.js         adapter-node + paths.base
├── vite.config.ts           Dev proxy + allowedHosts
├── orval.config.ts          OpenAPI → TypeScript codegen
├── tsconfig.json
└── package.json
```

### Routes (`src/routes/`)

File-based; `+page.svelte` is a page, `+page.ts` is its data loader, `+layout.svelte` wraps children, `+error.svelte` is the error boundary.

```
/                          home / landing
/casework/                 CaseworkRecord CRUD (advocate)
/contacts/                 Contacts (advocate)
/dashboard/                Operator dashboard
/dashboard/audit-logs/    Sensitive-data access log
/notifications/            In-app notifications
/persons/                  Cases catalog (search/filter/cards-vs-list)
/persons/[id]/             Case detail
/persons/[id]/edit/        Edit case
/persons/[id]/report/      Add a Report to the case
/reports/                  Reports CRUD
/settings/                 User settings
/statistics/               Stats dashboards
/submit/                   Submit-a-case intake
/testimonials/             Published testimonials list
/testimonials/[id]/        Testimonial detail
/testimonials/new/         Compose new testimonial
/watchdog/                 Watchdog surface
```

### `src/lib/` layout

- **Components** (`*.svelte`) — UI primitives and composite widgets: `Modal`, `Toast`, `StatusBadge`, `PersonCard`, `ViewToggle`, `FilterToolbar`, `ReportForm`, `TestimonialForm`, `MediaUploadModal`, `Icon`, etc.
- **API client** (`api/`) — see [API client](#api-client) below.
- **Schemas** (`schemas/`) — Zod schemas that parse generated OpenAPI types into richer runtime shapes (branded types, `Date`, `Decimal`).
- **Stores / state** — Svelte 5 runes-based modules: `session.ts`, `toast.ts`, `notification.ts`, `formError.ts`, `formFocus.ts`, `dataLoader.svelte.ts`.
- **Utilities** — `sanitize.ts` (HTML), `submitDraft.ts` (auto-save drafts), `statusPresentation.ts`, `debounce.ts`, `types.ts`.
- **Assets** (`assets/`) — fonts, images, anything bundled.

### Design system

All visual tokens (colors, radii, shadows, spacing, motion) live in `src/app.css` `:root`. Components reference them via `var(--…)` — never hardcode. `prefers-reduced-motion: reduce` is respected globally.

---

## API client

The client is **generated** from `../openapi.yml` (the Django backend's OpenAPI schema) using [orval](https://orval.dev/). Do not edit generated files by hand — re-run `npm run gen:api`.

```bash
npm run gen:api           # regenerate src/lib/api/generated/
npm run gen:api:check    # CI: fails if regen would change committed output
```

The pipeline:

1. `manage.py spectacular` (in the backend) dumps `../openapi.yml`.
2. orval reads it and writes `src/lib/api/generated/endpoints.ts` + `endpoints.schemas.ts` (TypeScript types + Zod schemas per endpoint family).
3. `scripts/fix-orval-order.js` reorders declarations so forward references don't break strict TS.
4. Every generated function calls the `fetcher` in [`src/lib/api/mutator.ts`](src/lib/api/mutator.ts). The mutator handles:
   - Forwarding session cookies (credentials).
   - Forwarding CSRF token on non-GET methods (`X-CSRFToken` from `csrftoken` cookie).
   - Prepending `base` (PUBLIC_BASE_PATH) to every URL — required for the `/testimonies/` sub-path deploy.
   - Returning the `Response` so orval's own JSON parser handles the simple case and the Zod layer (`parser.ts`) can intercept for typed runtime shapes.

Custom error handling lives in `src/lib/api/errors.ts` + `handleError.ts`. Svelte 5 hooks for API calls live in `useApiCall.svelte.ts`.

When you change a serializer in the backend:

1. Run the backend's `manage.py spectacular` (or rely on CI to flag drift).
2. Run `npm run gen:api` locally.
3. Fix any type errors in the consuming code.
4. Commit `openapi.yml` + the regenerated `src/lib/api/generated/` together.

---

## Production build

```bash
PUBLIC_BASE_PATH="" \
ORIGIN=https://cases.raisethevoices.org \
  npm run build
```

`PUBLIC_BASE_PATH=""` for the root-domain prod deploy (`/testimonies` for the demo VM). `ORIGIN` must match the public origin so CSRF + cookies scope correctly. `scripts/deploy.sh` runs the build with these vars set and rsyncs `./build/client/testimonies/` (with the `./build/server/chunks/client` symlink trick for `@sveltejs/adapter-node 5.5.x`) to `/var/www/cases/`.

---

## Testing

```bash
npm run test                 # unit tests (vitest)
npm run test:watch           # unit tests in watch mode
npm run check                # type-check (svelte-check)
npm run gen:api:check        # API drift gate (CI)
npm run audit:lh:build       # lighthouse audit against built bundle
```

E2E (Playwright) — see [`playwright.config.ts`](playwright.config.ts) and [`tests/`](tests/). Set `VITE_API_PROXY_TARGET=http://127.0.0.1:8040` so E2E runs against the local backend.

---

## Conventions

- **No hardcoded paths or IDs.** All paths flow through `$app/paths` (or the generated orval client's `base`).
- **No raw `fetch` in components.** Use the generated API client so CSRF, cookies, and error handling stay consistent.
- **Sanitize user-supplied HTML** with `src/lib/sanitize.ts` (isomorphic-dompurify). Untrusted narrative goes through `sanitizeNarrative` before render.
- **Status / type enums** are mirrored from `backend/cases/models.py`. When the backend adds a value, update `statusPresentation.ts` + any UI badge map in the consuming component.