# testimonies.world — End-to-End Architecture & Security Audit

**Date:** 2026-09-23
**Scope:** full stack (Django backend, SvelteKit frontend, CI/CD, infra, deployment)
**Method:** static read + cross-reference of git state, settings, models, viewsets, serializers, routes, components, Dockerfiles, systemd units, scripts, workflows.
**Severity scale:** Critical → High → Medium → Low.

> Every finding below cites the file and line that proves it. No theorising.

---

## 0. Git Sync State

| Item | Value |
|---|---|
| Branch | `main` |
| Remote sync | `Your branch is up to date with 'origin/main'` |
| Working tree | clean (`nothing to commit, working tree clean`) |
| Stashes | **4 stashes** on feature branches (`fix/c7-test-cleanup`, `chore/testimonials-quality-pass`, `feat/container-prod-readiness-v1`, `feat/openapi-zod-type-pipeline`) |
| Unpushed local commits | `24fb348` on `fix/c7-test-cleanup`, `1dd1b69` on `fix/c7-test-cleanup` |
| Last commit on `main` | `df2bdd6 refactor(ui): consolidate inline SVGs into Icon + extract StatsBar` |
| `SYSTEM_RULES.md` / `backend/.env` | gitignored (verified) |

The working tree is in sync with `origin/main`, but **4 stashes and a 2-commit local branch (`fix/c7-test-cleanup`) sit uncommitted to any push**. Nothing is lost, but they should either be pushed or dropped.

---

## 1. Critical Findings (block production)

### C-1. `CaseworkRecordViewSet.permission_classes` double-assigned — Advocate role gate silently dropped

`backend/casework/views.py:32-33`
```python
permission_classes = [permissions.IsAuthenticated, IsAdvocate]
permission_classes = [permissions.IsAuthenticated]
```

Python keeps only the second assignment. The class attribute is therefore `[IsAuthenticated]`. The comment block at lines 27-31 (Aug-2026 hardening commit) **intended** the Advocate gate but the rewrite is broken: any logged-in user — including a fresh volunteer — can read every `CaseworkRecord` row (`description`, `notes`, `next_steps`) and create/update/delete them. The view's `get_queryset()` (`casework/views.py:45-63`) returns all rows to authenticated users, so a volunteer can also **enumerate every casework record platform-wide**.

**Impact:** volunteers see PII (family contacts, un-redacted sources) the data model classifies as advocate-only.
**Fix:** delete line 33. Re-run `tests/test_auth.py` to confirm role enforcement.

### C-2. Production-shaped secrets in `backend/.env`

`backend/.env` is gitignored (good) but present in the working tree and reads at runtime via `scripts/systemd/rtv-cases-backend.service:24`. Confirmed values:

| Line | Key | Value | Severity |
|---|---|---|---|
| `backend/.env:2` | `SECRET_KEY` | `LFYaVMDjkPFTdGgXQ_x2Bq5fpr9OKX25tF463KXR39o7xXlzHVCRwWZxEiBWEj-yOwE` (50-char high-entropy) | C — forge Django sessions |
| `backend/.env:14-15` | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | real-looking OAuth credentials | C if prod |
| `backend/.env:19` | `ENABLE_E2E_TEST_AUTH` | `True` | C — flips on `/__test__/login/` |
| `backend/.env:20` | `TESTIMONIAL_E2E_AUTH_TOKEN` | `NPiJ-7mxxOC5SEsfWWCz1jU2N9WQTHvviyQjLqqgNhI` | C — token for `/__test__/login/` |

`.env.example` correctly sets `ENABLE_E2E_TEST_AUTH=False`. The on-disk file overrides it to True. Combined with the token, anyone with read on the file (or a backup of it) can `POST /__test__/login/ {"username":"admin"}` and become admin without password.

**Fix:** confirm `ENABLE_E2E_TEST_AUTH=False` on prod; rotate the token and `SECRET_KEY`; if the on-disk file is the live prod `.env`, treat it as compromised and rotate everything.

### C-3. Production admin credentials committed to repo

`CLAUDE.md:20` and `README.md:53`:
```
Django admin: demos.linkedtrust.us/testimonies/admin/ (admin / tw-admin-2026)
```

