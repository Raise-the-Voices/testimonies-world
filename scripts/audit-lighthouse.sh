#!/usr/bin/env bash
# scripts/audit-lighthouse.sh
#
# Run Lighthouse against the Testimonies.world frontend and gate on
# category-score thresholds. Mirrors the GH Action thresholds in
# .github/workflows/audit.yml + frontend/.lighthouserc.json so local
# runs and CI runs fail on the same regressions.
#
# Usage:
#   scripts/audit-lighthouse.sh                                         # dev server :3040
#   scripts/audit-lighthouse.sh http://localhost:4173/testimonies/      # vite preview
#   scripts/audit-lighthouse.sh https://demos.linkedtrust.us/testimonies/   # staging
#   scripts/audit-lighthouse.sh <url> 90 95 95 95                       # custom thresholds
#
# Defaults (override via positional args 2..5):
#     performance >= 85, accessibility >= 95, best-practices >= 90, seo >= 90
# Set a threshold to 0 to skip that category.
#
# Output:
#   - JSON report at .audit/lighthouse-<timestamp>.json
#   - One-line PASS / FAIL summary on stdout
#   - Exit 0 on PASS, 1 on FAIL, 2 on user / environment error.
#
# First run downloads lighthouse@12 via npx (~30 MB); subsequent runs
# use the npx cache. Requires Node 22+.

set -eo pipefail

URL="${1:-http://localhost:3040/testimonies/}"
THRESH_PERF="${2:-85}"
THRESH_A11Y="${3:-95}"
THRESH_BP="${4:-90}"
THRESH_SEO="${5:-90}"
TIMEOUT_MS="${LH_TIMEOUT_MS:-60000}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$REPO_ROOT/.audit"
mkdir -p "$OUT_DIR"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT="$OUT_DIR/lighthouse-${TIMESTAMP}.json"

if ! command -v npx >/dev/null 2>&1; then
    echo "ERROR: npx not on PATH. Install Node 22+ first." >&2
    exit 2
fi

echo "Probing $URL …"
if ! curl -fsSL --max-time 5 -o /dev/null "$URL"; then
    cat >&2 <<EOF
ERROR: $URL is not reachable.

Common causes:
  - Dev server not started: run
        PUBLIC_BASE_PATH=/testimonies npm run dev
    in another shell.
  - Wrong path: the Vite dev server expects /testimonies/, not /.
  - Backend down: API-driven pages render empty content; Lighthouse still
    runs but accessibility scores may be misleading. Pass a seeded
    staging URL for a true audit.

Pass a different URL as the first arg.
EOF
    exit 2
fi

echo "Running Lighthouse against $URL (perf>=${THRESH_PERF} a11y>=${THRESH_A11Y} bp>=${THRESH_BP} seo>=${THRESH_SEO}) …"
npx -y -p "lighthouse@^12" lighthouse \
    "$URL" \
    --quiet \
    --only-categories=performance,accessibility,best-practices,seo \
    --output=json \
    --output-path="$REPORT" \
    --chrome-flags="--headless=new --no-sandbox --disable-gpu" \
    --max-wait-for-load="$TIMEOUT_MS" \
    || {
        echo "Lighthouse exited non-zero. Inspect: $REPORT" >&2
        exit 1
    }

PERF=$(python3   -c "import json;print(json.load(open('$REPORT'))['categories']['performance']['score'])")
A11Y=$(python3   -c "import json;print(json.load(open('$REPORT'))['categories']['accessibility']['score'])")
BP=$(python3     -c "import json;print(json.load(open('$REPORT'))['categories']['best-practices']['score'])")
SEO=$(python3    -c "import json;print(json.load(open('$REPORT'))['categories']['seo']['score'])")

pct() { printf '%3d' "$(awk -v s="$1" 'BEGIN{print int(s*100)}')"; }
PERF_PCT=$(pct "$PERF")
A11Y_PCT=$(pct "$A11Y")
BP_PCT=$(pct   "$BP")
SEO_PCT=$(pct  "$SEO")

echo "Scores: perf=${PERF_PCT}  a11y=${A11Y_PCT}  best-practices=${BP_PCT}  seo=${SEO_PCT}"

FAIL=0
check() {
    # $1 = actual_pct (number), $2 = threshold (number), $3 = category name.
    if [ "$2" = "0" ]; then
        echo "  skip: $3 (threshold disabled)"
        return 0
    fi
    if awk -v a="$1" -v t="$2" 'BEGIN{exit !(a+0 < t+0)}'; then
        echo "  FAIL: $3 = $1 < $2"
        FAIL=1
    else
        echo "  ok:   $3 = $1 (>= $2)"
    fi
}
echo "Thresholds:"
check "$PERF_PCT" "$THRESH_PERF" "performance"
check "$A11Y_PCT" "$THRESH_A11Y" "accessibility"
check "$BP_PCT"   "$THRESH_BP"   "best-practices"
check "$SEO_PCT"  "$THRESH_SEO"  "seo"

if [ "$FAIL" = "1" ]; then
    echo
    echo "Lighthouse audit FAILED. Full report: $REPORT"
    exit 1
fi
echo
echo "Lighthouse audit PASSED. Report: $REPORT"
