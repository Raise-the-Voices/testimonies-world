"""
Operational wiring that lives outside settings.py on purpose.

This module owns the volatile ops config (logging, cache, Sentry)
that the deploy VM is most likely to have locally tweaked. The
deploy script (scripts/deploy.sh:64-93) preserves the VM's
local settings.py across a `git reset --hard origin/main` via
`git stash push` + `git stash pop`. If main evolves the ops
config inline in settings.py, that evolution conflicts with
the VM's local settings.py on the next deploy — exactly the
failure we just hit on the dashboard-polish PR cutover
(2026-09-09 12:05 UTC).

Lifting LOGGING / CACHES / Sentry init into a separate module
means:
  - Future main changes to ops behavior don't touch the
    parts of settings.py that operators edit (ALLOWED_HOSTS,
    custom validators, HSTS, etc.) — those merge cleanly.
  - Operators can override the wiring by importing this
    module and calling the individual init functions with
    their own config (rare; the common case stays
    env-driven).
  - Tests stay green: the same init_sentry() / init_logging()
    / configure_cache() functions are called from settings.py
    after DEBUG is known.

This is a refactor of code that already lives in settings.py —
no behavior change. All knobs (REDIS_URL, SENTRY_DSN,
LOG_LEVEL, etc.) are unchanged.
"""
import logging
import logging.config
import os
from pathlib import Path


def get_logging_config(*, debug: bool) -> dict:
    """Return the LOGGING dict for settings.py.

    Settings.py assigns this to its `LOGGING` module attribute so
    Django's `setup()` configures logging from the same place.
    Idempotent — safe to call multiple times.
    """
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            # JSON for production. Container log scrapers (Loki,
            # Splunk, CloudWatch, etc.) parse this directly.
            'json': {
                '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
                'rename_fields': {'asctime': 'timestamp', 'levelname': 'level'},
            },
            # Human-readable for dev / DEBUG.
            'plain': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'plain' if debug else 'json',
                'level': os.environ.get('LOG_LEVEL', 'INFO'),
            },
        },
        'loggers': {
            # Don't spam the console with SQL statements under
            # DEBUG. Production never sets this logger anyway
            # (DEBUG=False → postgres logs are at WARNING+).
            'django.db.backends': {'level': 'WARNING'},
        },
        'root': {'handlers': ['console'], 'level': 'INFO'},
    }


def init_logging(*, debug: bool, base_dir: Path) -> None:
    """Apply the LOGGING config to the live logging module.

    Called after LOGGING has been read into settings.py — this
    side-effect is what wires stdout/stderr in production. Safe
    to call multiple times.
    """
    logging.config.dictConfig(get_logging_config(debug=debug))
    # Keep the logs/ dir creation so any external scripts that
    # write to BASE_DIR/logs/ don't break. (No app code writes
    # here anymore — the file handler is gone.)
    (base_dir / 'logs').mkdir(exist_ok=True)


def configure_cache(*, redis_url: str) -> dict:
    """Return the CACHES dict — Redis when REDIS_URL is set,
    LocMem otherwise.

    LocMem is per-process, which means with gunicorn -w 2 the
    DRF throttle counters (AnonRateThrottle / UserRateThrottle /
    ScopedRateThrottle) don't share state — the effective per-user
    rate is 2x the configured cap. Redis gives one shared counter
    and matches the production deployment. The fall-through to
    LocMem keeps `manage.py test` working without a Redis running.

    Pure function — takes the redis_url as a parameter so this
    module doesn't depend on django.conf at import time. The
    caller is settings.py, which knows REDIS_URL.
    """
    if redis_url:
        return {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': redis_url,
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                },
            },
        }
    return {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'testimonies-cache',
        },
    }


def init_sentry(*, dsn: str) -> None:
    """Sentry init — no-op when SENTRY_DSN is empty.

    PII is opt-in (send_default_pii=False) per the project's
    data policy on testimonies-world: this app handles sensitive
    human-rights PII and we don't ship that to a third-party
    service unless an operator explicitly opts in via env.

    Idempotent — sentry_sdk.init() is safe to call multiple times
    (it merges config on subsequent calls).
    """
    if not dsn:
        return
    # Local imports so this module can be imported without
    # sentry_sdk installed (tests, dev, edge cases). When SENTRY_DSN
    # is set, the operator has already opted in by installing the
    # SDK; missing-sentry errors should surface at startup.
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=dsn,
        integrations=[DjangoIntegration()],
        environment=os.environ.get('SENTRY_ENV', 'production'),
        release=os.environ.get('SENTRY_RELEASE', ''),
        traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.0')),
        send_default_pii=False,
    )
