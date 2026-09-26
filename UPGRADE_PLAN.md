# testimonies.world — Detailed Upgrade Plan

**Companion to:** `AUDIT_REPORT.md` (read that first)
**Approach:** fix root causes, not symptoms. Sequence matters — some phases unblock others. Every step cites the file:line where the work starts.

---

## Sequencing (read this first)

```
Phase 0 — Stop the bleeding        3 critical findings       THIS WEEK
Phase 1 — Close the audit gaps     12 high findings          1-2 weeks
Phase 2 — Harden the platform      docker, systemd, secrets  2-4 weeks
Phase 3 — Observability + tests    you can't run what        ongoing
                                   you can't see
Phase 4 — Performance              caching, indexes, SSR    ongoing
Phase 5 — Process & docs           ADRs, runbooks, drills   ongoing
```

Each phase has dependencies on the previous. Don't skip Phase 0 to "do the fun work in Phase 4" — the criticals are exploitable today.

---

## Phase 0 — Stop the bleeding (3 days)

### 0.1 Fix the CaseworkRecord role gate (`casework/views.py:32-33`)

```python
# DELETE line 33:
permission_classes = [permissions.IsAuthenticated]
```

**Then add a regression test** that pins this. The next refactor will reintroduce the bug.

```python
# tests/test_auth.py
def test_casework_record_requires_advocate():
    from casework.views import CaseworkRecordViewSet
    assert CaseworkRecordViewSet.permission_classes == [
        permissions.IsAuthenticated, IsAdvocate,
    ], "CaseworkRecordViewSet must require IsAdvocate"
```

**Tip:** for any class that inherits from a `ViewSet`, lint `permission_classes` against an explicit allowlist in CI. A simple grep doesn't work because subclasses can override — read the MRO.

### 0.2 Audit `backend/.env` — is it the live prod `.env`?

