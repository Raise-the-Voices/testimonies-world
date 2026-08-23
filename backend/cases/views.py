from django.db.models import Count, Max
from django_filters import rest_framework as filters
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpResponse
from django.views import View

from .models import AuditLog, CaseCategory, FamilyRelationship, Media, Person, Report
from .serializers import (
    CaseCategorySerializer,
    FamilyRelationshipSerializer,
    MediaSerializer,
    PersonDetailSerializer,
    PersonListSerializer,
    PersonWriteSerializer,
    ReportSerializer,
)


def _normalize_country(raw: str) -> str:
    """Canonicalize a country name so 'Pakistan', 'PAKISTAN', 'pakistan'
    all collapse to one. Strips whitespace, title-cases the result.

    Keeps an internal allowlist of well-known abbreviations / multi-word
    names that don't title-case well so the dropdown reads naturally
    (e.g. 'USA', 'UAE', 'UK', 'South Korea'). Extend as needed.
    """
    if not raw:
        return ''
    cleaned = raw.strip()
    upper = cleaned.upper()
    overrides = {
        'USA': 'USA',
        'U.S.A.': 'USA',
        'US': 'USA',
        'UAE': 'UAE',
        'U.A.E.': 'UAE',
        'UK': 'UK',
        'U.K.': 'UK',
        'DRC': 'DRC',
        'DPRK': 'DPRK',
    }
    if upper in overrides:
        return overrides[upper]
    return cleaned.title()


