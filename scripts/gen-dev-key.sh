#!/usr/bin/env bash
# gen-dev-key.sh — print a fresh Fernet key for local dev.
#
# Used by the dev fallback path in cases/testimonials/encryption.py
# during the H-6 grace period (and beyond, for any developer who
# runs without TESTIMONIALS_FERNET_KEY set).
#
# Usage:
#   ./scripts/gen-dev-key.sh
#   # Then add the printed line to backend/.env:
#   TESTIMONIALS_FERNET_KEY=<printed-line>
#
# Each developer should have their OWN key. Don't share — sharing a
# dev key across machines defeats the per-host isolation.
#
# Production keys live in `/etc/testimonies-world/testimonials.key`
# (mode 0600) and are rotated via `manage.py shell -c "...rotate..."`
# — out of scope for this script.

set -euo pipefail

cd "$(dirname "$0")/../backend"
KEY=$(.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
cat <<EOF
Add to backend/.env (or your local override file):

TESTIMONIALS_FERNET_KEY=$KEY

Key generated. Each developer generates their own.
EOF