Decide one of three answers:
1. **No, prod uses a different path** — fine. Move on.
2. **Yes, this IS prod's `.env`** — rotate everything immediately:
   - `SECRET_KEY` → new value (`python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
   - `GOOGLE_CLIENT_SECRET` → rotate via Google Cloud Console, deploy new value
   - `TESTIMONIAL_E2E_AUTH_TOKEN` → new value, update CI secret, redeploy
   - Set `ENABLE_E2E_TEST_AUTH=False` (and keep it False in prod; CI uses its own value)
   - Force a session-cookie flush: deploy then `python manage.py shell -c "from django.contrib.sessions.models import Session; Session.objects.all().delete()"`
3. **Unsure** — assume yes (option 2).

**Tip:** secrets in a gitignored file are still readable by anyone with shell on the box, anyone with a backup, anyone with read on a CI artifact. Treat any on-disk secret as "we hope nobody finds it", not "it's safe".

### 0.3 Rotate the admin password + remove creds from docs

```bash
backend/.venv/bin/python backend/manage.py changepassword admin
```

Then edit `CLAUDE.md:20` and `README.md:49-54` — replace the `admin / tw-admin-2026` line with a link to an internal onboarding doc (1Password, sealed Notion page, sealed GitHub gist accessible only to operators).

**Tip:** if the URL `demos.linkedtrust.us/testimonies/admin/` is reached by anyone with the creds, the platform is already compromised. Don't worry about preserving "demo convenience" — the cost of compromise is human-rights workers being exposed.

---

## Phase 1 — Close the audit gaps (1-2 weeks)

### 1.1 Audit completeness on Person + Media (`cases/views.py:385-998`)

Add `_audit()` calls to:
- `PersonViewSet.perform_create` (`:385-395`)
- `PersonViewSet.perform_update` (`:397-432`)
- `PersonViewSet.perform_destroy` (`:362-376`) — already has one, verify the helper signature matches
- `MediaViewSet.perform_create` (`:991-993`)
- `MediaViewSet.perform_update` (`:995-998`)
- Add `MediaViewSet.perform_destroy` (currently uses default, no audit)

**Tip:** the audit helper should be a classmethod or module-level helper, not copy-pasted in each viewset. Search the codebase for `_audit(` — if there are 5+ duplicates with the same shape, extract to `cases/audit.py`.

```python
# backend/cases/audit.py (new file)
from .models import AuditLog

def write_audit(*, user, action, target_type, target_id, details="", ip=None):
    AuditLog.objects.create(
        user=user if user.is_authenticated else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=ip,
    )
```

### 1.2 Fix `TestimonialViewSet.submit` permission (`cases/testimonials/views.py:276-285`)

```python
@action(
    detail=True, methods=['post'],
    permission_classes=[permissions.IsAuthenticated, CanSubmitTestimonial],
)
def submit(self, request, pk=None):
    ...
```

Then in `_transition` (`views.py:356-411`), add an object-level check: only the author OR an Advocate may submit; only an Advocate may approve/reject/archive.

**Tip:** when an `@action` doesn't declare `permission_classes`, DRF falls back to the viewset's `permission_classes` — which here is `IsAuthenticatedOrReadOnly`. Always declare `permission_classes=` on `@action` decorators. Add a CI grep:

```yaml
- name: Lint @action permission_classes
  run: |
    ! grep -rn "@action(" backend/ | grep -v "permission_classes="
```

### 1.3 Fix `SourceViewSet.perform_create` parent-report check (`cases/views.py:875-880`)

Either:

```python
def perform_create(self, serializer):
    report = serializer.validated_data['report']
    if not request_can_write_report(self.request.user, report):
        raise PermissionDenied("Cannot attach a source to a report you do not own.")
    serializer.save()
```

Or restrict the queryset on the FK field:

```python
class SourceSerializer(serializers.ModelSerializer):
    report = serializers.PrimaryKeyRelatedField(
        queryset=Report.objects.filter(...),  # filter by user authorship
    )
```

**Tip:** the second approach (queryset filter) is preferred because it returns 400 with a clear message, not 403. The first approach is more flexible if the rule depends on request context.

### 1.4 Lock down `ReportSerializer` Section M fields (`cases/serializers.py:232-235`)

```python
class ReportWriteSerializer(ReportSerializer):
    class Meta(ReportSerializer.Meta):
        # Volunteer-safe fields only
        read_only_fields = [
            'created_by', 'created_at', 'updated_at',
            'risk_level', 'risk_concerns', 'internal_notes',
        ]
```

Then have `ReportViewSet` pick `ReportWriteSerializer` for non-Advocate users and the full serializer for Advocate+. Or use a per-action serializer map in `get_serializer_class()`.

**Tip:** keep the read serializer (with the field-stripping `to_representation`) and write serializer (with read-only fields) as separate classes. Mixing the two in one class leads to subtle bugs where a PATCH silently drops the field instead of erroring.

### 1.5 Delete `cases/testimonials/dev_key.py` once deploys are clean

Path: `backend/cases/testimonials/dev_key.py:27-29`.

Add a startup assertion in `encryption.py`:
```python
if not settings.DEBUG and getattr(settings, 'TESTIMONIALS_DEV_FALLBACK_KEY_USED', False):
    raise ImproperlyConfigured("Dev fallback key was used in production.")
```

Track usage with a flag the encryption module sets the first time it falls back.

**Tip:** "delete the dev fallback" sounds safe but breaks every dev who doesn't know how to generate a real key. Two-step:
1. Generate a real key for every developer (`scripts/gen-dev-key.sh`).
2. Add a one-week grace period where the fallback still works but emits a `warnings.warn(DeprecationWarning)`.
3. After the grace period, the fallback raises `ImproperlyConfigured` in any environment.

### 1.6 Wire up `audit.yml` Lighthouse CI (`.github/workflows/audit.yml:21-55`)

Current: builds and exits. Target:

```yaml
- name: Run Lighthouse CI
  run: |
    npm install -g @lhci/cli
    lhci autorun --config=frontend/.lighthouserc.json
```

`frontend/.lighthouserc.json` already declares thresholds; just invoke them.

**Tip:** Lighthouse on cold GitHub runners is slow (3-5 min per URL). Don't run on every PR — restrict to PRs touching `frontend/` via path filter:

```yaml
on:
  pull_request:
    branches: [main]
    paths:
      - 'frontend/**'
```

### 1.7 Fix `SCRIPT_NAME` routing break (`backend/.env:9`, `scripts/nginx/rtv-cases:197-213`)

Set `SCRIPT_NAME=/testimonies` in deployed `.env`. Extend `scripts/deploy.sh:430-475` smoke test:

```bash
for path in /testimonies/ /testimonies/api/v1/persons/ /testimonies/static/admin/css/base.css; do
  curl -fsS -o /dev/null -w "%{http_code} $path\n" "https://${HOST}${path}"
done
```

**Tip:** `SCRIPT_NAME` is read at import time on Django (when `STATIC_URL` and other URLs are computed). A server restart is required after changing it — `manage.py` won't pick it up live.

### 1.8 Add `--radius-control` to `app.css:91`

```css
--radius-control: 0.375rem;  /* matches the rounded-md/control aesthetic */
```

**Tip:** run `grep -rn 'var(--radius-control)' frontend/src/` after adding the token to confirm every reference resolves. Some browsers cache CSS at the file level — bump the build hash.

### 1.9 Move fetches into `+page.ts` on 7 pages

Pages listed in audit §H-10. Pattern:

```typescript
// routes/persons/[id]/+page.ts (new file)
import { getPerson } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
  const person = await getPerson(fetch, params.id);
  return { person };
};
```

```svelte
<!-- routes/persons/[id]/+page.svelte -->
<script lang="ts">
  import type { PageData } from './$types';
  let { data }: { data: PageData } = $props();
</script>
```

**Tip:** if the page needs client-side reactivity (polling, optimistic updates), keep the universal load for first paint and use `$effect` for the reactive part. Don't replace the universal load — supplement it.

### 1.10 Replace `any` at render boundary (8 sites)

Use the existing interfaces from `frontend/src/lib/types.ts`. For `as any` casts in `submit/+page.svelte:233-255`, define a Zod schema:

```typescript
import { z } from 'zod';

const SubmitStateSchema = z.object({
  uid: z.string(),
  // ...
});
```

**Tip:** the cost of a `tsc --noEmit` clean run on this codebase should be measured. If it's slow, the types are too deep, not too strict.

### 1.11 Add concurrency + pre-deploy gate to `deploy.yml`

```yaml
concurrency:
  group: deploy-prod
  cancel-in-progress: false

jobs:
  deploy:
    needs: [audit, ci]  # both must pass
```

### 1.12 Close the remaining H items from audit (H-9 Dockerfile root, H-6 already covered in 1.5)

For H-9: add `USER node` to `frontend/Dockerfile` runtime stage. Create the user in builder if needed:

```dockerfile
FROM node:22-alpine AS builder
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001
...

FROM node:22-alpine AS runtime
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001
COPY --from=builder --chown=nodejs:nodejs /app/build /app/build
USER nodejs
```

**Tip:** also `npm ci` as `nodejs` (not root) in the builder stage to avoid a different class of supply-chain risk where a malicious postinstall script runs as root.

---

## Phase 2 — Harden the platform (2-4 weeks)

### 2.1 Secrets management

Stop putting secrets in `.env` files. Use one of:

**Option A — sops + age (recommended for self-hosted):**
```bash
# operator workstation
sops --age age1xyz... --encrypt --in-place secrets.enc.yaml
# server
sops --decrypt secrets.enc.yaml > /etc/testimonies-world/secrets.yaml
```

Then Django reads from `/etc/testimonies-world/secrets.yaml` via a thin loader.

**Option B — Doppler / Vault / AWS Secrets Manager:** if you have a hosted secrets manager.

**Option C — at minimum:** move `.env` to `/etc/testimonies-world/backend.env`, mode 0600, owned by the systemd user. Document the path in a runbook.

**Tip:** secrets-in-git is binary: once committed, consider them permanently exposed. Rotate immediately if any secret ever lands in git history, even if later removed.

### 2.2 Encrypt plaintext PII columns at rest

`Person.medical_notes`, `Person.precise_location`, `Report.reporter_name`, `Report.reporter_contact`, `Report.precise_location`.

Mirror the Testimonial pattern:
- Add encrypted columns (`*_encrypted`).
- Migrate data with a data migration that reads plaintext, encrypts, writes ciphertext, then drops plaintext.
- Add property getters/setters for backwards compat in views.
- Bump `Testimonial.schema_version` is unrelated — this is a different model. Use Django migration versioning.

**Tip:** once you encrypt plaintext columns, you can no longer query them with `WHERE reporter_name LIKE '%foo%'`. If any view does that, switch to a hash column for lookup (`reporter_name_hash = SHA256(LOWER(reporter_name))`) and query against the hash.

### 2.3 DB indexes — review all models

`backend/cases/models.py`. For each model:
- List every `filter()` and `order_by()` call across views, serializers, and tests.
- Ensure a B-tree index exists for the leading column.
- For composite queries, add composite indexes in `Meta.indexes`.

Models needing attention (audit M-8):
- `Source` (`:879-880`) — add `(report_id, is_private)`.
- `CaseUpdate` (`:1151-1154`) — add `(person, -update_date)`.

**Tip:** Django's `db_index=True` is fine for single columns. For composite or partial indexes, use `Meta.indexes` with `models.Index(fields=[...], name=...)`. For partial indexes (e.g. only on `is_private=True`), use `condition=Q(...)`.

### 2.4 Hardening systemd units

Both `scripts/systemd/rtv-cases-backend.service` and `scripts/systemd/rtv-cases-frontend.service` should have:

```ini
NoNewPrivileges=true
ProtectSystem=strict
PrivateTmp=true
ProtectHome=true
MemoryDenyWriteExecute=true
LockPersonality=true
RestrictRealtime=true
RestrictSUIDSGID=true
```

Reference: `scripts/systemd/rtv-cases-db-backup.service:36-38` already has most of these.

**Tip:** test hardening in a dev VM first — some directives break apps that need `/tmp` access. `django.core.files.uploadedfile` uses `TemporaryFile` which needs `PrivateTmp=true` to be functional but isolated.

### 2.5 gunicorn: lock down `forwarded_allow_ips`

`backend/gunicorn.conf.py:32-33`: change `'*'` to `'127.0.0.1'` (or the specific nginx IP). Use the `--forwarded-allow-ips` CLI flag or `FORWARDED_ALLOW_IPS` env var.

**Tip:** if you ever put gunicorn behind a TCP load balancer, the LB's IP needs to be in `forwarded_allow_ips` too. Document this in `scripts/deploy.sh`.

### 2.6 Docker hardening

`docker-compose.yml`:
```yaml
services:
  backend:
    security_opt:
      - no-new-privileges:true
    cap_drop: [ALL]
    read_only: true
    tmpfs:
      - /tmp
    mem_limit: 512m
    pids_limit: 100
```

`frontend/Dockerfile`: add `USER nodejs` (done in Phase 1).

**Tip:** `read_only: true` requires every writable path to be a tmpfs or volume. `staticfiles/` and `media/` are volumes; `cache/` may need a tmpfs. Test before deploying.

### 2.7 Add `audit.yml` security scanning

Use Trivy or Grype:

```yaml
- name: Trivy scan
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: fs
    scan-ref: .
    severity: CRITICAL,HIGH
    exit-code: '1'
    ignore-unfixed: true
```

**Tip:** pin the action to a SHA, not `@master`. `@master` can change behavior out from under you.

### 2.8 Restrict `ENABLE_E2E_TEST_AUTH` to non-prod

In `backend/testimonies/settings.py`:
```python
if ENABLE_E2E_TEST_AUTH and not DEBUG and not getattr(settings, 'ALLOW_TEST_AUTH_IN_PROD', False):
    raise ImproperlyConfigured("ENABLE_E2E_TEST_AUTH=True is not allowed in production.")
```

**Tip:** the URL `/__test__/login/` (`backend/testimonies/urls.py:242-249`) should be reachable only when this flag is on. Verify it returns 404 (not 403) when off — 403 leaks that the endpoint exists.

---

## Phase 3 — Observability + tests (ongoing)

### 3.1 Structured logging

Currently the backend uses gunicorn's default. Add `python-json-logger` or `structlog`:

```python
# backend/testimonies/settings.py
LOGGING = {
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
    },
    ...
}
```

**Tip:** every log line should include `request_id` (set by middleware) so you can grep a single request across services. Without request IDs, debugging is archaeology.

### 3.2 Metrics

Add `django-prometheus`:
```python
INSTALLED_APPS += ['django_prometheus']
MIDDLEWARE.insert(0, 'django_prometheus.middleware.PrometheusBeforeMiddleware')
```

Expose `/metrics` behind admin-only auth. Scrape with Prometheus. Alert on:
- 5xx rate > 1% over 5 min
- p99 latency > 2s
- DB connection pool exhaustion

**Tip:** metrics without alerts are decoration. Pick 3-5 SLOs and alert only on those. Alert fatigue is real.

### 3.3 Error tracking

Wire Sentry on both backend and frontend:
- Backend: `pip install sentry-sdk`, `import sentry_sdk; sentry_sdk.init(dsn=...)`.
- Frontend: `npm install @sentry/sveltekit`, add to `hooks.client.ts`.

PII: configure Sentry's `before_send` to scrub `reporter_*`, `precise_location`, `medical_notes` fields. Sentry's default scrubbers catch credit cards and SSNs but not custom PII columns.

**Tip:** Sentry is a third-party processor — verify their data-processing agreement covers GDPR / equivalent. For a human-rights platform, the bar is higher than for a SaaS startup.

### 3.4 Test coverage expansion

Current: 4 vitest specs + 2 playwright specs + Django test suite.

Add:
1. **API client tests** — `frontend/src/lib/api/mutator.test.ts`, `errors.test.ts`, `drfCompat.test.ts`.
2. **Component tests** — `Modal.test.ts`, `Bell.test.ts`, `ViewToggle.test.ts`, `Toast.test.ts`.
3. **Accessibility tests** — `@axe-core/playwright` integrated into existing E2E specs.
4. **Visual regression** — Playwright `toHaveScreenshot()` on top 5 pages (login, person detail, dashboard, testimonial workflow, contact list).
5. **Backend security tests** — extend `tests_security.py` with cases that assert the audit log fires on every CRUD.
6. **Coverage gate** — extend `coverage report --fail-under=80` to the entire `cases/`, `casework/`, `contacts/` packages, not just `cases.testimonials`.

**Tip:** visual regression catches "we shipped `--radius-control` missing" regressions like the one in H-1. Without it, the next CSS migration breaks 12 buttons and nobody notices for two weeks.

### 3.5 Load testing

Use `locust` or `k6` against a staging instance. Profile with Django Debug Toolbar or `django-silk` in a non-prod environment.

**Tip:** synthetic load ≠ real traffic. The audit found an unauthenticated user can hammer `/api/testimonials/<id>/source/` at 600/min — load-test that specifically.

---

## Phase 4 — Performance (ongoing)

### 4.1 SSR / first paint

Already covered in Phase 1 §1.9. Track via Lighthouse CI (Phase 1 §1.6) once it's wired.

### 4.2 Query optimization

After indexes are in place (Phase 2 §2.3), profile slow endpoints:

```python
from django.db import connection
from django.test.utils import CaptureQueriesContext

