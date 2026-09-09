"""
Gunicorn config — bind via env, log to stdout/stderr (12-factor).

The systemd unit (scripts/systemd/rtv-cases-backend.service) still
passes the same gunicorn flags inline; this file is the canonical
config for the Docker image and for any future migration of the
on-host unit. Both surfaces are interchangeable.
"""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8040')}"
workers = int(os.environ.get('WEB_CONCURRENCY', '2'))
worker_class = os.environ.get('WEB_WORKER_CLASS', 'gthread')
threads = int(os.environ.get('WEB_THREADS', '2'))
timeout = int(os.environ.get('WEB_TIMEOUT', '60'))
graceful_timeout = int(os.environ.get('WEB_GRACEFUL_TIMEOUT', '30'))
keepalive = int(os.environ.get('WEB_KEEPALIVE', '5'))
max_requests = int(os.environ.get('WEB_MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.environ.get('WEB_MAX_REQUESTS_JITTER', '50'))

# 12-factor: log to stdout/stderr. Docker / k8s capture them.
accesslog = '-'
errorlog = '-'
loglevel = os.environ.get('LOG_LEVEL', 'info')
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s '
    '"%(f)s" "%(a)s" %(L)s'
)

# Forwarded header trust. Only safe because the upstream nginx
# (or compose service) is trusted to set X-Forwarded-Proto.
forwarded_allow_ips = '*'
proxy_allow_ips = '*'
