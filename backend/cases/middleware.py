"""Lightweight request-id middleware.

Why a custom middleware (not a context var or signal): we want a UUID
attached to every Django request — view code, logging, and the 500
handler all need to read the same id, and middleware is the only
hook Django runs unconditionally for every request before any view.

The id is generated fresh per request and stashed on
``request.request_id``. It is intentionally NOT exposed to the
client in normal responses (no information leak) — only the 500
handler surfaces it, so a user who hits a server bug can paste the
id and an operator can ``journalctl | grep <id>`` to find the
matching traceback.

Pair with the request_id field in ``testimonies.urls.json_500`` —
that handler is what returns the id to the client.
"""

from __future__ import annotations

import uuid


class RequestIdMiddleware:
    """Attach a short UUID to every request as ``request.request_id``.

    Runs before all view code so view-level loggers and the 500
    handler can read it. No outbound side effects — does not log,
    does not set headers (a future revision can echo it in a response
    header for debugging, but that would leak it to non-500 responses
    too).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = uuid.uuid4().hex[:12]
        return self.get_response(request)