Anyone hitting `https://demos.linkedtrust.us/testimonies/admin/` with `admin / tw-admin-2026` is in. The README also documents the demo creds in `pass: tw-admin-2026` form on line 53. **If this is the prod URL** (the host is `demos.linkedtrust.us`, not `cases.raisethevoices.org`), the repo ships the keys to the kingdom.

**Fix:** rotate the admin password; remove both lines from CLAUDE.md / README.md; move demo creds to a sealed onboarding doc.

---

## 2. High Findings

### H-1. `--radius-control` token referenced 10× but never defined

Token declared in `frontend/src/app.css` is missing the `--radius-control` line, yet:

```
frontend/src/lib/Toast.svelte:217, 268, 286
frontend/src/lib/ErrorCard.svelte:194
frontend/src/lib/ReportForm.svelte:862
frontend/src/routes/persons/[id]/+page.svelte:2241, 2249
frontend/src/routes/contacts/new/+page.svelte:502
frontend/src/routes/reports/+page.svelte:968
```

CSS variable lookup fails silently → buttons / toasts lose their rounded corners. Visible UI regression caused by partial design-system migration.

**Fix:** add `--radius-control: var(--radius-input);` (or appropriate value) to `app.css:91`.

### H-2. `PersonViewSet` and `MediaViewSet` write paths skip `AuditLog`

`backend/cases/views.py:385-432` (`PersonViewSet.perform_create`/`perform_update`): no `_audit()` call. Only `CaseEvent` is written on status diffs. Person create/edit are invisible in the audit log.

`backend/cases/views.py:991-998` (`MediaViewSet.perform_create`/`perform_update`) + no `perform_destroy` override at all: uploads, edits, deletes of media leave no `AuditLog` row. The dashboard's `/audit-logs/` page promises a paper trail; this gap breaks that promise for two of the highest-stakes tables.

**Fix:** add `_audit('EDITED', instance, 'created')` / `'updated'` / `'DELETED'` to both viewsets.

### H-3. `TestimonialViewSet.submit` has no role gate

`backend/cases/testimonials/views.py:276-285`:
```python
@action(detail=True, methods=['post'])
def submit(self, request, pk=None):
```

No `permission_classes=` kwarg. Falls back to `DEFAULT_PERMISSION_CLASSES = IsAuthenticatedOrReadOnly` (`testimonies/settings.py:372-374`). Combined with `from_states=[DRAFT, REJECTED]` validation only (`views.py:281-285, 383-388`), an authenticated Advocate can POST to `/api/testimonials/<id>/submit/` on any volunteer's draft they can resolve via `get_object()`.

