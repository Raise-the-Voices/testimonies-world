"""
Production settings — DJANGO_SETTINGS_MODULE=testimonies.settings_prod.

Layers production-only invariants on top of the base settings module:

  * `DEBUG` is forced to `False` regardless of the environment.
  * `ALLOWED_HOSTS` must be set explicitly — no default. Catches the
    "forgot to set ALLOWED_HOSTS on the new host" misconfig.
  * `SECRET_KEY` must be set (also enforced by base settings, but
    re-asserted here so the failure mode is unambiguous in prod).
  * Secure cookie / HTTPS / HSTS headers are set, not optional.

Use this in production by exporting:

    DJANGO_SETTINGS_MODULE=testimonies.settings_prod

In the systemd unit, gunicorn invocation, or WSGI entrypoint.
"""

from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

# Bring in everything from the base module.
from .settings import *  # noqa: F401,F403


# --- Strict invariants for production --------------------------------------

# DEBUG=False unconditionally — never honor .env here.
DEBUG = False

# ALLOWED_HOSTS has no default in prod; the operator must set it explicitly.
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        'ALLOWED_HOSTS must be set explicitly in production '
        '(e.g. cases.raisethevoices.org,demos.linkedtrust.us).'
    )
if '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        'ALLOWED_HOSTS must not contain "*" in production.'
    )

# SECRET_KEY must also be set. settings.py already enforces this when
# DEBUG=False, but we re-check so the prod settings module is honest
# about what it requires even if the base module's check ever changes.
SECRET_KEY = config('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured(
        'SECRET_KEY must be set in production.'
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
