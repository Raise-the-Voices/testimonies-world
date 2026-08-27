"""
Django settings for testimonies project (testimonies.world).
"""

import os
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

# Sensitive media stored separately
SENSITIVE_MEDIA_ROOT = BASE_DIR / 'sensitive_media'

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
os.makedirs(SENSITIVE_MEDIA_ROOT, exist_ok=True)
