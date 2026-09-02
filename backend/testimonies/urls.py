from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from cases.views import (
    CaseCategoryViewSet,
    FamilyRelationshipViewSet,
    MediaViewSet,
    PersonViewSet,
    ReportViewSet,
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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'Raise the Voices — Admin'
admin.site.site_title = 'Raise the Voices'
admin.site.index_title = 'Case Management'
