"""
Django settings for testimonies project (testimonies.world).
"""

import os
import sys
from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='dev-insecure-change-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

SCRIPT_NAME = config('SCRIPT_NAME', default='')
FORCE_SCRIPT_NAME = SCRIPT_NAME or None

# TLS is terminated upstream by Cloudflare/Caddy on the hypervisor; nginx on
# this VM only sees plain HTTP on loopback. Tell Django to trust the
# X-Forwarded-Proto header so request.is_secure() reflects the public scheme.
# Required for allauth to build OAuth redirect_uri values as https:// —
# otherwise Google rejects the handshake with `redirect_uri_mismatch`
# (2026-08-27 outage on cases.raisethevoices.org).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# --- Cookie + transport security ---------------------------------------
# Defaults are safe (HTTPS-only, SameSite=Lax) for any DEBUG=False
# deployment. We pin them explicitly rather than relying on Django's
# auto-derived defaults — explicit settings make the security posture
# auditable from a single grep.
#
# Test-environment note: the .env on this VM sets DEBUG=False (matching
# prod), but the Django test client runs over plain HTTP and can't
# `Set-Cookie: Secure` or follow SECURE_SSL_REDIRECT. So we disable
# the runtime-only settings (cookie-secure, ssl-redirect) under the
# test runner; HSTS settings are kept because they're response headers
# — test client ignores them.
#
# `not DEBUG` is preserved as the default so a real prod deploy
# (DEBUG=False) gets the hardened behavior automatically.

_IS_TEST_RUNNER = 'test' in sys.argv
_PROD_HARDEN = not DEBUG and not _IS_TEST_RUNNER

SESSION_COOKIE_SECURE = _PROD_HARDEN
CSRF_COOKIE_SECURE = _PROD_HARDEN
SESSION_COOKIE_HTTPONLY = True  # not a default in older Django versions
CSRF_COOKIE_HTTPONLY = False     # JS needs to read the CSRF cookie
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# HSTS — once a browser has seen the header, all subsequent
# requests to the domain must be HTTPS for the configured lifetime.
# 1 year is the recommended production floor. Include subdomains
# since cases.raisethevoices.org lives on the same infra as other
# properties (e.g. help.raisethevoices.org) that share the same
# CA / cert chain.
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Always redirect plain-HTTP requests to HTTPS. Disabled in tests
# (the test client can't follow TLS redirects on a plain-HTTP loopback).
SECURE_SSL_REDIRECT = _PROD_HARDEN

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    # Third party
    'rest_framework',
    'django_filters',
    'corsheaders',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    # Our apps
    'cases',
    'casework',
    'contacts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'testimonies.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'testimonies' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'testimonies.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('PG_DB', default='testimonies_world'),
        'USER': config('PG_USER', default='testimonies'),
        'PASSWORD': config('PG_PASSWORD', default=''),
        'HOST': config('PG_HOST', default='10.0.0.100'),
        'PORT': config('PG_PORT', default='5432'),
    }
}

# The shared dev Postgres user lacks CREATEDB, and the schema is portable
# (no PG-specific features), so the test runner swaps to SQLite. Detect
# `manage.py test` via sys.argv; opt out with USE_POSTGRES_FOR_TESTS=1
# (e.g. in CI with a superuser). NAME is a string here so Django's PG
# connection code never tries to parse it as a SQL identifier.
import sys as _sys
if (
    'test' in _sys.argv
    and not config('USE_POSTGRES_FOR_TESTS', default=False, cast=bool)
):
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'test_db.sqlite3'),
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = f'{SCRIPT_NAME}/static/' if SCRIPT_NAME else '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Project-level static dir (auth.css for the allauth templates lives here).
# App-level static/ dirs are still picked up automatically because TEMPLATES
# has APP_DIRS=True — equivalent for staticfiles is the default Finder.
STATICFILES_DIRS = [BASE_DIR / 'testimonies' / 'static']
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Media files
MEDIA_URL = f'{SCRIPT_NAME}/media/' if SCRIPT_NAME else '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Sensitive media stored separately
SENSITIVE_MEDIA_ROOT = BASE_DIR / 'sensitive_media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Sites framework (required by allauth)
SITE_ID = 1