**Fix:** add `@action(..., permission_classes=[CanSubmitTestimonial])` and an object-level authorship check inside `_transition` (volunteer may submit only own draft; Advocate may not advance other authors' drafts without review).

### H-4. `SourceViewSet.perform_create` lacks parent-report authorship check

`backend/cases/views.py:875-880` calls `serializer.save()` without verifying the requester owns `validated_data['report']`. A volunteer can POST `{report: <any_report_id>, ...}` and attach a Source to any report on the platform.

**Fix:** in `perform_create`, check `request.user` can write to `instance.report` (or use a `PrimaryKeyRelatedField` with `queryset=Report.objects.filter(...)` filtered to authored reports).

### H-5. `ReportSerializer` exposes Section M fields as writable to volunteers

`backend/cases/serializers.py:232-235`: `risk_level`, `risk_concerns`, `internal_notes` are writable on PATCH. Read-side `to_representation` (`serializers.py:262-268`) strips them for non-Advocates, but a volunteer can `PATCH /reports/<id>/` with `{"internal_notes":"..."}` on any report they authored.

**Fix:** add `risk_level`/`risk_concerns`/`internal_notes` to `read_only_fields` for the volunteer serializer path; use a separate `ReportInternalWriteSerializer` for Advocate+.

### H-6. Committed Fernet dev-fallback key

`backend/cases/testimonials/dev_key.py:27-29`:
```python
TESTIMONIALS_DEV_FALLBACK_KEY = b'hqMeZwk7bLZku5x5flLKUDPKaZvbk0aTPW3PO8Y_-vk='
```

If any deployment runs with `DEBUG=True` (or `ALLOW_DEV_FALLBACK_KEY=True`), every `source_encrypted`/`precise_location_encrypted` ciphertext is decryptable by anyone with repo read.

**Fix:** delete `dev_key.py` once all deploys set `TESTIMONIALS_FERNET_KEY`. Add a startup-time assertion that `DEBUG=False` ⇒ the fallback path is unreachable.

### H-7. `audit.yml` Lighthouse CI does nothing

`.github/workflows/audit.yml:21-55` runs `npm ci && npm run build` then exits. No `lhci collect`, no `lhci assert`, despite the workflow title "Lighthouse CI on PR preview". Branch-protection rules that depend on this file silently do nothing.

**Fix:** add the `lhci collect` + `lhci assert` steps; verify `.lighthouserc.json` thresholds match the script.

### H-8. `SCRIPT_NAME` empty → static/media broken in prod

`backend/.env:9` sets `SCRIPT_NAME=` (empty). With `SCRIPT_NAME` empty, Django serves `/static/`, `/media/`, `/api/`. nginx (`scripts/nginx/rtv-cases:197-213`) matches only `/testimonies/api/`, `/testimonies/admin/`, etc. — **not** the bare paths. The smoke test in `deploy.sh:430-475` does not exercise `/testimonies/static/` or `/testimonies/api/`, so this can ship silently.

**Fix:** set `SCRIPT_NAME=/testimonies` in the deployed `.env`; extend the smoke test to hit `/testimonies/api/v1/...` and `/testimonies/static/...`.

### H-9. `frontend/Dockerfile` runtime runs as root

`frontend/Dockerfile:38-70` (runtime stage): no `USER` directive. The SvelteKit Node adapter runs as root inside the container. Combined with no `cap_drop` / `no-new-privileges` in `docker-compose.yml`, a Node CVE is a root-level container escape.

**Fix:** add `USER node` (or a non-root user created in builder) to runtime stage.

### H-10. SSR-defeating client-only fetching on key pages

Pages without `+page.ts` (initial fetch happens in `$effect` / `onMount`):
```
frontend/src/routes/persons/[id]/+page.svelte
frontend/src/routes/persons/[id]/edit/+page.svelte
frontend/src/routes/persons/[id]/report/+page.svelte:36
frontend/src/routes/casework/new/+page.svelte
frontend/src/routes/contacts/new/+page.svelte
frontend/src/routes/submit/+page.svelte
frontend/src/routes/settings/+page.svelte:17  (literal `onMount`)
```

Hard refresh renders empty skeleton → waits for browser round-trip. Defeats SvelteKit SSR, hurts first paint and SEO.

**Fix:** move fetches into `+page.ts` (universal load).

### H-11. Type system holes — `any` at render boundary

```
frontend/src/lib/PersonCard.svelte:29        person: any
frontend/src/lib/RelatedCases.svelte:41      const body: any = res.data
frontend/src/lib/RelatedCases.svelte:108     <StatusBadge status={person.current_status as any} />
frontend/src/routes/+layout.svelte:15        children: any
frontend/src/routes/submit/+page.svelte:39   let categories: any[] = $state([])
frontend/src/routes/submit/+page.svelte:233-255  5× (s as any).uid
frontend/src/routes/persons/[id]/edit/+page.svelte:18   categories: any[]
frontend/src/routes/persons/[id]/edit/+page.svelte:124  (c: any) => c.id
```

`Person`, `PersonCategory`, `StatusValue` are all already declared in `lib/types.ts`. A field rename silently propagates with no compile error.

**Fix:** replace `any` with the existing interfaces; remove `as any` casts.

### H-12. `deploy.yml` no concurrency group, no pre-deploy gate

`.github/workflows/deploy.yml:4-6`: triggers on every `push` to `main` with no concurrency group. Two pushes within 30 s spawn two concurrent deploys to the same VM. The deploy shell (`scripts/deploy.sh:84`) does `git reset --hard origin/main` — concurrent runs can race on this.

Also: deploy does not invoke `audit.yml` or `validate.sh` as a pre-deploy gate.

**Fix:** add `concurrency: { group: deploy-prod, cancel-in-progress: false }`; require `audit.yml` and `ci.yml` to be green.

---

## 3. Medium Findings

### M-1. Bell dropdown + tablists lack keyboard/AT semantics
- `frontend/src/lib/Bell.svelte:162` — `role="dialog"` without `aria-modal="true"`, no focus trap.
- `frontend/src/lib/ViewToggle.svelte:50-71` and `routes/notifications/+page.svelte:136-153` — `role="tablist"`/`role="tab"` with no ←/→/Home/End navigation (WCAG tablist pattern violation).

### M-2. `mutator.ts` Content-Type guard has operator-precedence bug
`frontend/src/lib/api/mutator.ts:42-48`:
```js
if (
  options.body &&
  typeof FormData === 'undefined' ||
  (!(options.body instanceof FormData) && !('Content-Type' in headers))
) {
```
`&&` binds tighter than `||`. Works by accident.

### M-3. No retry logic in API client
`frontend/src/lib/api/mutator.ts` is single-shot; transient server blips surface as hard errors to users.

### M-4. Plaintext PII columns (defence-in-depth gap)
`Person.medical_notes`, `Person.precise_location`, `Report.reporter_name`, `Report.reporter_contact`, `Report.precise_location` are stored unencrypted. API-layer `to_representation` strips them, but a DB dump or backup leak exposes them.

### M-5. `MediaSerializer` lets volunteers attach to any Person/Report
`backend/cases/serializers.py:172-180` (`fields='__all__'`, `read_only_fields=['uploaded_by','created_at']`). Volunteer can set `person`/`report` to a foreign id.

### M-6. Hardcoded hex colors in 24 of 36 components
`StatusBreakdownChart.svelte:36-43` (8 brand hexes), `ErrorCard.svelte:111-112,141`, `Toast.svelte:300-318`, `TestimonialCard.svelte:259-280` (12 status-pill hexes). Tokens `--color-success-*`, `--color-warning-*` exist in `app.css:48-55` but enforcement is per-component conscience, not lint-enforced.

### M-7. Skeleton shimmer keyframes duplicated in 3 files
`Skeleton.svelte:172`, `StatisticsCard.svelte:209`, `RelatedCases.svelte:219` — fragile `:global()` cascade.

### M-8. `Source` and `CaseUpdate` models missing DB indexes
`backend/cases/models.py:879-880` (`Source`) and `:1151-1154` (`CaseUpdate`) — no `(report_id, is_private)` / `(person, -update_date)` indexes. Section Q per-person history reads are sequential.

### M-9. CI throttle on Testimonial transition actions absent
`cases/testimonials/views.py:50-94` — only the global `user: 600/minute` cap applies. An Advocate can fire 600 decrypt calls per minute on `/api/testimonials/<id>/source/`.

### M-10. CI does not gate against `Source`/`CaseUpdate` index regressions
No migration lint, no `EXPLAIN` check.

### M-11. `gunicorn.conf.py` trusts X-Forwarded-For from any source
`backend/gunicorn.conf.py:32-33`: `forwarded_allow_ips = '*'`, `proxy_allow_ips = '*'`. On-host prod binds 127.0.0.1 (`scripts/systemd/rtv-cases-backend.service:27`), so the surface is bounded, but it's a defence-in-depth gap.

### M-12. backend service hardening inconsistent with backup service
`scripts/systemd/rtv-cases-backend.service` lacks `NoNewPrivileges=true`, `ProtectSystem=strict`, `PrivateTmp=true` — all present on `scripts/systemd/rtv-cases-db-backup.service:36-38`.

### M-13. `frontend/Dockerfile` ships full `node_modules` into runtime
Line 56: `COPY --from=builder /app/node_modules /app/node_modules` — pulls 1.6 GB into runtime image. Only the production deps are needed.

### M-14. `audit-lighthouse.sh` runs Chrome with `--no-sandbox`
`scripts/audit-lighthouse.sh:107`. Operator-only, but worth flagging for future runs against untrusted URLs.

### M-15. `scripts/validate.sh` references nonexistent user systemd unit
`scripts/validate.sh:54`: `systemctl --user is-active tmp-testimonies-backend` — unit is not in repo; the "is the app already running" check silently no-ops on every developer machine.

### M-16. `scripts/systemd/rtv-cases-frontend.service` ExecStart unverified
`scripts/systemd/rtv-cases-frontend.service:12-16`: comment explicitly admits ExecStart is "best-guess reconstruction" asking future maintainers to verify against prod.

### M-17. `SourceViewSet.perform_update` audit row lacks field-delta
`backend/cases/views.py:887-888` only logs `"updated"` (vs Report's `<field list>`). Limits forensic value.

### M-18. Inconsistent toast feedback across `load()` handlers
Some routes (`/`, etc.) call `handleApiError` correctly; many `load()` functions catch errors silently into inline state without firing a toast. Users miss transient errors.

### M-19. `WireFormatError` throw path dormant for most endpoints
`frontend/src/lib/api/parser.ts:17-38` throws on Zod failure, but only `getPerson` (api.ts:161-168) wraps with `withSchema`. Other endpoints accept unvalidated JSON.

### M-20. `frontend/src/routes/+layout.svelte:74-80` storage event listener leaks
Added every render with no cleanup.

---

## 4. Low Findings

- **L-1** No `node_modules/` gitignore at repo root (only `frontend/node_modules/`); no `*.log`, `*.pid`, `*.sqlite` (only `.sqlite3`) in root `.gitignore`.
- **L-2** `MediaStorageRouter.url()` (`backend/cases/storage.py:142-144`) doesn't sanitise path — safe in practice because `MediaDownloadView` (`cases/views.py:1229-1232`) blocks traversal.
- **L-3** `PersonCard.svelte:65-99` — three sibling `<a>` elements pointing to the same URL; SR announces "View details" three times.
- **L-4** `MediaUploadModal.svelte:297-308` — `<div role="button">` drop zone lacks `aria-label`.
- **L-5** `extractFieldErrors` (`frontend/src/lib/api/errors.ts:154-165`) only handles flat `{field: string|string[]}` — DRF nested serializer errors silently dropped.
- **L-6** `IsUnauthorized` / `IsServer` / `IsValidation` getters on `ApiError` (`frontend/src/lib/api/errors.ts:88-99`) have no consumers — handlers branch on raw `status`.
- **L-7** CI runs on every push to `feat/**`/`fix/**`/etc. (`.github/workflows/ci.yml:4-7`) — burns minutes.
- **L-8** CI backend job (`ci.yml:98`) re-runs `pip install` every time (no `actions/cache` on Python deps).
- **L-9** `scripts/deploy.sh:71` tags are never pruned or pushed — ~365 deploy tags per year per env.
- **L-10** `scripts/deploy.sh:305-312` fallback gunicorn pid in `/tmp/cases-backend.pid` — world-writable → pid hijack risk.
- **L-11** `scripts/backup_db.sh:42-45` `set -a; source "$ENV_FILE"` exposes `SECRET_KEY`, `GOOGLE_CLIENT_SECRET`, `TESTIMONIAL_E2E_AUTH_TOKEN` to every child process; visible in `/proc/<pid>/environ`.
- **L-12** `scripts/deploy.sh:49-54` bootstraps Node 22 from `deb.nodesource.com` over `curl|bash` from the prod VM.
- **L-13** `CI_CD_TROUBLESHOOTING.md:7-14` documents `api-drift` as a separate job — it's actually a step inside `backend`.
- **L-14** `frontend/src/routes/+layout.svelte:216-217` sets both `inert` and `aria-hidden` — `inert` already implies `aria-hidden`.

---

## 5. Numerical Scores (out of 10)

| Category | Score | Justification |
|---|---|---|
| **Git / Version Control** | 8 / 10 | Clean working tree, conventional commits, protected branches. Stashes + 1 unpushed branch are minor hygiene. |
| **UI / UX & Visual Design** | 6 / 10 | Token system declared but not enforced (`--radius-control` undefined, 24/36 components with hex). SSR-defeating fetches hurt first paint. Skeleton system is comprehensive. |
| **Frontend Architecture & Code Quality** | 6 / 10 | Orval generation + Zod overlays + structured error envelopes are solid. Undermined by `any` at render boundary, missing SSR, no retry logic, dormant WireFormatError path. |
| **Backend & Database Architecture** | 5 / 10 | API design is mature (throttles, audit logging, encryption-at-rest for testimonials). Audit-log coverage is incomplete on Person/Media; permission classes duplicate; mass-assignment gaps on Source/Report. DB indexes thin on Source/CaseUpdate. |
| **Security & Access Control** | 3 / 10 | C-1 (CaseworkRecord role gate silently dropped), committed dev Fernet key, production `.env` with E2E test-auth on, committed admin creds. These are individually severe; together they put the platform outside "secure enough for a human-rights casework system". |
| **DevOps / Build / CI-CD** | 5 / 10 | Audit workflow does nothing. Deploy has no concurrency group. systemd hardening is inconsistent. Docker images are mostly fine but frontend runs as root. Backup/rotate strategy is wired. |
| **Tests** | 5 / 10 | Backend has security/auth/perf/testimonials tests; frontend has 4 unit + 2 E2E specs. No component tests, no a11y tests, no visual regression. Coverage gate only on `cases.testimonials + cases.tests`. |
| **Accessibility** | 6 / 10 | html lang, skip-link, ARIA on Modal, heading hierarchy. Bell dialog missing aria-modal; tablists missing arrow-key navigation. |
| **Documentation** | 7 / 10 | CLAUDE.md, README.md, CI_CD_TROUBLESHOOTING.md, schema-version README, testimonials encryption posture. SYSTEM_RULES.md is gitignored (good). |
| | | |
| **Overall System Score** | **5.0 / 10** | Strong scaffolding (auth, audit, encryption, CI structure, design tokens), undermined by 3 critical findings that an attacker can chain, plus a UI regression that ships silently. Not production-grade as-is for a human-rights platform. |

---

## 6. Strategic Recommendations & Action Plan

### Phase 0 — Stop the bleeding (this week)

1. **C-1** Delete `backend/casework/views.py:33`. Re-run `tests/test_auth.py` and add a regression test that asserts `CaseworkRecordViewSet.permission_classes == [IsAuthenticated, IsAdvocate]`.
2. **C-2** Verify whether `backend/.env` is the live prod `.env`. If yes: rotate `SECRET_KEY`, `GOOGLE_CLIENT_SECRET`, `TESTIMONIAL_E2E_AUTH_TOKEN`; set `ENABLE_E2E_TEST_AUTH=False`. If no: ensure prod uses a vault/sops-managed `.env`.
3. **C-3** Rotate the `admin` Django user password. Remove `admin / tw-admin-2026` from CLAUDE.md and README.md. Move demo creds to a sealed onboarding doc.
4. **H-1** Add `--radius-control` to `frontend/src/app.css:91`. Eyeball the affected pages to confirm corners return.
5. **H-8** Set `SCRIPT_NAME=/testimonies` in deployed `.env`. Extend `deploy.sh` smoke test to hit `/testimonies/api/...` and `/testimonies/static/...`.

### Phase 1 — Audit completeness (next sprint)

6. **H-2** Add `_audit()` calls to `PersonViewSet.perform_create`, `perform_update`, `perform_destroy`; same for `MediaViewSet` (`backend/cases/views.py:991-998`). Add tests asserting `AuditLog` rows.
7. **H-3** Add `permission_classes=[CanSubmitTestimonial]` to the `submit` action on `TestimonialViewSet`; add object-level authorship check in `_transition`.
8. **H-4** Restrict `SourceSerializer`'s parent `report` to authored reports via `PrimaryKeyRelatedField(queryset=Report.objects.filter(...))` in `SourceViewSet.perform_create`.
9. **H-5** Move `risk_level`, `risk_concerns`, `internal_notes` to a separate Advocate-only write serializer; or add to `read_only_fields` for the volunteer path.
10. **H-6** Delete `backend/cases/testimonials/dev_key.py` once all deploys set `TESTIMONIALS_FERNET_KEY`; add a startup assertion that `DEBUG=False` ⇒ the fallback path is unreachable.
11. **H-7** Wire up `lhci collect` + `lhci assert` in `audit.yml`; verify `.lighthouserc.json` thresholds.

### Phase 2 — Hardening (next 2 sprints)

12. **H-9 / M-13** Add `USER node` (or new non-root user) to `frontend/Dockerfile` runtime stage; drop `node_modules` from runtime image.
13. **H-10** Move fetches on the 7 SSR-defeating pages to `+page.ts`.
14. **H-11** Replace all `any` at render boundary with existing interfaces; remove `as any` casts.
15. **H-12** Add `concurrency:` block to `deploy.yml`; gate deploy on `audit.yml` + `ci.yml` green.
16. **M-4** Wrap `Person.medical_notes`, `Person.precise_location`, `Report.reporter_*`, `Report.precise_location` in Fernet (mirror `Testimonial` pattern). Audit-only fields encrypted at rest.
17. **M-8** Add `(report_id, is_private)` index to `Source`; `(person, -update_date)` to `CaseUpdate`.
18. **M-11 / M-12** Restrict `forwarded_allow_ips` to localhost; add `NoNewPrivileges=true`, `ProtectSystem=strict`, `PrivateTmp=true` to both frontend and backend systemd units.
19. **M-15** Delete the `--user` line in `scripts/validate.sh:54` (or create the user unit) — silent no-op is worse than a clear failure.
20. **M-16** Verify `scripts/systemd/rtv-cases-frontend.service:12-16` against the actual on-host unit; update the in-repo copy.

### Phase 3 — Polish

21. **M-6** Run `grep -rE '#[0-9a-fA-F]{3,6}' frontend/src/lib/`; replace each hex with the matching token. Add a `stylelint` rule to block raw hex.
22. **M-7** Extract the skeleton shimmer keyframes into `app.css`; delete the duplicates.
23. **M-18 / M-19** Add `withSchema` wrapping to all `api.ts` endpoints; ensure every `load()` error surfaces a toast.
24. **M-3** Add bounded exponential-backoff retry in `mutator.ts` for idempotent GETs.
25. **H-10 → accessibility** Add ←/→/Home/End keyboard navigation to `ViewToggle` and the notifications tablist; add `aria-modal="true"` + focus trap to `Bell.svelte`.

### Long-term (quarter)

26. **CI** Branch protection should require `ci.yml` + `audit.yml` + `deploy.yml` smoke test all green before merge to `main`.
27. **Secrets** Move all prod secrets to a vault (sops + age, or Django `django-environ` reading from `/etc/testimonies-world/*.env`). The on-disk `.env` is gitignored but present, and operators are reading it from system backups.
28. **Schema versioning** `Testimonial.schema_version=1` is the contract. Treat any subsequent bump as a coordinated migration (CLAUDE.md already documents this).
29. **Observability** No structured logging, no metrics endpoint, no Sentry wiring visible. The smoke test in `deploy.sh:430-475` is a probe, not a monitoring path. Add `django-prometheus` + a `/metrics` endpoint behind admin-only auth, and wire Sentry on both backend and frontend.
30. **DB indexes review** A schema-wide `EXPLAIN ANALYZE` pass against the top-20 query patterns would catch the Source/CaseUpdate gaps and likely surface 3-5 more.

---

## 7. Top 5 Risks (one line each)

1. **C-1** Advocate role gate silently dropped on `CaseworkRecordViewSet` — any volunteer can read/write every casework record. (`casework/views.py:32-33`)
2. **C-2** `ENABLE_E2E_TEST_AUTH=True` + a real token in `backend/.env:19-20` — anyone with file read can become admin via `/__test__/login/`.
3. **C-3** Production admin credentials committed in `CLAUDE.md:20` and `README.md:53` (`admin / tw-admin-2026`).
4. **H-7** `audit.yml` Lighthouse CI does nothing despite its name — branch-protection perf gate is silent.
5. **H-8** `SCRIPT_NAME` empty in `.env` — nginx routing for static/media/api silently broken in prod; smoke test doesn't catch it.

---

*End of report. The full agent transcripts that produced these findings are available at `/tmp/claude-1006/-home-aya-testimonies-world/23d85f0b-3a0b-4b8b-a30c-adbd426e5259/tasks/` (not for redistribution).*
