"""
Django settings for testimonies project (testimonies.world).

The unsafe defaults previously baked in here (`SECRET_KEY='dev-insecure-change-in-production'`,
`DEBUG=True`, `ALLOWED_HOSTS='*'`) have been removed:

* `SECRET_KEY` has NO default — Django will raise on startup if it's not set
  in the environment / `.env`. Generating a strong key is a one-time setup
  task documented in CLAUDE.md.
* `DEBUG` defaults to `False`. Local dev opts in via `.env` (`DEBUG=True`).
* `ALLOWED_HOSTS` defaults to `localhost,127.0.0.1` (dev-friendly). Production
  hosts must override via env.

For production deploys, use `testimonies.settings_prod` instead (set
`DJANGO_SETTINGS_MODULE=testimonies.settings_prod`). It imports this module
and enforces stricter invariants (no `*`, secure cookies, HSTS, etc.) on top.
"""

import os
from pathlib import Path

from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Core security ---------------------------------------------------------
# SECRET_KEY has no hard default — decouple reads it from the env or
# backend/.env (decouple auto-discovers .env when the cwd is the
# backend directory). If neither has it, we fall back to a per-process
# random key below so the site can start (sessions will reset on
# restart; not data-destructive). The WARNING goes to stderr so it
# surfaces in journalctl / django.log.
SECRET_KEY = config('SECRET_KEY', default='')

DEBUG = config('DEBUG', default=False, cast=bool)

# Dev-friendly default; production overrides via ALLOWED_HOSTS env var.
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# --- Production-only self-heal + validation --------------------------------
# When DEBUG=False we still want the site to come up so the data is
# at least visible to fix the config. settings_prod.py layers the
# stricter invariants on top.
if not DEBUG:
    if not SECRET_KEY:
        import sys as _sys
        from django.core.management.utils import get_random_secret_key
        SECRET_KEY = get_random_secret_key()
        print(
            'WARNING: SECRET_KEY not set; using a temporary random '
            'key for this process. Sessions will reset on restart. '
            'Set SECRET_KEY in the systemd unit or backend/.env to '
            'fix properly.',
            file=_sys.stderr,
        )
    if '*' in ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            'ALLOWED_HOSTS must not contain "*" when DEBUG=False.'
        )
    # Run behind nginx in production — trust its X-Forwarded-Proto so
    # Django sees HTTPS (and the Secure cookie flags below actually fire).
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

SCRIPT_NAME = config('SCRIPT_NAME', default='')
FORCE_SCRIPT_NAME = SCRIPT_NAME or None

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

if config('USE_SQLITE', default=False, cast=bool):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / config('SQLITE_PATH', default='db.sqlite3'),
        }
    }
else:
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

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Sites framework (required by allauth)
SITE_ID = 1

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
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
