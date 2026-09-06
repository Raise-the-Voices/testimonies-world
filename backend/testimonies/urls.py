from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from cases.views import (
    CaseCategoryViewSet,
    FamilyRelationshipViewSet,
    MediaViewSet,
    PersonViewSet,
    ReportViewSet,
    serve_protected_media,
)
from casework.views import (
    CaseworkRecordViewSet,
    NotificationViewSet,
    UserPreferenceViewSet,
)
from contacts.views import ContactViewSet

router = DefaultRouter()
router.register(r'persons', PersonViewSet, basename='person')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'media', MediaViewSet, basename='media')
router.register(r'categories', CaseCategoryViewSet, basename='category')
router.register(r'relationships', FamilyRelationshipViewSet, basename='relationship')
router.register(r'casework', CaseworkRecordViewSet, basename='casework')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'preferences', UserPreferenceViewSet, basename='preference')
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
    re_path(r'^media/(?P<path>.*)$', serve_protected_media, name='protected-media'),
]

if settings.DEBUG:
    # In DEBUG, keep Django's media serving for collectstatic-style
    # convenience. The protected view is still authoritative — these
    # static() URLs only run when DEBUG=True (i.e. local dev).
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'Raise the Voices — Admin'
admin.site.site_title = 'Raise the Voices'
admin.site.index_title = 'Case Management'
