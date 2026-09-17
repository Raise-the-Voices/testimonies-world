#!/usr/bin/env bash
# scripts/validate.sh
#
# Full validation pipeline: config gates → Playwright E2E → Lighthouse CI.
#
# Layers:
#   1. Config & drift gates     (Django check, migrations, OpenAPI, frontend
#                                type-check + tests — mirrors pre-push hook)
#   2. Playwright E2E           (@critical suite against a running app)
#   3. Lighthouse CI            (perf/a11y/bp/seo thresholds; reuses
#                                scripts/audit-lighthouse.sh)
#
# Usage:
#     scripts/validate.sh                                       # http://localhost:3040/testimonies/
#     scripts/validate.sh http://localhost:4173/testimonies/    # vite preview
#     scripts/validate.sh https://demos.linkedtrust.us/testimonies/   # staging
#     LAYER=1|2|3 scripts/validate.sh [url]                     # run a single layer
#     SKIP_L1=1 SKIP_L2=1 SKIP_L3=1 scripts/validate.sh …       # opt out
#
# Exit codes:
#   0  all requested layers passed
#   1  a gate failed
#   2  preflight failed (services unreachable, missing tools)
#
# The app is expected to already be running on $URL. To start a detached
# dev server before validation, set START_APP=1. The script first probes
# $URL for up to 60 s before declaring preflight failed.

set -eo pipefail

URL="${1:-http://localhost:3040/testimonies/}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACTS="$REPO_ROOT/.audit"
mkdir -p "$ARTIFACTS"

step() { printf '\n\033[36m== %s ==\033[0m\n' "$1"; }
ok()   { printf '\033[32m  ✓ %s\033[0m\n' "$1"; }
bad()  { printf '\033[31m  ✗ %s\033[0m\n' "$1"; FAILED=1; }
note() { printf '\033[33m  · %s\033[0m\n' "$1"; }
FAILED=0
LAYER_RUN="${LAYER:-123}"

# ===== Layer 0: preflight ============================================
step "Layer 0 / Preflight"
cd "$REPO_ROOT"
[ -x backend/.venv/bin/python ]             || { bad "backend/.venv/bin/python missing"; exit 2; }
[ -f frontend/node_modules/.bin/vitest ]    || { bad "frontend/node_modules missing — run 'cd frontend && npm ci'"; exit 2; }
command -v npx >/dev/null                    || { bad "npx missing — install Node 22+"; exit 2; }
command -v curl >/dev/null                   || { bad "curl missing"; exit 2; }

if [ "${START_APP:-0}" = "1" ]; then
    step "Layer 0 / Starting app (opt-in)"
    if command -v systemctl >/dev/null && \
       systemctl --user is-active tmp-testimonies-backend >/dev/null 2>&1; then
        note "tmp-testimonies-backend + tmp-testimonies-frontend already active"
    else
        (cd frontend && PUBLIC_BASE_PATH=/testimonies \
            nohup npm run dev -- --host 0.0.0.0 --port 3040 \
                >"$ARTIFACTS/dev-server.log" 2>&1 &) 2>/dev/null || true
        note "started detached dev server (logs: .audit/dev-server.log)"
    fi
fi

probe_count=0
until curl -fsSL --max-time 5 -o /dev/null "$URL"; do
    probe_count=$((probe_count+1))
    if [ "$probe_count" -ge 12 ]; then
        bad "$URL not reachable after 60 s — start the app or set START_APP=1"
        exit 2
    fi
    sleep 5
done
ok "tools present + $URL reachable (after ${probe_count} probe(s))"

# ===== Layer 1: config & drift gates ================================
if [ -z "${SKIP_L1:-}" ] && [ "$LAYER_RUN" != "2" ] && [ "$LAYER_RUN" != "3" ]; then
    step "Layer 1a / Django check + migrations drift + OpenAPI drift"
    USE_SQLITE=True DJANGO_SECRET_KEY=v-ns \
        backend/.venv/bin/python backend/manage.py check >/dev/null 2>&1 \
        && ok "Django check" || bad "Django check"
    USE_SQLITE=True DJANGO_SECRET_KEY=v-ns \
        backend/.venv/bin/python backend/manage.py makemigrations --check --dry-run >/dev/null 2>&1 \
        && ok "no missing migrations" || bad "missing migrations"
    (cd frontend && unset USE_SQLITE DJANGO_SECRET_KEY \
        && bash -c 'set -o pipefail; npm run gen:api:check' >/dev/null 2>&1) \
        && ok "openapi.yml + generated/ in sync" || bad "openapi drift"

    step "Layer 1b / Frontend type-check + tests"
    (cd frontend && npm run check) >"$ARTIFACTS/svelte-check.log" 2>&1 \
        && ok "svelte-check" || { bad "svelte-check — see .audit/svelte-check.log"; }
    (cd frontend && npm run test)  >"$ARTIFACTS/vitest.log" 2>&1 \
        && ok "vitest" || { bad "vitest — see .audit/vitest.log"; }
fi

# ===== Layer 2: Playwright E2E (--grep @critical only) ==============
if [ -z "${SKIP_L2:-}" ] && [ "$LAYER_RUN" != "1" ] && [ "$LAYER_RUN" != "3" ]; then
    step "Layer 2 / Playwright E2E ($URL)"
    cd "$REPO_ROOT/frontend"
    if [ -f node_modules/@playwright/test/package.json ]; then
        npx playwright install --with-deps chromium \
            >"$ARTIFACTS/pw-install.log" 2>&1 \
            || { bad "playwright browser install — see .audit/pw-install.log"; }
        # @critical = the ship-blocker set: auth loop, public browse, casework
        # CRUD, testimonial submit→publish. Anything tagged @regression
        # stays in the full suite, gated only on dev runs.
        PW_TEST_HTML_REPORT="$ARTIFACTS/playwright-html" \
            PW_TEST_JUNIT="$(pwd)/test-results/junit.xml" \
            npx playwright test --grep @critical \
                >"$ARTIFACTS/playwright.log" 2>&1 \
            && ok "Playwright @critical" \
            || bad "Playwright @critical — .audit/playwright.log + html report"
    else
        bad "@playwright/test not installed — 'cd frontend && npm ci'"
    fi
fi

# ===== Layer 3: Lighthouse ==========================================
if [ -z "${SKIP_L3:-}" ] && [ "$LAYER_RUN" != "1" ] && [ "$LAYER_RUN" != "2" ]; then
    step "Layer 3 / Lighthouse ($URL)"
    bash "$REPO_ROOT/scripts/audit-lighthouse.sh" "$URL" \
        >"$ARTIFACTS/lighthouse-summary.log" 2>&1 \
        && ok "Lighthouse audit" \
        || bad "Lighthouse — .audit/lighthouse-summary.log + .audit/lighthouse-*.json"
fi

# ===== Summary =======================================================
step "Summary"
if [ "$FAILED" = "1" ]; then
    bad "validation FAILED. Artefacts: $ARTIFACTS/"
    exit 1
fi
ok "validation PASSED. Artefacts: $ARTIFACTS/"
