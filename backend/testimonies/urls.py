from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from cases.testimonials.views import (
    TestimonialTagViewSet,
    TestimonialViewSet,
)
from cases.views import (
    AuditLogViewSet,
    CaseCategoryViewSet,
    DebugRecentPersonsView,
    FamilyRelationshipViewSet,
    MediaDownloadView,
    MediaViewSet,
    PersonViewSet,
    ReportViewSet,
    SourceViewSet,
    logout_done,
)
from cases.dashboard import DashboardViewSet
from casework.views import (
    CaseworkRecordViewSet,
    NotificationViewSet,
    UserPreferenceViewSet,
)
from contacts.views import ContactViewSet
from .healthz import healthz

router = DefaultRouter()
router.register(r'persons', PersonViewSet, basename='person')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'media', MediaViewSet, basename='media')
# /api/sources/ — sources attached to a Report. Most are created via
# the nested ReportSerializer.sources slot, but this endpoint supports
# standalone CRUD for editing/listing.
router.register(r'sources', SourceViewSet, basename='source')
router.register(r'categories', CaseCategoryViewSet, basename='category')
router.register(r'relationships', FamilyRelationshipViewSet, basename='relationship')
router.register(r'casework', CaseworkRecordViewSet, basename='casework')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'preferences', UserPreferenceViewSet, basename='preference')
router.register(r'contacts', ContactViewSet, basename='contact')
# /api/audit-logs/ — staff-only read-only audit log powering the
# SvelteKit /dashboard/audit-logs page. See AuditLogViewSet in
# cases/views.py for filter/permission details.
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')
# /api/dashboard/ — role-scoped aggregator for the SvelteKit
# /dashboard page. See cases/dashboard.py for the role scoping rules.
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
# /api/testimonials/ — publication-facing wrappers around cases.
# Transition actions (/submit/, /approve/, /reject/, /publish/,
# /archive/) and the encrypted-source endpoints are detailed in
# cases/testimonials/views.py.
router.register(r'testimonials', TestimonialViewSet, basename='testimonial')
router.register(r'testimonial-tags', TestimonialTagViewSet, basename='testimonial-tag')


def session_info(request):
    """Return current user info for the SvelteKit frontend."""
    if request.user.is_authenticated:
        groups = list(request.user.groups.values_list('name', flat=True))
        return JsonResponse({
            'authenticated': True,
            'username': request.user.username,
            'email': request.user.email,
            'groups': groups,
            'is_staff': request.user.is_staff,
        })
    return JsonResponse({'authenticated': False})


# --- Custom JSON error handlers (C2 hardening) -------------------------
# Django's defaults render an HTML 404 / 500 page. The SvelteKit
# frontend treats every response as JSON and rejects anything else
# on /api/* — so an HTML 404 on, say, /api/persons/999/ makes the
# frontend log a noisy parse error instead of surfacing a clean
# "not found". Worse, the default 500 page echoes the request path,
# query string, and (under DEBUG) the full Python traceback — enough
# to fingerprint installed packages and read local variables in the
# failing frame.
#
# These handlers return a stable JSON envelope with no request
# details. The real traceback still lands in Sentry / journald via
# the logging wiring in testimonies/ops.py — operators see it, the
# anonymous HTTP client doesn't.
#
# The string dotted paths below are what Django's URL resolver
# actually uses (not the function objects). Setting them at module
# level is what makes them the ROOT_URLCONF-wide handler404/500 —
# the same pattern Django's docs recommend.

def json_404(request, exception=None):
    """404 handler. Returns JSON, never the request path.

    Django's default 404 page renders the offending path verbatim
    inside the page body. Echoing the path back is convenient for
    debugging but leaks routing structure to probes — e.g. hitting
    /api/admin/foo/ confirms /admin/ is on the same host. We omit
    the path entirely; the status code is enough for the client
    to recover.
    """
    return JsonResponse(
        {'error': 'Not found', 'status': 404},
        status=404,
    )


def json_500(request):
    """500 handler. Returns JSON, never the traceback or path.

    Django's debug 500 page (DEBUG=True) renders the full Python
    traceback — local variables, package versions, the query
    string, the request body, everything in the failing frame.
    Even DEBUG=False still includes the exception type and
    request.path in the standard 500 template, which is enough
    to fingerprint routing and installed apps.

    We return a stable envelope and nothing else. The real
    traceback is captured by Django's logger + Sentry (config in
    testimonies/ops.py). Operators see it via journalctl; an
    anonymous HTTP client doesn't get a single byte of it.
    """
    return JsonResponse(
        {'error': 'Server error', 'status': 500},
        status=500,
    )