# Email — used by casework notifications. Console backend in dev prints to
# stdout (look for "Subject:" lines). In prod we route through Migadu, an
# external transactional mailer — chosen over a self-hosted Postfix to
# avoid deliverability / spam-classification risk on our IP range.
#
# Migadu SMTP (see https://migadu.com/guides/ for canonical recipe):
#   host:   smtp.migadu.com
#   port:   465 with implicit SSL  (recommended)
#         | 587 with STARTTLS        (fallback if 465 is blocked)
#   auth:   full mailbox email address + password
#   from:   must live on the same domain as the mailbox or messages will
#           be sent "on behalf of" and look spammy to recipients
#
# To enable in prod, set in .env:
#   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
#   EMAIL_HOST=smtp.migadu.com
#   EMAIL_PORT=465
#   EMAIL_USE_SSL=True
#   EMAIL_USE_TLS=False
#   EMAIL_HOST_USER=noreply@<migadu-domain>
#   EMAIL_HOST_PASSWORD=<mailbox password>     # never commit
#   DEFAULT_FROM_EMAIL=Testimonies.world <noreply@<migadu-domain>>
#
# Never commit SMTP credentials. .env is gitignored; .env.example lists
# the keys without values.
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default='587', cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
# EMAIL_USE_TLS is STARTTLS (typically port 587). EMAIL_USE_SSL is implicit
# TLS (typically port 465). Set exactly one — they're mutually exclusive.
# Dev defaults to STARTTLS so a hypothetical future 587-only environment
# works out of the box; production sets EMAIL_USE_SSL=True for Migadu.
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
# Defensive cap so a hung SMTP handshake can't tie up a gunicorn worker
# indefinitely. Django's default is None (system default, ~minutes).
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=15, cast=int)
DEFAULT_FROM_EMAIL = config(
    'DEFAULT_FROM_EMAIL',
    default='Testimonies.world <noreply@linkedtrust.us>',
)

# Public base URL used in notification email bodies. Honored by the
# casework notifications module — keep this in sync with the deploy target.
SITE_URL = config('SITE_URL', default='https://demos.linkedtrust.us/testimonies')

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    # Rate limiting — protects against scrapers enumerating /api/persons/?
    # search= and authenticated spammers POSTing /submit. Limits are
    # generous enough not to trip real users but block obvious abuse:
    #   - anon: 60 reads/min — covers a normal anon browser session
    #     (catalog + a few detail views) without false positives
    #   - user: 600 reads/min — 10/sec, well above any human pace
    # Per-view overrides via `throttle_scope` on a per-action basis if
    # a future endpoint needs a different rate.
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/minute',
        'user': '600/minute',
    },
}

# --- OpenAPI schema (drf-spectacular) -----------------------------------
# The frontend's `gen:api` script (see frontend/package.json) calls
# `manage.py spectacular --file openapi.yml` and feeds the result to
# `orval` to generate TypeScript types + Zod schemas. CI runs
# `gen:api:check` on every PR; if the freshly-generated TS differs
# from the committed copy, the build fails — that's the drift gate.
#
# COMPONENT_SPLIT_REQUEST is critical: DRF PATCH serializers often have
# different fields than GET serializers (write_only for input, read_only
# for output). Without this split, orval would generate one merged type
# and PATCH requests would either fail validation (extra fields) or
# silently drop fields (missing required).
SPECTACULAR_SETTINGS = {
    'TITLE': 'Testimonies.world API',
    'DESCRIPTION': (
        'Casework platform for documenting human rights cases. '
        'Sensitive endpoints (contacts, sensitive media) require authentication.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'GENERIC_ADDITIONAL_PROPERTIES': False,
    'TAGS': [
        {'name': 'persons', 'description': 'Person records (cases) — read public, write auth'},
        {'name': 'media', 'description': 'Media files (photos, videos, documents, links)'},
        {'name': 'reports', 'description': 'Chronological reports on a person'},
        {'name': 'relationships', 'description': 'Family relationships between persons'},
        {'name': 'contacts', 'description': 'Always-private contact records (advocate-only)'},
        {'name': 'casework', 'description': 'Casework records (advocacy actions)'},
        {'name': 'categories', 'description': 'Case categories'},
        {'name': 'session', 'description': 'Current session / authentication'},
    ],
}

# CORS — allow SvelteKit dev server
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3040,http://127.0.0.1:3040'
).split(',')
CORS_ALLOW_CREDENTIALS = True

# CSRF — trust SvelteKit origin
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:3040,http://127.0.0.1:3040,https://demos.linkedtrust.us,https://cases.raisethevoices.org'
).split(',')

# Auth — allauth with Google OAuth
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
LOGIN_REDIRECT_URL = f'{SCRIPT_NAME}/' if SCRIPT_NAME else '/'
LOGOUT_REDIRECT_URL = f'{SCRIPT_NAME}/' if SCRIPT_NAME else '/'
ACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_LOGIN_ON_GET = True
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGOUT_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True

# Google OAuth — configure client_id and secret in Django admin → Social Applications
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': config('GOOGLE_CLIENT_ID', default=''),
            'secret': config('GOOGLE_CLIENT_SECRET', default=''),
        },
    },
}

# Cookie paths for subdir deployment
if SCRIPT_NAME:
    SESSION_COOKIE_PATH = SCRIPT_NAME + '/'
    CSRF_COOKIE_PATH = SCRIPT_NAME + '/'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
        },
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Create log directory
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
os.makedirs(SENSITIVE_MEDIA_ROOT, exist_ok=True)
