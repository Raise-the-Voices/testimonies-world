"""
Production settings — DJANGO_SETTINGS_MODULE=testimonies.settings_prod.

Layers production-only invariants on top of the base settings module:

  * `DEBUG` is forced to `False` regardless of the environment.
  * `ALLOWED_HOSTS` should be set explicitly — falls back to a safe
    default list if unset (logs a warning so the operator notices).
  * `SECRET_KEY` should be set — falls back to a per-process random
    key if unset (sessions will reset on restart, but the site is
    at least reachable so data is visible to fix the config).
  * Secure cookie / HTTPS / HSTS headers are set, not optional.

Use this in production by exporting:

    DJANGO_SETTINGS_MODULE=testimonies.settings_prod

In the systemd unit, gunicorn invocation, or WSGI entrypoint.

NOTE on the fallbacks: they are intentionally permissive so the site
comes up even when the systemd unit forgets to export the env vars.
This is a temporary crutch to restore data visibility — operators
should set SECRET_KEY and ALLOWED_HOSTS properly as soon as possible.
The warnings print to stderr at import time so they show up in
journalctl / django.log.
"""

import sys

from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

# Bring in everything from the base module.
from .settings import *  # noqa: F401,F403


# --- Strict invariants for production --------------------------------------

# DEBUG=False unconditionally — never honor .env here.
DEBUG = False

# ALLOWED_HOSTS default. If the operator hasn't set it (e.g. the
# systemd unit forgot to export the env var), fall back to the
# known public hostnames so the site is at least reachable. Log a
# warning so the misconfig is visible in the deploy logs.
_ALLOWED_HOSTS_DEFAULT = [
    'cases.raisethevoices.org',
    'demos.linkedtrust.us',
    'localhost',
    '127.0.0.1',
]
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(), default='')
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = list(_ALLOWED_HOSTS_DEFAULT)
    print(
        'WARNING: ALLOWED_HOSTS not set; defaulting to '
        + ', '.join(ALLOWED_HOSTS)
        + '. Set ALLOWED_HOSTS in the systemd unit or backend/.env '
        + 'to override.',
        file=sys.stderr,
    )
if '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        'ALLOWED_HOSTS must not contain "*" in production.'
    )

# SECRET_KEY default. Same pattern: fall back to a per-process
# random key if unset, so the site can start and operators can see
# the warning. Sessions will reset on restart (inconvenient but
# not data-destructive) — set SECRET_KEY properly to fix.
SECRET_KEY = config('SECRET_KEY', default='')
if not SECRET_KEY:
    from django.core.management.utils import get_random_secret_key
    SECRET_KEY = get_random_secret_key()
    print(
        'WARNING: SECRET_KEY not set; using a temporary random key '
        'for this process. Sessions will reset on restart. Set '
        'SECRET_KEY in the systemd unit or backend/.env to fix '
        'properly.',
        file=sys.stderr,
    )


# --- Secure cookie / transport hardening -----------------------------------
# These are already set by settings.py when DEBUG=False, but we re-state
# them here so a settings_prod.py diff makes the prod guarantees obvious
# and so removing them from settings.py later doesn't silently regress.

# Trust nginx's X-Forwarded-Proto (this app runs behind nginx in prod).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Redirect plain-HTTP requests to HTTPS.
SECURE_SSL_REDIRECT = True

# Cookies only sent over HTTPS.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS — tell browsers to use HTTPS for a year, including subdomains,
# and allow the domain to be submitted to the HSTS preload list.
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Don't leak Referer headers to cross-origin destinations.
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
