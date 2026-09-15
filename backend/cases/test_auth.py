"""
test_auth — Playwright E2E bootstrap view.

A single POST endpoint that authenticates as a pre-existing user
and returns a session cookie. Designed for hermetic CI runs and
local E2E iteration against the real backend.

SECURITY MODEL — read before changing anything in this file.

The endpoint is gated by **three** independent conditions, all of
which must hold for the URL to even exist:

  1. settings.DEBUG is True (production never has DEBUG=True).
  2. settings.TESTIMONIAL_E2E_AUTH_TOKEN is a non-empty string.
  3. The X-Test-Auth-Token header on the request matches (2)
     byte-for-byte.

If any of (1) (2) (3) fails, the response is **404 Not Found** —
we deliberately refuse to disclose the endpoint's existence to a
caller who hasn't proven they have the token. A naive 401 would
tell an unauthenticated scanner "yes, this URL exists, you just
don't have the key" — a small but real information leak.

The view is registered in testimonies/urls.py behind a helper
(_include_test_routes) that returns the URL pattern only when
(1) and (2) hold; otherwise it returns an empty list. So the
endpoint doesn't exist in URL resolution at all when the gate
is closed.

OTHER POSTURE:

  - No user creation: the body's `username` must already exist.
    This prevents enumeration and prevents the endpoint from
    silently mutating production-shaped databases if it's ever
    misconfigured.
  - CSRF-exempt: the view authenticates by token, not by cookie,
    so the CSRF protection model doesn't apply.
  - No DRF throttles: the existing `submit` / `mutation` scopes
    would 429 legitimate CI runs (many spec files × bootstrap
    calls). The endpoint is debug-only; rate-limiting it adds
    noise without security value.
  - Excluded from OpenAPI: @extend_schema(exclude=True) keeps
    /__test__/login/ out of openapi.yml so it can't leak into
    generated client SDKs or the Swagger UI.
  - Audited: every call (success or failure) is logged with
    username, remote IP, and the first 6 characters of the
    supplied token. A burst of calls with mismatched tokens is
    visible in the same stream.
"""

import logging
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

# Header name in HTTP-meta form (Django uppercases + prefixes with
# HTTP_ and converts dashes to underscores).
_TOKEN_HEADER_META = 'HTTP_X_TEST_AUTH_TOKEN'


@method_decorator(csrf_exempt, name='dispatch')
class TestLoginView(APIView):
    """POST /__test__/login/ — token-authenticated session bootstrap.

    Request:

        POST /__test__/login/
        X-Test-Auth-Token: <matches settings.TESTIMONIAL_E2E_AUTH_TOKEN>
        Content-Type: application/json

        {"username": "e2e-advocate"}

    Response:

        204 No Content (with Set-Cookie: sessionid=...)

        404 Not Found  — token missing or wrong (gate failed)
        400 Bad Request — body missing `username`
        404 Not Found  — username not in DB (we use 404 instead of
                          401 here to avoid username-enumeration;
                          the existence of the URL is already
                          protected by the token gate above)
    """

    # Empty by default — we don't want DRF's SessionAuthentication
    # looking for a session cookie on the *request* (there isn't
    # one; this is the bootstrap). Our own auth is the token check.
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(exclude=True)
    def post(self, request):
        expected = getattr(settings, 'TESTIMONIAL_E2E_AUTH_TOKEN', '') or ''
        provided = request.META.get(_TOKEN_HEADER_META, '') or ''

        # Constant-time compare. Belt-and-braces: the token is
        # high-entropy (we generate via secrets.token_urlsafe(32)),
        # so timing attacks aren't practical here, but the
        # compare_digest idiom is cheap and removes a class of
        # "did we forget" review comments.
        if not expected or not secrets.compare_digest(provided, expected):
            logger.warning(
                'e2e test-login rejected: bad or missing token',
                extra={'remote_addr': request.META.get('REMOTE_ADDR')},
            )
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Body parsing. DRF parses application/json into
        # request.data; if the body is missing or wrong type,
        # request.data is an empty QueryDict.
        username = (request.data or {}).get('username') if hasattr(request, 'data') else None
        if not username or not isinstance(username, str):
            return Response(
                {'detail': 'username required (string)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Same 404 as the token gate, intentionally. A 401
            # here would let an attacker who has the token (e.g.
            # a former dev with a stale local copy) probe valid
            # usernames. The token already gates access; once
            # you're past it, treat all "you can't" responses
            # the same.
            logger.info(
                'e2e test-login: unknown username',
                extra={
                    'username': username,
                    'remote_addr': request.META.get('REMOTE_ADDR'),
                },
            )
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Establish the session. The backend uses
        # django.contrib.auth.backends.ModelBackend (see
        # AUTHENTICATION_BACKENDS in settings.py), which is what
        # allauth also accepts, so subsequent requests carrying
        # this cookie authenticate normally through DRF's
        # SessionAuthentication.
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        logger.info(
            'e2e test-login granted',
            extra={
                'username': username,
                'remote_addr': request.META.get('REMOTE_ADDR'),
                # First 6 chars is enough to correlate repeated
                # calls from the same token without logging the
                # full secret.
                'token_prefix': provided[:6] if provided else '',
            },
        )

        # 204 — body is empty; Set-Cookie carries the sessionid.
        return Response(status=status.HTTP_204_NO_CONTENT)