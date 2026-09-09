"""
Liveness probe for Docker / k8s / load balancers.

Returns 200 with `{"ok": true, "db": "ok", "cache": "ok"}` when
both the database and cache backends respond to a trivial query;
503 with details on failure. Does NOT check external services
(no PG TCP probe, no Redis TCP probe) — those are caught at the
connection level by the engine on first query and would surface
as 500s before this view runs.
"""
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def healthz(request):
    """DB + cache liveness. Cheap by design: each check is a
    single round-trip with no test data, no auth, no CSRF.
    """
    db_ok = True
    cache_ok = True
    details: dict = {}

    # DB
    try:
        with connection.cursor() as c:
            c.execute('SELECT 1')
            c.fetchone()
    except Exception as e:  # noqa: BLE001 — health checks must catch all
        db_ok = False
        # Cap the message so a noisy DB error doesn't bloat the
        # response body (200/503 are both JSON).
        details['db_error'] = str(e)[:200]

    # Cache
    try:
        cache.set('__healthz__', '1', 5)
        if cache.get('__healthz__') != '1':
            cache_ok = False
    except Exception as e:  # noqa: BLE001
        cache_ok = False
        details['cache_error'] = str(e)[:200]

    ok = db_ok and cache_ok
    return JsonResponse(
        {
            'ok': ok,
            'db': 'ok' if db_ok else 'fail',
            'cache': 'ok' if cache_ok else 'fail',
            **details,
        },
        status=200 if ok else 503,
    )
