"""Test-only URLConf used by JsonErrorHandlerTests in tests_security.py.

Exposes a single route (/test-500/) whose view always raises — this
gives the handler500 test a way to drive an unhandled exception
through the WSGI stack so the JSON 500 envelope is exercised end to
end.

Never imported by the production URLConf. The test reaches it via
`override_settings(ROOT_URLCONF='cases.tests_500_urlconf')`, which
gives the test client a fresh URL resolver whose urlpatterns are
read from this module.

Why a real module and not `mock.patch` on `testimonies.urls.urlpatterns`:
Django's URL resolver caches `_url_patterns` the first time it's
constructed, so monkey-patching the list in place after import has
no effect. The cleanest way to swap urlpatterns for a single test is
to point ROOT_URLCONF at a different module — that's exactly what
`override_settings(ROOT_URLCONF=...)` is for.

The handler500/handler404 re-exports below are critical: Django's
exception handler reads `handler%s` from the URLConf module
(see django.urls.resolvers.URLResolver.resolve_error_handler),
NOT from the original ROOT_URLCONF. If we override ROOT_URLCONF
without also exporting handler500 here, Django falls back to its
default HTML error page and our JSON handlers are never exercised.

We re-export the SAME production handlers (testimonies.urls.json_500
/ json_404), so the test asserts the production wiring end-to-end:
the function the production URLConf points at is the function that
actually returns the JSON envelope.
"""
from django.urls import path

from testimonies.urls import json_404 as handler404
from testimonies.urls import json_500 as handler500

from .tests_security import _raising_view


urlpatterns = [
    # /test-500/ — the only URL this URLConf knows. The view raises
    # unconditionally so handler500 above gets invoked.
    path('test-500/', _raising_view),
]
