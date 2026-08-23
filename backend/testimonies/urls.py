from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.defaults import page_not_found, server_error
from rest_framework.routers import DefaultRouter

from cases.views import (
    CaseCategoryViewSet,
    FamilyRelationshipViewSet,
    MediaDownloadView,
    MediaViewSet,
    PersonViewSet,
    ReportViewSet,
    media_auth_check,
)
from casework.views import CaseworkRecordViewSet
from contacts.views import ContactViewSet

router = DefaultRouter()
router.register(r'persons', PersonViewSet, basename='person')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'media', MediaViewSet, basename='media')
router.register(r'categories', CaseCategoryViewSet, basename='category')
router.register(r'relationships', FamilyRelationshipViewSet, basename='relationship')
router.register(r'casework', CaseworkRecordViewSet, basename='casework')
router.register(r'contacts', ContactViewSet, basename='contact')


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


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/session/', session_info),
    path('accounts/', include('allauth.urls')),
    # nginx auth_request sub-request endpoint (C4). Declared BEFORE the
    # catch-all /media/<path> so that /media/_auth_check resolves here,
    # not to MediaDownloadView with path='_auth_check'.
    path('media/_auth_check', media_auth_check, name='media_auth_check'),
    # Permission-gated media download. Replaces Django's static() helper so
    # visibility (PUBLIC / RESTRICTED / SENSITIVE) is enforced at fetch time
    # instead of relying on file-path secrecy. Also used as a safety net
    # when nginx auth_request is bypassed (e.g. local dev server).
    re_path(r'^media/(?P<path>.*)$', MediaDownloadView.as_view(), name='media_download'),
]


# --- Error handlers -------------------------------------------------------
# Django's default 404/500 pages are HTML and leak template variables, request
# paths, and (in DEBUG=True) full stack traces. For /api/* we return JSON so
# the SvelteKit frontend can parse the error instead of receiving an HTML
# blob; for everything else (/admin/, /accounts/, ...) we keep Django's
# default behavior so the admin and browser-driven flows keep working.


def _wants_json(request) -> bool:
    """True for /api/* paths where the SPA expects JSON responses."""
    return request.path.startswith('/api/')


def api_not_found(request, exception=None):
    if _wants_json(request):
        return JsonResponse(
            {'detail': 'Not found', 'path': request.path},
            status=404,
        )
    return page_not_found(request, exception)


def api_server_error(request):
    if _wants_json(request):
        # Never include the exception text or traceback in the response body.
        return JsonResponse(
            {'detail': 'Internal server error'},
            status=500,
        )
    return server_error(request)


handler404 = 'testimonies.urls.api_not_found'
handler500 = 'testimonies.urls.api_server_error'


admin.site.site_header = 'Raise the Voices — Admin'
admin.site.site_title = 'Raise the Voices'
admin.site.index_title = 'Case Management'
