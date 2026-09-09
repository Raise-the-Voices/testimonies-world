# syntax=docker/dockerfile:1.7
#
# Multi-stage build for the Django backend.
#
#   builder  — python:3.12-slim-bookworm; installs build deps for
#              Pillow + psycopg2, creates a venv at /app/.venv with
#              all runtime deps. Cached layer — changes only when
#              requirements.txt changes.
#   runtime  — slim-bookworm without build deps; copies the venv
#              from builder + the application code; drops to a
#              non-root user; wires up the entrypoint.
#
# The entrypoint (scripts/docker/entrypoint-backend.sh) waits for
# PG and Redis, then optionally runs migrations + collectstatic,
# then execs the CMD. The CMD uses gunicorn.conf.py from this
# directory, so the same image can run with whatever
# WEB_CONCURRENCY / WEB_TIMEOUT the operator sets.

# ---------- builder ----------
FROM python:3.12-slim-bookworm AS builder
WORKDIR /app

# System deps for Pillow + psycopg2. Stays out of the runtime
# image (the runtime stage installs only the shared libs).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg62-turbo-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /app/.venv \
    && /app/.venv/bin/pip install --no-cache-dir --upgrade pip \
    && /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

# ---------- runtime ----------
FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app

# Runtime-only system deps. libpq5 is the shared lib for
# psycopg2-binary (built statically into the wheel, so we
# mostly need the .so for django.utils.encoding); libjpeg
# and zlib for Pillow.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libjpeg62-turbo \
        zlib1g \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r app && useradd -r -g app -d /app app

# Copy venv (huge cache hit) and app code (smaller, layer
# order means changes to .py don't bust the venv cache).
COPY --from=builder /app/.venv /app/.venv
COPY . /app

# Match the on-host layout so whitenoise + media work the same.
# The /app/logs dir is created even though we no longer write a
# file there — kept for backward-compat with anything that expects
# the path to exist (operator scripts, future log-shipping agents).
RUN mkdir -p /app/media /app/sensitive_media /app/logs /app/staticfiles \
    && chown -R app:app /app
USER app

ENV PATH=/app/.venv/bin:$PATH \
    DJANGO_SETTINGS_MODULE=testimonies.settings \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8040

EXPOSE 8040

# Liveness — hits the /healthz view added in this PR. Uses curl
# because the runtime image installs it (and a few lines of bash
# would be heavier than a one-shot HTTP probe).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8040/healthz || exit 1

ENTRYPOINT ["scripts/docker/entrypoint-backend.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "testimonies.wsgi:application"]