with CaptureQueriesContext(connection) as ctx:
    result = serializer.data
print(len(ctx.captured_queries), ctx.captured_queries)
```

Look for N+1s (`select_related`/`prefetch_related` missing), large result sets (pagination), or duplicated queries.

**Tip:** `prefetch_related` is the right tool for reverse FKs and M2M; `select_related` for FKs. Don't prefetch everything — only what's accessed in the same request.

### 4.3 Caching

Two layers worth adding:
1. **Per-view cache** for the public list endpoints (`/api/persons/`, `/api/testimonials/` published list) with `cache_control` headers + Redis-backed storage.
2. **Template fragment cache** on the dashboard widgets.

Don't cache anything that depends on the requesting user.

**Tip:** caching without cache invalidation is a bug. Set short TTLs (60s) initially and tune. A stale dashboard for 60 seconds is fine; a stale public list for an hour is a documentation bug.

### 4.4 Bundle size

SvelteKit already tree-shakes well. Verify with `vite-bundle-visualizer`:

```bash
npm install --save-dev vite-bundle-visualizer
```

Then `import { visualizer } from 'vite-bundle-visualizer';` in `vite.config.ts` (gated on env).

**Tip:** if a single dep is >100 KB, it's almost always a date library or an icon library. Replace with lighter alternatives.

### 4.5 Worker pool tuning

`backend/gunicorn.conf.py:12` — `WEB_CONCURRENCY=2` × `WEB_THREADS=2` = 4 concurrent. For a CPU-light IO-heavy app like Django+DRF, tune to `WEB_CONCURRENCY = 2 × CPU cores`, `WEB_THREADS = 4`. Verify with load testing.

**Tip:** `gthread` workers are fine for IO-heavy. `gevent` for very high concurrency. Don't switch worker class without load testing — switching to `gevent` breaks a lot of sync code that assumes thread-safety.

---

## Phase 5 — Process & documentation (ongoing)

### 5.1 ADRs (Architecture Decision Records)

Add `docs/adr/` with one file per decision:

```markdown
# ADR-001: Use Fernet for testimonial encryption