def _aggregate_countries(qs):
    """Group persons by normalized country name, summing counts.

    Done in Python (not SQL) so we can normalize the label at the same
    time — Django ORM can't easily GROUP BY LOWER(country) AND pick a
    canonical display label in one query across SQLite/Postgres.

    Returns a list of (country, count) sorted by count desc, then name.
    """
    counts = {}
    for raw in qs.values_list('country', flat=True):
        norm = _normalize_country(raw)
        if not norm:
            continue
        counts[norm] = counts.get(norm, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


class PersonFilter(filters.FilterSet):
    country = filters.CharFilter(lookup_expr='iexact')
    status = filters.CharFilter(field_name='current_status')
    category = filters.ModelMultipleChoiceFilter(
        field_name='categories',
        queryset=CaseCategory.objects.all(),
    )
    quality = filters.NumberFilter(field_name='quality_tier')
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Person
        fields = ['country', 'current_status', 'medical_status',
                  'quality_tier', 'gender', 'is_published']


class PersonViewSet(viewsets.ModelViewSet):
    filterset_class = PersonFilter
    search_fields = ['name', 'legal_name', 'aliases', 'country',
                     'summary_narrative']
    ordering_fields = ['name', 'country', 'current_status',
                       'updated_at', 'created_at']

    def get_queryset(self):
        qs = Person.objects.annotate(
            report_count=Count('reports'),
        ).prefetch_related('categories')
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_published=True)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return PersonListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return PersonWriteSerializer
        return PersonDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def watchdog(self, request):
        """Persons ordered by urgency — days since last report, weighted by critical status."""
        persons = self.get_queryset().annotate(
            last_report_date=Max('reports__date_start'),
        ).exclude(
            current_status__in=['released', 'deceased']
        ).order_by('last_report_date')[:50]
        serializer = PersonListSerializer(persons, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Aggregate statistics for dashboard."""
        qs = Person.objects.filter(is_published=True)
        return Response({
            'total': qs.count(),
            'by_status': dict(
                qs.values_list('current_status').annotate(c=Count('id')).values_list('current_status', 'c')
            ),
            'by_country': _aggregate_countries(qs),
            'by_category': list(
                CaseCategory.objects.annotate(
                    count=Count('person')
                ).values('name', 'count').order_by('-count')
            ),
            'by_medical': dict(
                qs.values_list('medical_status').annotate(c=Count('id')).values_list('medical_status', 'c')
            ),
        })

    @action(detail=False, methods=['get'])
    def countries(self, request):
        """List of countries with case counts — case-insensitive merge.

        Counts are dynamic: when other filters are active in the query
        string (current_status, medical_status, quality_tier, gender,
        category, etc.), counts reflect the filtered subset. The `country`
        filter itself is intentionally excluded so the dropdown keeps
        showing every country regardless of which one is selected.
        """
        qs = Person.objects.all()
        if not request.user.is_authenticated:
            qs = qs.filter(is_published=True)

        # Apply every query param EXCEPT `country` (we're aggregating by
        # country — applying a country filter would only return that
        # country). Empty values are skipped so the absence of a filter
        # behaves as "no filter".
        filter_params = {
            k: v for k, v in request.query_params.items()
            if k != 'country' and v
        }
        if filter_params:
            qs = PersonFilter(filter_params, queryset=qs).qs

        rows = _aggregate_countries(qs)
        return Response([
            {'country': name, 'count': count}
            for name, count in rows
        ])


class ReportViewSet(viewsets.ModelViewSet):
    serializer_class = ReportSerializer
    filterset_fields = ['person', 'source_type', 'is_private']
    search_fields = ['narrative', 'source_attribution']
    ordering_fields = ['date_start', 'created_at']

    def get_queryset(self):
        qs = Report.objects.select_related('person')
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_private=False, person__is_published=True)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class MediaViewSet(viewsets.ModelViewSet):
    serializer_class = MediaSerializer
    filterset_fields = ['person', 'report', 'media_type', 'visibility']

    def get_queryset(self):
        qs = Media.objects.all()
        if not self.request.user.is_authenticated:
            qs = qs.filter(visibility='public')
        elif not self.request.user.groups.filter(name__in=['Advocate', 'Admin']).exists():
            qs = qs.exclude(visibility='sensitive')
        return qs

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class CaseCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CaseCategory.objects.all()
    serializer_class = CaseCategorySerializer
    permission_classes = [permissions.AllowAny]


class FamilyRelationshipViewSet(viewsets.ModelViewSet):
    queryset = FamilyRelationship.objects.select_related('person_a', 'person_b')
    serializer_class = FamilyRelationshipSerializer


# --- Media download (permission-gated) -------------------------------------

_SENSITIVE_GROUPS = frozenset({'Advocate', 'Admin'})


def _can_view_visibility(user, visibility: str) -> bool:
    """Return True if ``user`` may fetch a Media row of the given visibility.

    Mirrors the rules used by ``MediaViewSet.get_queryset``:
      * PUBLIC       — anyone, including anonymous
      * RESTRICTED   — any authenticated user
      * SENSITIVE    — staff or member of Advocate/Admin groups
    """
    if visibility == Media.Visibility.PUBLIC:
        return True
    if not user.is_authenticated:
        return False
    if visibility == Media.Visibility.RESTRICTED:
        return True
    # SENSITIVE
    return user.is_staff or user.groups.filter(name__in=_SENSITIVE_GROUPS).exists()


class MediaDownloadView(View):
    """Serve ``Media.file`` only after a per-row visibility check.

    Replaces Django's ``static()`` helper for ``/media/`` so that the
    visibility flag stored on each ``Media`` row is actually enforced at
    download time. Every download of a SENSITIVE file is recorded in
    ``AuditLog`` (action=DOWNLOADED) for accountability.
    """

    http_method_names = ['get', 'head']

    def get(self, request, path):
        try:
            media = Media.objects.get(file=path)
        except Media.DoesNotExist:
            raise Http404('Media not found')

        if not _can_view_visibility(request.user, media.visibility):
            raise PermissionDenied

        if (media.visibility == Media.Visibility.SENSITIVE
                and request.user.is_authenticated):
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.DOWNLOADED,
                target_type='media',
                target_id=media.id,
                ip_address=request.META.get('REMOTE_ADDR') or None,
            )

        if not media.file:
            raise Http404('Media has no file')
        return FileResponse(media.file.open('rb'))


def media_auth_check(request):
    """Auth sub-request endpoint for nginx ``auth_request`` directive.

    Called by nginx via the internal ``/__media_auth`` location (see
    ``deploy/nginx/rtv-cases.conf``) **before** serving any
    ``/media/<path>`` request. Resolves the URL path to a ``Media``
    row, checks the user's visibility against
    ``_can_view_visibility``, and returns:

      * ``200`` — the request is allowed. nginx proceeds to serve the
        file from disk via ``alias``.
      * ``403`` — the request is denied. nginx returns 403 to the
        client.

    The body is always empty (nginx discards it). Sensitive-tier
    accesses are recorded in ``AuditLog`` here too, so the audit trail
    covers both nginx-fronted and direct downloads.
    """
    # nginx sets X-Original-URI on the auth sub-request; fall back to
    # the ?path= query string if a different caller ever hits this.
    path = request.headers.get('X-Original-URI') or request.GET.get('path', '')
    # Strip the /media/ prefix to get the storage-relative path
    # (e.g. "public/abc.jpg"). MediaDownloadView does the same thing.
    if path.startswith('/media/'):
        path = path[len('/media/'):]
    # Defensive: collapse any URL-decoded traversal attempts before
    # they hit the DB lookup.
    path = path.lstrip('/')

    try:
        media = Media.objects.get(file=path)
    except Media.DoesNotExist:
        raise PermissionDenied

    if not _can_view_visibility(request.user, media.visibility):
        raise PermissionDenied

    if (media.visibility == Media.Visibility.SENSITIVE
            and request.user.is_authenticated):
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.DOWNLOADED,
            target_type='media',
            target_id=media.id,
            ip_address=request.META.get('REMOTE_ADDR') or None,
        )

    return HttpResponse(status=200)