handler404 = 'testimonies.urls.json_404'
handler500 = 'testimonies.urls.json_500'


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    # /api/debug/recent-persons/ — staff-only self-audit endpoint for
    # smoke-testing the create → DB → retrieve lifecycle. Registered
    # as a plain URL (not via router.register) because
    # DebugRecentPersonsView is a generics.ListAPIView, not a
    # ViewSet. See cases/views.py.
    path(
        'api/debug/recent-persons/',
        DebugRecentPersonsView.as_view(),
        name='debug-recent-persons',
    ),
    path('api/session/', session_info),
    # /logout/done/ — success screen rendered after allauth clears
    # the session cookie. See logout_done() in cases/views.py and
    # ACCOUNT_LOGOUT_REDIRECT_URL in settings.
    path('logout/done/', logout_done, name='logout-done'),
    path('accounts/', include('allauth.urls')),
    # OpenAPI schema — generated by drf-spectacular from the live
    # serializer/viewset introspection. The frontend's `npm run gen:api`
    # downloads `/api/schema/` and feeds it to `orval` to produce TS
    # types + Zod schemas (see frontend/orval.config.ts).
    #
    # The swagger-ui and redoc views are dev-only — they pull from a
    # CDN-sidecar bundle (drf_spectacular_sidecar) which would bloat
    # prod for no benefit. Guard with DEBUG.
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/schema/swagger-ui/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path(
        'api/schema/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc',
    ),
    # Protected media — see serve_protected_media() in cases/views.py.
    # Authenticated only; visibility-tier check is performed inside
    # the view so sensitive / restricted media can't be downloaded by
    # guessing the filename. Nginx proxies /media/ to gunicorn; this
    # route handles the actual access-control + file streaming.
    #
    # The trailing `(?P<path>.*)` (not Django's `<path:path>`) is what
    # makes `/media/` itself match. `<path:path>` rejects the empty
    # match, so a bare `/media/` request would otherwise fall through
    # to Django's 404 handler — and the prod deploy smoke test (see
    # scripts/deploy.sh) explicitly checks for 401 here to prove that
    # nginx is routing `/media/` to Django instead of serving files
    # straight off disk (the alias-based setup that was replaced on
    # 2026-08-27). 401 = the auth gate fired; 404 = nginx/Django are
    # mis-wired and we'd be back to leaking filenames.
    re_path(r'^media/(?P<path>.*)$', MediaDownloadView.as_view(), name='protected-media'),
    # /healthz — liveness probe. Used by Docker HEALTHCHECK, k8s
    # liveness probes, and load balancers. Returns 200 with
    # `{ok, db, cache}` or 503 on failure. The nginx config
    # (/docker/nginx.conf) does NOT proxy this path publicly;
    # only the container-to-container `backend` upstream is
    # allowed to hit it.
    path('healthz', healthz, name='healthz'),
]

if settings.DEBUG:
    # In DEBUG, keep Django's media serving for collectstatic-style
    # convenience. The protected view is still authoritative — these
    # static() URLs only run when DEBUG=True (i.e. local dev).
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# E2E test-only routes. See cases/test_auth.py for the security
# model and settings.py for the gating env vars
# (ENABLE_E2E_TEST_AUTH + TESTIMONIAL_E2E_AUTH_TOKEN).
#
# The URL is registered ONLY when both are set to truthy values.
# In any other configuration (production, or local without a
# token), the URL pattern is not added and requests fall through
# to Django's 404 — refusing to disclose the endpoint's existence.
#
# This block is intentionally OUTSIDE the `if settings.DEBUG:`
# branch above: we want this surface to be reachable on local
# + CI runners that run DEBUG=False for prod parity, as long as
# the dedicated E2E gate is on.
if (
    getattr(settings, 'ENABLE_E2E_TEST_AUTH', False)
    and getattr(settings, 'TESTIMONIAL_E2E_AUTH_TOKEN', '')
):
    from cases.test_auth import TestLoginView
    urlpatterns += [
        path('__test__/login/', TestLoginView.as_view(), name='test-login'),
    ]

admin.site.site_header = 'Raise the Voices — Admin'
admin.site.site_title = 'Raise the Voices'
admin.site.index_title = 'Case Management'