## Status
Accepted (2026-09-23)

## Context
Testimonial `source` and `precise_location` columns contain PII that
must not appear in DB dumps or backups.

## Decision
Use Fernet (AES-128-CBC + HMAC-SHA256) via `cryptography.fernet.Fernet`.
Key rotation via `MultiFernet`.

## Consequences
- Plaintext backup of DB alone is insufficient to decrypt these columns.
- Column queries (LIKE, full-text) are no longer possible — use a hash
  column for lookup if needed.
- Key rotation requires `MultiFernet` and a re-encrypt script.

## Alternatives considered
- Application-level AES without HMAC: rejected (no integrity).
- pgcrypto: rejected (key in DB; backup contains key).
```

**Tip:** ADRs that aren't read are worthless. Link them from CLAUDE.md so new devs see them.

### 5.2 Threat model

Document the threat model. What are you defending against?

- **Adversary A: opportunistic attacker** — scripts known CVEs, finds exposed admin panels. (Mitigations: rate limits, HTTPS, 2FA, audit logs.)
- **Adversary B: authenticated volunteer** — tries to access casework / contacts they shouldn't see. (Mitigations: C-1 fix, RBAC tests.)
- **Adversary C: insider with file read** — exfiltrates `.env`, decrypts testimonials. (Mitigations: secrets vault, key rotation.)
- **Adversary D: state-level attacker with subpoena / coercion** — targets operators, demands platform access. (Out of scope for code; mitigations are legal/policy.)

**Tip:** writing the threat model down surfaces assumptions. "We assume no one reads `/etc/testimonies-world/*.env`" is an assumption worth making explicit.

### 5.3 Runbooks

For each operational task:
- How to rotate `SECRET_KEY` (and what breaks — sessions, password reset tokens)
- How to rotate the Fernet key (and the re-encrypt migration)
- How to restore from backup (and how long it takes)
- How to fail over if the DB host (10.0.0.100) goes down
- How to revoke an Advocate's access immediately (without DB access)

**Tip:** a runbook that hasn't been drilled is a fiction. Quarterly fire drills: rotate a key, restore from backup, revoke access. Time each one. Update the runbook with what surprised you.

### 5.4 Code review checklist

Pin the SYSTEM_RULES.md rules into a PR template:

```markdown
## Pre-merge checklist
- [ ] Permission changes have a regression test
- [ ] New endpoints have audit-log calls (or documented exception)
- [ ] No secrets in code, comments, or examples
- [ ] Migrations are backwards-compatible (no `RemoveField` without multi-step)
- [ ] No `any` introduced on domain entities (Person, Report, Media, CaseworkRecord)
- [ ] Lighthouse perf budget unchanged (run local audit)
- [ ] Rollout notes updated (migrations, restart, env var changes)
```

**Tip:** checklists only work if the CI enforces them. Either add CI steps (lint for `any`, grep for secrets) or accept that humans will skip them.

### 5.5 Branch hygiene

Per SYSTEM_RULES §3: branches should be deleted after merge. Currently the repo has 4 stashes on feature branches. Either:
- Push the branch and open a PR (`git push origin fix/c7-test-cleanup && gh pr create`)
- Drop the branch (`git branch -D fix/c7-test-cleanup && git stash drop`)

Don't leave stashes around — they're silent debt.

**Tip:** `git stash push -m "wip-on-X"` then forget about it is a recipe for losing 2 days of work to a `git stash drop`. If the work matters, commit it (even on a feature branch).

---

## Quick reference — top tips per area

| Area | Tip |
|---|---|
| Secrets | Treat any on-disk secret as "we hope nobody finds it". Rotate aggressively. |
| Encryption | Encrypted columns are opaque to SQL. Add hash columns for lookups. |
| RBAC | Declare `permission_classes=` on every `@action`. Lint it in CI. |
| Audit logging | Single helper, one place. Every CRUD on sensitive tables. |
| Frontend types | `any` at the render boundary defeats the type system. Replace with existing interfaces. |
| SSR | Universal loads in `+page.ts`, not `onMount`/`$effect`. SSR-first. |
| Design tokens | If it's not in `app.css`, it shouldn't be inline. Enforce with stylelint. |
| CI | A workflow that does nothing is worse than no workflow — false confidence. |
| Docker | `USER nonroot`, `cap_drop: ALL`, `read_only: true`. Defaults. |
| systemd | Match the most-hardened unit (the backup one). Consistency = security. |
| Performance | Profile before optimizing. `CaptureQueriesContext` is your friend. |
| Process | ADRs + threat model + runbooks + drills. Code is 20% of operational security. |

---

## What "production-grade" actually means for this platform

For testimonies.world, "production-grade" is:

1. **No critical findings.** Every C-finding closed. ✅
2. **No exploitable H findings.** Every H-finding closed or documented with a compensating control. ✅
3. **Auditable.** Every change to a person / report / media / testimonial leaves a row in `AuditLog`. ✅
4. **Encryptable.** Sensitive columns are encrypted at rest with rotation. ✅
5. **Observable.** Logs, metrics, traces, alerts. SLOs defined. ✅
6. **Drilled.** Runbooks exist. Quarterly drills. Last drill time and outcome logged. ✅
7. **Documented.** ADRs, threat model, runbooks, on-call rotation. ✅
8. **Hardened.** Docker + systemd + secrets management all at the same level. ✅

That's the target. The audit gave you a list; this plan gives you a sequence. Start with Phase 0.
