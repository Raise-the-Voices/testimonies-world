from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from cases.views import (
    CaseCategoryViewSet,
    FamilyRelationshipViewSet,
    MediaDownloadView,
    MediaViewSet,
    PersonViewSet,
    ReportViewSet,
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
    # Permission-gated media download. Replaces Django's static() helper so
    # visibility (PUBLIC / RESTRICTED / SENSITIVE) is enforced at fetch time
    # instead of relying on file-path secrecy.
    re_path(r'^media/(?P<path>.*)$', MediaDownloadView.as_view(), name='media_download'),
]

admin.site.site_header = 'Raise the Voices — Admin'
admin.site.site_title = 'Raise the Voices'
admin.site.index_title = 'Case Management'
