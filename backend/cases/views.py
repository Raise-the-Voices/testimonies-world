from django.conf import settings
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Max, Q, When
from django.db.models.functions import Lower
from django.http import (
    FileResponse, HttpResponse, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponsePermanentRedirect,
)
from django.utils import timezone
from django_filters import rest_framework as filters
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import generics, permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import AuditLog, CaseCategory, CaseEvent, FamilyRelationship, Media, Person, Report, Source
from .permissions import IsVolunteer
from contacts.permissions import IsAdvocate
from .throttles import ActionScopedThrottle
from .serializers import (
    AuditLogSerializer,
    CaseCategorySerializer,
    FamilyRelationshipSerializer,
    MediaSerializer,
    PersonDetailSerializer,
    PersonListSerializer,
    PersonWriteSerializer,
    ReportInternalWriteSerializer,
    ReportSerializer,
    SourceSerializer,
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

    # --- Recency / staleness filters -----------------------------------
    # `stale` is a relative-day window ("show me cases not touched in
    # 90+ days") rather than an absolute date — that's what HR
    # advocates actually use. Internally we resolve it to
    # updated_at < now() - N days in `filter_stale` below. The
    # absolute `updated_after` / `updated_before` filters are kept
    # for power users who want exact date windows (e.g., "everything
    # between 2024-01-01 and 2024-03-31"); both can be combined
    # with `stale` — the AND is intentional.
    # `CharFilter` rather than `NumberFilter` because we want the
    # `filter_stale` method to receive the raw value and decide
    # what's valid (negative, non-numeric → ignore gracefully). Using
    # `NumberFilter` runs DRF's int validator before the method fires
    # and returns 400 for "abc", which we don't want — the filter
    # should be opt-in, never error out the whole list call.
    stale = filters.CharFilter(method='filter_stale')
    updated_after = filters.DateFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = filters.DateFilter(field_name='updated_at', lookup_expr='lte')

    class Meta:
        model = Person
        fields = ['country', 'current_status', 'medical_status',
                  'quality_tier', 'gender', 'is_published']

    def filter_stale(self, queryset, name, value):
        """`?stale=N` → persons with updated_at older than N days.

        Stale is computed against updated_at (last edit), not
        last_known_date (the date the case actually occurred) — the
        former tells you whether the record has been touched recently,
        which is what "abandoned case" means in advocate workflows.
        `last_known_date` is a property of the situation, not of our
        record-keeping.
        """
        if value is None or value == '':
            return queryset
        try:
            days = int(value)
        except (TypeError, ValueError):
            return queryset
        if days < 0:
            return queryset
        from datetime import timedelta
        from django.utils import timezone
        cutoff = timezone.now() - timedelta(days=days)
        return queryset.filter(updated_at__lt=cutoff)


# Fields on Person whose edits auto-write a CaseEvent row in
# `PersonViewSet.perform_update`. One row per changed field per save.
# All five are surfaced in the public person-detail timeline (the
# "Status history" feed on the case page). A future PR can extend
# this tuple without touching perform_update's diff logic.
_STATUS_HISTORY_FIELDS = (
    'current_status',
    'medical_status',
    'current_status_date',
    'current_status_source',
    'current_status_verification',
)


class PersonViewSet(viewsets.ModelViewSet):
    """Person CRUD.

    Read access (list / retrieve): anyone (anonymous included) can read
    published persons. `get_queryset` filters out unpublished rows for
    anonymous viewers.

    Write access (create / update / destroy):
        - Must be authenticated (`IsAuthenticatedOrReadOnly`).
        - Must be a Volunteer, Advocate, or staff (`IsVolunteer`).

    Delete is hard-delete (not soft) — Person has no provenance
    requirement like Contact does (see contacts/views.py). FKs are CASCADE
    in models.py, so deleting a Person removes its Reports (and any
    Media those Reports reference), its Media rows, and any
    FamilyRelationship rows on either end. The underlying files
    (profile image, uploaded media) are removed automatically by
    Django 3.1+'s FileField behaviour.

    Every delete writes a single `AuditLog` row capturing the snapshot
    *before* the row vanishes, so the deletion is traceable even after
    the Person row is gone.

    Filtering (django-filter):
      ?search=           text search over name, legal_name, aliases,
                          country, summary_narrative
      ?country=          exact match (case-insensitive)
      ?current_status=   exact match
      ?medical_status=   exact match
      ?quality_tier=     exact match
      ?gender=           exact match
      ?is_published=     exact match (true|false)
      ?category=         repeatable, M2M match against CaseCategory
      ?stale=N           persons whose updated_at is older than N days
                          (relative window — advocates use this to flag
                          abandoned cases)
      ?updated_after=    updated_at >= YYYY-MM-DD
      ?updated_before=   updated_at <= YYYY-MM-DD
      ?ordering=         any of: name, country, current_status,
                          updated_at, created_at (prefix with '-' for
                          descending). Default: deceased cases last,
                          then newest-submitted first. An explicit
                          ?ordering= replaces both keys — a caller who
                          asks for `name` gets a pure A-Z list with
                          deceased cases interleaved.
      ?page=N            paginated, PAGE_SIZE=10
    """

    filterset_class = PersonFilter
    search_fields = ['name', 'legal_name', 'aliases', 'country',
                     'summary_narrative']
    ordering_fields = ['name', 'country', 'current_status',
                       'updated_at', 'created_at']
    # Default ordering for the catalog. `deceased_rank` (annotated in
    # get_queryset for the list action) sorts deceased cases to the end:
    # the catalog is a call to action, and there is nothing a volunteer
    # can do for someone already confirmed dead, so those rows shouldn't
    # occupy the first page ahead of people who are still detained or
    # disappeared. Within each of the two groups the previous default —
    # newest submitted first — is preserved.
    #
    # Not listed in `ordering_fields`: that list is the allow-list for
    # caller-supplied ?ordering=, and `deceased_rank` is an internal
    # annotation, not a documented sort key. DRF only validates
    # caller-supplied values against it, so the default below is
    # unaffected.
    ordering = ['deceased_rank', '-created_at']
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsVolunteer]
    # Per-action throttles. `create` is the /submit Person POST — the
    # highest-friction, highest-spam-risk surface; cap at 10/hour.
    # Updates/destroys are mutations under the same per-user cap.
    # The default anon/user throttles from settings still apply on top
    # of these (ActionScopedThrottle only narrows the scope, doesn't
    # replace the anon/user rates).
    throttle_classes = [ActionScopedThrottle]
    throttle_scopes = {
        'create': 'submit',
        'update': 'mutation',
        'partial_update': 'mutation',
        'destroy': 'mutation',
    }

    def get_queryset(self):
        # Prefetch reverse-FK chains that PersonDetailSerializer walks on
        # every retrieve. Without these, a single person-detail request
        # triggered ~5 follow-up queries (reports, media_files, both
        # relationship sides, and the related Person on the other end of
        # each relationship). Trade-off: anonymous viewers also fetch
        # private reports + their media and then filter in Python in
        # PersonDetailSerializer.get_reports. For low-cardinality case
        # records this over-fetch is cheaper than per-row queries; if
        # profiling shows otherwise, gate the prefetch on auth.
        #
        # `select_related('created_by')` collapses the FK to User
        # (rendered as `created_by` in both PersonListSerializer and
        # PersonDetailSerializer) into the same JOIN — without it,
        # every list/detail row triggers a User fetch.
        #
        # Heavy prefetches (`reports`, `reports__media_files`, the
        # two relationship sides) are gated on `self.action` because
        # the list-shape endpoints (`watchdog`, `related`,
        # `statistics`, `countries`) return PersonListSerializer
        # which only walks `categories` + `media_files`. Prefetching
        # reports/relationships on those endpoints was a per-page
        # tax with no consumer.
        #
        # For anonymous viewers we also use a Prefetch with a
        # filtered queryset so the `is_private=False` filter in
        # PersonDetailSerializer.get_reports hits the cache instead
        # of issuing a per-row query.
        from django.db.models import Prefetch
        qs = Person.objects.select_related('created_by')
        # The `list` action renders `report_count` on
        # PersonListSerializer. We compute it in Python from the
        # `reports` prefetch in the serializer (see
        # PersonListSerializer.get_report_count) rather than
        # annotating here — `annotate(report_count=Count('reports'))`
        # adds a GROUP BY to the main SELECT that breaks
        # prefetch_related's batching for the other prefetches
        # (Django can't fold a per-row report JOIN into the same
        # query plan that the 'reports' / 'reports__media_files' /
        # 'media_files' / 'relationships_*' prefetches need to
        # traverse, so they degrade to per-row queries).
        if self.action in ('watchdog', 'related', 'statistics', 'countries'):
            # List-shape endpoints return PersonListSerializer which
            # walks categories + media_files + (for related) reports
            # (for get_report_count + get_days_since_last_report). The
            # watchdog annotation (`annotate(last_report_date=Max(...))`)
            # also reads the reports table, so we prefetch reports
            # there too. Skip reports__media_files and the two
            # relationship sides — those are detail-only.
            if self.action in ('watchdog', 'related'):
                qs = qs.prefetch_related('categories', 'media_files', 'reports')
            else:
                qs = qs.prefetch_related('categories', 'media_files')
        else:
            # list / retrieve / create / update / partial_update /
            # destroy — PersonDetailSerializer walks everything.
            if not self.request.user.is_authenticated:
                public_reports = Prefetch(
                    'reports',
                    queryset=Report.objects.filter(is_private=False),
                )
                qs = qs.prefetch_related(
                    'categories',
                    public_reports,
                    'reports__media_files',
                    'media_files',
                    # Power PersonDetailSerializer.get_status_history —
                    # timeline_events is filtered in Python by event_kind,
                    # so a flat prefetch is fine (CaseEvent indexes person
                    # + event_date, models.py:1063, so the prefetch is a
                    # single index scan per person).
                    'timeline_events',
                    'relationships_as_a__person_b',
                    'relationships_as_b__person_a',
                )
            else:
                qs = qs.prefetch_related(
                    'categories',
                    'reports',
                    'reports__media_files',
                    'media_files',
                    'timeline_events',
                    'relationships_as_a__person_b',
                    'relationships_as_b__person_a',
                )
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_published=True)

        # Sort key backing the `ordering` attribute above. Annotated for
        # EVERY action, not just `list`: GenericAPIView.get_object() runs
        # `filter_queryset(get_queryset())` too, so `retrieve`, `update`,
        # `partial_update` and `destroy` all push the default ordering
        # through OrderingFilter. Scoping this to `self.action == 'list'`
        # raises FieldError on every detail route — the annotation has to
        # exist anywhere the ordering might be applied.
        #
        # A CASE expression adds no GROUP BY of its own, so unlike the
        # Count() annotation discussed above it does not break the
        # prefetch batching. Where `watchdog` / `related` layer their own
        # aggregates on top, Django folds this column into their GROUP BY
        # harmlessly — it is functionally dependent on current_status, and
        # the primary key is already in the grouping.
        return qs.annotate(
            deceased_rank=Case(
                When(current_status=Person.Status.DECEASED, then=1),
                default=0,
                output_field=IntegerField(),
            ),
        )

    # --- Audit log helpers (mirror ReportViewSet) -------------------------

    def _client_ip(self) -> str | None:
        xff = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR')

    def _audit(self, action: str, instance: Person, details: str = '') -> None:
        AuditLog.objects.create(
            user=self.request.user if self.request.user.is_authenticated else None,
            action=action,
            target_type='person',
            target_id=instance.pk,
            details=details,
            ip_address=self._client_ip(),
        )

    def perform_destroy(self, instance):
        # Capture provenance BEFORE the row vanishes. CASCADE on
        # Report.person, Media.person, and FamilyRelationship.person_a/b
        # (cases/models.py) will delete those children + the underlying
        # files; this audit row is the only surviving trace.
        details = (
            f'name={instance.name}; '
            f'country={instance.country}; '
            f'reports={instance.reports.count()}; '
            f'media={instance.media_files.count()}; '
            f'relationships='
            f'{instance.relationships_as_a.count() + instance.relationships_as_b.count()}'
        )
        self._audit(AuditLog.Action.DELETED, instance, details)
        instance.delete()

    def get_serializer_class(self):
        if self.action == 'list':
            return PersonListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return PersonWriteSerializer
        return PersonDetailSerializer

    def perform_create(self, serializer):
        # Mass-assignment guard: `is_published` is a publication gate
        # that only staff / advocates should control. Volunteers can
        # still submit cases (the /submit page), but the rows land as
        # drafts (is_published=False). Silently drop the field rather
        # than 403-ing — the volunteer shouldn't see the request
        # fail over a field they can't see in the UI anyway.
        user = self.request.user
        if not (user.is_staff or user.groups.filter(name='Advocate').exists()):
            serializer.validated_data.pop('is_published', None)
        instance = serializer.save(created_by=user)
        # Audit-log the create (audit H-2). The other CRUD ops
        # (update, destroy, retrieve-private) were already wired;
        # create was the missing piece. Co-located with the save so a
        # DB failure on either side surfaces as a 500 to the client.
        self._audit(AuditLog.Action.EDITED, instance, 'created')

    def perform_update(self, serializer):
        # Same `is_published` guard as perform_create. A volunteer
        # who somehow PATCHes the published flag silently has it
        # dropped instead of 403-ing — fail-open on this field because
        # the alternative breaks the /submit flow which legitimately
        # sends other writable fields alongside it.
        user = self.request.user
        if not (user.is_staff or user.groups.filter(name='Advocate').exists()):
            serializer.validated_data.pop('is_published', None)
        # Status-change capture: every edit that touches one of the
        # status-ish fields writes a CaseEvent row. The whole block is
        # in a transaction so a DB failure on either side rolls back.
        # We diff after save() (rather than comparing validated_data to
        # the instance) because validated_data only carries the fields
        # the caller sent — an unchanged field would diff against the
        # new value via the instance attribute, which is the right
        # comparison.
        old_values = {
            f: getattr(serializer.instance, f)
            for f in _STATUS_HISTORY_FIELDS
        }
        with transaction.atomic():
            instance = serializer.save()
            new_values = {
                f: getattr(instance, f) for f in _STATUS_HISTORY_FIELDS
            }
            for field in _STATUS_HISTORY_FIELDS:
                if old_values[field] != new_values[field]:
                    CaseEvent.objects.create(
                        person=instance,
                        event_kind=CaseEvent.EventKind.STATUS_CHANGE,
                        event_date=timezone.now().date(),
                        description=f'{field}: {old_values[field]} → {new_values[field]}',
                        source='auto',
                        created_by=user,
                    )
            # Audit-log the update (audit H-2). Inside the atomic block
            # so the audit + CaseEvent rows either both land or both
            # roll back together with the save.
            self._audit(AuditLog.Action.EDITED, instance, 'updated')

    def retrieve(self, request, *args, **kwargs):
        # Audit-log every detail view of a Person. Anonymous retrievals are
        # already gated to `is_published=True` by `get_queryset`, so this
        # mostly captures authenticated users browsing case details —
        # which is the paper trail CLAUDE.md promises but `AuditLog.Action`
        # never actually wired up before this commit.
        instance = self.get_object()
        self._audit(AuditLog.Action.VIEWED, instance, '')
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        responses={200: PersonListSerializer(many=True)},
        description=(
            'Persons ordered by urgency — most stale first. Excludes '
            '`released` and `deceased` status. Limited to 50 rows.'
        ),
    )
    @action(detail=False, methods=['get'])
    def watchdog(self, request):
        """Persons ordered by urgency — days since last report, weighted by critical status."""
        persons = (
            self.get_queryset()
            .annotate(last_report_date=Max('reports__date_start'))
            .exclude(current_status__in=['released', 'deceased'])
            .order_by('last_report_date')[:50]
            # prefetch AFTER the slice so Django only walks categories
            # for the 50 returned rows, not every excluded/non-excluded
            # person. PersonListSerializer iterates `categories` so this
            # would otherwise be 50 follow-up queries.
            .prefetch_related('categories')
        )
        serializer = PersonListSerializer(persons, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description='Aggregated counts by status / country / category / medical status.',
                response=inline_serializer(
                    name='StatisticsResponse',
                    fields={
                        'total': serializers.IntegerField(),
                        'by_status': serializers.DictField(child=serializers.IntegerField()),
                        'by_country': serializers.ListField(child=inline_serializer(
                            name='StatisticsCountryCount',
                            fields={
                                'country': serializers.CharField(),
                                'count': serializers.IntegerField(),
                            },
                        )),
                        'by_category': inline_serializer(
                            name='CategoryCount',
                            fields={
                                'name': serializers.CharField(),
                                'count': serializers.IntegerField(),
                            },
                            many=True,
                        ),
                        'by_medical': serializers.DictField(child=serializers.IntegerField()),
                    },
                ),
            ),
        },
    )
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

    @extend_schema(
        responses=inline_serializer(
            name='CountryCountEntry',
            fields={
                'country': serializers.CharField(),
                'count': serializers.IntegerField(),
            },
            many=True,
        ),
        description=(
            'List of countries with case counts. Counts are dynamic — when '
            'other filters are present, counts reflect the filtered subset. '
            'The `country` filter itself is ignored (the dropdown always '
            'shows every country regardless of which is selected).'
        ),
    )
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

    @extend_schema(
        responses=inline_serializer(
            name='RelatedPersonsResponse',
            fields={
                # Reuse PersonListSerializer shape. Inline definition
                # would duplicate PersonListSerializer's fields — the
                # serializer referenced here is the same class the
                # /watchdog and /statistics actions return, so the
                # generated TS client types line up across endpoints.
                'results': PersonListSerializer(many=True),
            },
        ),
        description=(
            'Top related persons for the given person ID. Heuristic: '
            'published persons who share the same country OR at least '
            'one category with the target, ranked by shared-category '
            'count (descending), then same-country (descending), then '
            'most-recently-updated. The target person is excluded. '
            'Results are capped at 6.'
        ),
    )
    @action(detail=True, methods=['get'])
    def related(self, request, pk=None):
        """Top-N persons related to this one.

        Why "country OR shared category" rather than AND:
          Same-country alone is a meaningful but weak signal — two
          citizens of a country often have nothing in common. Same-
          category alone is a meaningful but weak signal — "journalist"
          is shared by journalists everywhere. Combining with OR widens
          the candidate set without forcing an artificial intersection,
          and ranking by both scores gives the strongest relationships
          the top slots. (AND would over-filter and return empty sets
          for niche categories in countries with few published persons.)

        Limits:
          - Top 6 (UI sweet spot for a sidebar — more would push the
            layout past one row on desktop).
          - Same N for any role; this endpoint isn't role-gated because
            the heuristic is the same regardless of who's asking
            (authenticated vs not affects `is_published` filter only,
            which PersonViewSet.get_queryset already handles).
        """
        target = self.get_object()

        # Pull the M2M values once so the subquery in the annotation
        # doesn't have to re-evaluate the categories list per row.
        # .all() triggers the M2M fetch; values_list('pk', flat=True)
        # gives a plain list usable in a subquery filter.
        target_category_ids = list(target.categories.values_list('pk', flat=True))

        qs = self.get_queryset().exclude(pk=target.pk)

        # Pre-filter: same country OR shared category. Without this,
        # the annotation could produce zeros for totally unrelated
        # persons — and "no related cases" is what we want for
        # unrelated matches anyway.
        if target.country:
            qs = qs.filter(Q(country=target.country) | Q(categories__in=target_category_ids))
        else:
            qs = qs.filter(categories__in=target_category_ids)

        # Annotate with the two scoring columns. The conditional
        # expression lets same_country sort work even when the target
        # has no country set (returns 0 for every row, no break).
        qs = qs.annotate(
            same_country=Case(
                When(country=target.country, then=1),
                default=0,
                output_field=IntegerField(),
            ),
            shared_categories=Count(
                'categories',
                filter=Q(categories__in=target_category_ids),
                distinct=True,
            ),
        ).distinct()

        # Rank: most-shared-categories first, then same-country, then
        # recency. The .distinct() above collapses the M2M JOIN
        # duplicates the annotation would otherwise produce.
        qs = qs.order_by('-shared_categories', '-same_country', '-updated_at')[:6]

        # prefetch_related so PersonListSerializer.categories doesn't
        # trigger N+1 over the result set. Without it, 6 rows = 6
        # follow-up queries; with it, 1 batched query.
        qs = qs.prefetch_related('categories')

        serializer = PersonListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)


class ReportFilter(filters.FilterSet):
    """Filter for `/api/reports/` used by the global `/reports` page.

    Adds explicit `date_from` / `date_to` lookups on `date_start` (the
    event date, NOT `created_at` — the latter would include back-dated
    imports in the wrong bucket). The `filterset_fields = [...]` shortcut
    only generates exact-match filters; lookup suffixes like
    `date_start__gte` are not auto-generated, so they need to be declared
    here. Query-param names (`date_from` / `date_to`) are cleaner than
    the raw `date_start__gte` / `date_start__lte` lookups and let the
    frontend stay agnostic to the underlying field name.
    """

    date_from = filters.DateFilter(field_name='date_start', lookup_expr='gte')
    date_to = filters.DateFilter(field_name='date_start', lookup_expr='lte')

    class Meta:
        model = Report
        fields = ['person', 'source_type', 'is_private']


class ReportViewSet(viewsets.ModelViewSet):
    """Report CRUD.

    Read access: anyone (anonymous included) can list + retrieve reports
    on **published** persons where `is_private=False`. The default
    `IsAuthenticatedOrReadOnly` already enforces write authentication.

    Write access (create / update / destroy):
        - Must be authenticated (`IsAuthenticatedOrReadOnly`).
        - Must be a Volunteer, Advocate, or staff (`IsVolunteer`).
        - For update / destroy on an existing row, must additionally be
          the report's author OR staff OR in the Advocate group.

    Filtering: `?search=` runs `SearchFilter` over `narrative` +
    `source_attribution`. `?source_type=`, `?person=`, `?is_private=`
    run `DjangoFilterBackend` via `ReportFilter`. `?date_from=` /
    `?date_to=` are added by `ReportFilter` for the global reports
    list page.

    Audit log: every update and destroy writes an `AuditLog` row with the
    actor, the changed field list, and the request IP. Matches the
    privacy model in CLAUDE.md (reports are the canonical narrative and
    we want a paper trail of every correction).
    """

    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsVolunteer]
    filterset_class = ReportFilter
    search_fields = ['narrative', 'source_attribution']
    ordering_fields = ['date_start', 'created_at']
    # Reports are submitted in the second leg of /submit (after the
    # Person POST). 20/hour is generous — a single submission is one
    # POST, and a volunteer editing their own reports won't approach
    # this. The cap is the spam / abuse ceiling.
    throttle_classes = [ActionScopedThrottle]
    throttle_scopes = {
        'create': 'submit_report',
        'update': 'mutation',
        'partial_update': 'mutation',
        'destroy': 'mutation',
    }

    def get_queryset(self):
        # media_files + sources reverse-FKs are iterated by their
        # nested serializers (ReportSerializer.media_files / .sources)
        # — without prefetch_related this is N+1 over every report in
        # the list. select_related('person') covers the FK lookup in
        # ReportSerializer's Person field; `created_by` is rendered by
        # the same serializer (read-only but still in the response) so
        # we add it to the same JOIN.
        qs = (
            Report.objects
            .select_related('person', 'created_by')
            .prefetch_related('media_files', 'sources')
        )
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_private=False, person__is_published=True)
        return qs

    # --- Authorship gate -------------------------------------------------

    def retrieve(self, request, *args, **kwargs):
        # Audit-log only when the report is private. Public reports are
        # noise; private reports are the canonical narrative and the
        # paper trail CLAUDE.md promises.
        instance = self.get_object()
        if instance.is_private:
            self._audit(AuditLog.Action.VIEWED, instance, 'private')
        return super().retrieve(request, *args, **kwargs)

    def _user_can_modify(self, user, instance: Report) -> bool:
        """Staff and Advocates can modify any report. Volunteers can only
        modify their own. Returns False for everyone else."""
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        if user.groups.filter(name='Advocate').exists():
            return True
        return instance.created_by_id == user.id

    # --- Audit log helpers (mirror contacts/views.py) --------------------

    def _client_ip(self) -> str | None:
        xff = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR')

    def _audit(self, action: str, instance: Report, details: str = '') -> None:
        AuditLog.objects.create(
            user=self.request.user if self.request.user.is_authenticated else None,
            action=action,
            target_type='report',
            target_id=instance.pk,
            details=details,
            ip_address=self._client_ip(),
        )

    # --- Write hooks -----------------------------------------------------

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        self._audit(AuditLog.Action.EDITED, instance, 'created')

    def perform_update(self, serializer):
        # Authorship gate (must run BEFORE save() so the failure doesn't
        # partially apply).
        if not self._user_can_modify(self.request.user, serializer.instance):
            raise PermissionDenied(
                'Only the report author, an advocate, or staff can edit this report.'
            )
        # Capture the field-level delta so the audit row tells us what
        # actually changed, not just that something did.
        before = {f: getattr(serializer.instance, f) for f in serializer.fields}
        instance = serializer.save()
        after = {f: getattr(instance, f) for f in serializer.fields}
        changed = [
            f for f in before
            if str(before[f]) != str(after[f])
        ]
        details = f'updated fields: {", ".join(changed) or "(none)"}'
        self._audit(AuditLog.Action.EDITED, instance, details)

    def perform_destroy(self, instance):
        # Authorship gate (DRF invokes perform_destroy with the already-
        # fetched instance, so we have access to it before the delete).
        if not self._user_can_modify(self.request.user, instance):
            raise PermissionDenied(
                'Only the report author, an advocate, or staff can delete this report.'
            )
        # Capture provenance BEFORE the row vanishes. CASCADE on the
        # Media FK (cases/models.py) will delete any attached media rows
        # + their underlying files; this audit row is the only surviving
        # trace of the report that was.
        person_id = instance.person_id
        self._audit(AuditLog.Action.DELETED, instance, f'person_id={person_id}')
        instance.delete()

    # --- Section M (internal) update endpoint (audit H-5) --------------
    #
    # Section M fields (risk_level, risk_concerns, risk_concerns_other,
    # internal_notes) are the operator-only risk + internal-notes
    # columns. They were previously writable by any authenticated user
    # via the volunteer ReportSerializer even though the read side
    # stripped them for non-Advocates (asymmetric gate).
    #
    # This dedicated endpoint moves the write side to a route that is
    # explicitly gated to IsAdvocate (staff or Advocate group). The
    # volunteer ReportSerializer now has those fields in
    # read_only_fields so a volunteer PATCH silently drops them — the
    # same pattern used for `is_published`.
    @action(
        detail=True, methods=['patch', 'put'],
        permission_classes=[IsAdvocate],
        serializer_class=ReportInternalWriteSerializer,
        url_path='internal',
    )
    def internal_update(self, request, pk=None):
        """PATCH/PUT Section M fields. Staff or Advocate group only.

        Body: any subset of {risk_level, risk_concerns,
        risk_concerns_other, internal_notes}. Returns the updated row
        via the full ReportSerializer (the same read shape an
        Advocate sees from /api/reports/<id>/).
        """
        instance = self.get_object()
        serializer = ReportInternalWriteSerializer(
            instance, data=request.data, partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        # Audit-log the Section M change separately from the main
        # Report update path, so the trail is explicit. Diff against
        # the prior state so the audit row carries what changed, not
        # just that something did (mirrors ReportViewSet.perform_update).
        before = {
            f: getattr(instance, f)
            for f in ReportInternalWriteSerializer.Meta.fields
        }
        # `updated` is the saved instance after our serializer wrote
        # its subset of fields — re-read to compare.
        after = {f: getattr(updated, f) for f in before}
        changed = [
            f for f in before if str(before[f]) != str(after[f])
        ]
        details = f'updated fields: {", ".join(changed) or "(none)"}'
        self._audit(AuditLog.Action.EDITED, updated, details)

        # Return the full report shape so the caller sees the Section
        # M fields they just wrote.
        return Response(ReportSerializer(updated, context={'request': request}).data)


class SourceViewSet(viewsets.ModelViewSet):
    """Standalone CRUD for Report sources.

    Most sources are created via the nested `ReportSerializer.sources`
    slot during a Report POST. This viewset exists for (a) listing
    sources across reports, (b) adding a source to an existing report,
    and (c) editing/deleting an individual source row.

    Permission: same as Report — authenticated + Volunteer. Modifying
    an existing source requires being the source's report author,
    Advocate, or staff (mirrors Report authorship gate). Reads on
    private sources are gated the same way Report reads are.
    """

    serializer_class = SourceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsVolunteer]
    filterset_fields = ['report', 'source_type', 'is_private']

    def get_queryset(self):
        qs = Source.objects.select_related('report', 'report__person')
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_private=False, report__is_private=False)
        return qs

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_private or instance.report.is_private:
            self._audit(AuditLog.Action.VIEWED, instance, 'private')
        return super().retrieve(request, *args, **kwargs)

    def _user_can_modify_source(self, user, instance: Source) -> bool:
        """Authorship gate: only the report's author, Advocate, or staff
        can modify a Source row. Mirrors ReportViewSet._user_can_modify."""
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        if user.groups.filter(name='Advocate').exists():
            return True
        return instance.report.created_by_id == user.id

    def _client_ip(self) -> str | None:
        xff = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR')

    def _audit(self, action: str, instance: Source, details: str = '') -> None:
        AuditLog.objects.create(
            user=self.request.user if self.request.user.is_authenticated else None,
            action=action,
            target_type='source',
            target_id=instance.pk,
            details=details,
            ip_address=self._client_ip(),
        )

    def perform_create(self, serializer):
        # Default report to whatever the URL filter said (or the request
        # body's `report` field). SourceSerializer has `report` as a
        # regular writable FK.
        instance = serializer.save()
        self._audit(AuditLog.Action.EDITED, instance, 'created')

    def perform_update(self, serializer):
        if not self._user_can_modify_source(self.request.user, serializer.instance):
            raise PermissionDenied(
                'Only the report author, an advocate, or staff can edit this source.'
            )
        instance = serializer.save()
        self._audit(AuditLog.Action.EDITED, instance, 'updated')

    def perform_destroy(self, instance):
        if not self._user_can_modify_source(self.request.user, instance):
            raise PermissionDenied(
                'Only the report author, an advocate, or staff can delete this source.'
            )
        report_id = instance.report_id
        self._audit(AuditLog.Action.DELETED, instance, f'report_id={report_id}')
        instance.delete()


class MediaViewSet(viewsets.ModelViewSet):
    """Media CRUD.

    Reads are gated by visibility (see `get_queryset`): anonymous sees only
    public; authenticated non-advocates see public+restricted; advocates
    and staff see everything. That's the existing behavior.

    Permission: `IsAuthenticatedOrReadOnly` — public media remains
    browsable without login (a person detail page with a public photo
    should work for anonymous viewers). Sensitive media is gated separately
    inside `perform_create` / `perform_update`: only advocates and staff
    can put a row in the `sensitive` tier. This blocks a volunteer from
    accidentally (or otherwise) marking evidence as sensitive, which
    would hide it from other volunteers mid-investigation.
    """

    serializer_class = MediaSerializer
    filterset_fields = ['person', 'report', 'media_type', 'visibility']
    # Tightened to IsVolunteer to match PersonViewSet / ReportViewSet /
    # FamilyRelationshipViewSet. The previous IsAuthenticatedOrReadOnly
    # gate let any logged-in user (even an authenticated outsider with
    # no group) upload/edit/delete media. The sensitive-tier gate inside
    # perform_create / perform_update still applies on top of this.
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsVolunteer]
    # Uploads are heavier (multipart, 50 MB cap) and a common spam
    # surface. 30/hour is a real-user ceiling — a case has maybe 1-5
    # attached media files.
    throttle_classes = [ActionScopedThrottle]
    throttle_scopes = {
        'create': 'media_upload',
        'update': 'mutation',
        'partial_update': 'mutation',
        'destroy': 'mutation',
    }

    def get_queryset(self):
        # select_related the three FKs that MediaSerializer renders as
        # nested objects (person, report, uploaded_by) so a list view
        # doesn't trigger one query per row per FK.
        qs = Media.objects.select_related('person', 'report', 'uploaded_by')
        if not self.request.user.is_authenticated:
            qs = qs.filter(visibility='public')
        elif not self.request.user.groups.filter(name__in=['Advocate', 'Admin']).exists():
            qs = qs.exclude(visibility='sensitive')
        return qs

    def retrieve(self, request, *args, **kwargs):
        # Audit-log sensitive-tier media. The sensitive tier is the
        # evidence tier — every retrieval gets a row.
        instance = self.get_object()
        if instance.visibility == Media.Visibility.SENSITIVE:
            self._audit(AuditLog.Action.VIEWED, instance, 'sensitive')
        return super().retrieve(request, *args, **kwargs)

    def _can_mark_sensitive(self, user) -> bool:
        """Only advocates and staff can put media in the sensitive tier."""
        if not user or not user.is_authenticated:
            return False
        return user.is_staff or user.groups.filter(name='Advocate').exists()

    # --- Audit log helpers (mirror the other viewsets) -------------------

    def _client_ip(self) -> str | None:
        xff = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR')

    def _audit(self, action: str, instance: Media, details: str = '') -> None:
        AuditLog.objects.create(
            user=self.request.user if self.request.user.is_authenticated else None,
            action=action,
            target_type='media',
            target_id=instance.pk,
            details=details,
            ip_address=self._client_ip(),
        )

    def _check_sensitive_upload(self, serializer):
        # When updating, the field may be omitted (partial PATCH) — fall
        # back to the existing value so we don't reject a PATCH that
        # doesn't touch visibility at all.
        visibility = serializer.validated_data.get(
            'visibility',
            getattr(serializer.instance, 'visibility', 'public'),
        )
        if visibility == Media.Visibility.SENSITIVE and not self._can_mark_sensitive(self.request.user):
            raise PermissionDenied(
                'Only advocates can upload or mark media as sensitive.'
            )

    def perform_create(self, serializer):
        self._check_sensitive_upload(serializer)
        instance = serializer.save(uploaded_by=self.request.user)
        # Audit-log the create (audit H-2). Co-located with the save
        # so a DB failure on either side surfaces as a 500.
        self._audit(AuditLog.Action.EDITED, instance, 'created')

    def perform_update(self, serializer):
        self._check_sensitive_upload(serializer)
        # Don't overwrite uploaded_by on edit.
        instance = serializer.save()
        # Audit-log the update (audit H-2).
        self._audit(AuditLog.Action.EDITED, instance, 'updated')

    def perform_destroy(self, instance):
        # Audit-log the destroy (audit H-2). The default DRF destroy
        # was silent — no paper trail when a media row was removed.
        # Capture provenance BEFORE the delete so this audit row is
        # the only surviving trace after the cascade. Mirrors the
        # shape used by PersonViewSet.perform_destroy.
        details = (
            f'visibility={instance.visibility}; '
            f'person_id={instance.person_id}; '
            f'report_id={instance.report_id}'
        )
        self._audit(AuditLog.Action.DELETED, instance, details)
        instance.delete()


class CaseCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CaseCategory.objects.all()
    serializer_class = CaseCategorySerializer
    permission_classes = [permissions.AllowAny]


class FamilyRelationshipFilter(filters.FilterSet):
    """Filter for /api/relationships/.

    `relationship_type` is a plain equality filter; `person=X` matches
    rows where X is on either side (the model has both `person_a` and
    `person_b` FKs, so a default equality on either would silently
    miss the other side).
    """

    person = filters.NumberFilter(method='filter_person')

    def filter_person(self, queryset, name, value):
        return queryset.filter(Q(person_a_id=value) | Q(person_b_id=value))

    class Meta:
        model = FamilyRelationship
        fields = ['relationship_type']


class FamilyRelationshipViewSet(viewsets.ModelViewSet):
    """Family-relationship CRUD.

    Read access: anonymous visitors can read relationships whose
    BOTH persons are published — the public case-detail page renders
    the family section for these rows. Anon reads are also gated
    server-side in `get_queryset`, so unpublished persons' family
    links never leak via this endpoint.

    Authenticated volunteers / advocates / staff read everything.

    Write access (create / update / destroy):
        - Must be authenticated (`IsAuthenticatedOrReadOnly`).
        - Must be a Volunteer / Advocate / staff (`IsVolunteer`).

    Audit log: every successful create/update/delete writes an `AuditLog`
    row with `target_type='relationship'`, mirroring the Report / Person
    / Contact viewsets. Provenance is captured *before* delete so the
    audit row survives the cascade.

    Validation: the serializer enforces no-self-link and no-duplicate-
    pair (see `FamilyRelationshipSerializer.validate`). Schema-level
    validation only — no business logic in the viewset beyond the
    gate + audit trail.

    History note (C6 + M1, reverted 2026-09-22): the previous tighten
    to `IsAuthenticated` blocked the public case-detail page from
    rendering the family sidebar. UX was chosen over the original
    C6+M1 anon-tightening; defense-in-depth is preserved by the
    `is_published=True` filter on both sides in `get_queryset`, so
    relationships involving unpublished persons remain invisible to
    anon. Operators reviewing this tradeoff: if anon should not see
    family links at all, revert permission_classes back to
    `[permissions.IsAuthenticated, IsVolunteer]` and keep the
    queryset filter (a no-op for authed viewers).
    """

    serializer_class = FamilyRelationshipSerializer
    filterset_class = FamilyRelationshipFilter
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsVolunteer]

    def get_queryset(self):
        qs = (
            FamilyRelationship.objects
            .select_related('person_a', 'person_b')
            .order_by('id')
        )
        # Same anon-defense-in-depth pattern as PersonViewSet.get_queryset:
        # anonymous viewers only see relationships whose BOTH persons are
        # published. A relationship between an unpublished draft and a
        # published case must not leak the unpublished side's name to a
        # scraper. Authenticated volunteers see everything.
        if not self.request.user.is_authenticated:
            qs = qs.filter(
                person_a__is_published=True,
                person_b__is_published=True,
            )
        return qs
    # Family-relationship writes are uncommon (1-2 per case); keep
    # them under the generic mutation cap.
    throttle_classes = [ActionScopedThrottle]
    throttle_scopes = {
        'create': 'mutation',
        'update': 'mutation',
        'partial_update': 'mutation',
        'destroy': 'mutation',
    }

    # --- Audit log helpers (mirror ContactViewSet / PersonViewSet) -------

    def _client_ip(self) -> str | None:
        xff = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR')

    def _audit(self, action: str, instance: FamilyRelationship, details: str = '') -> None:
        AuditLog.objects.create(
            user=self.request.user if self.request.user.is_authenticated else None,
            action=action,
            target_type='relationship',
            target_id=instance.pk,
            details=details,
            ip_address=self._client_ip(),
        )

    # --- Write hooks -----------------------------------------------------

    def perform_create(self, serializer):
        instance = serializer.save()
        self._audit(AuditLog.Action.EDITED, instance, 'created')

    def perform_update(self, serializer):
        # Capture the field-level delta so the audit row tells us what
        # actually changed, not just that something did. We snapshot
        # only the writable primitive fields — read-only derived
        # fields like `person_a_name` have no model attribute, and FK
        # fields need `to_representation` to give us the underlying
        # ID rather than the related object.
        before = {
            name: serializer.fields[name].to_representation(
                getattr(serializer.instance, name)
            )
            for name in serializer.fields
            if not serializer.fields[name].read_only
        }
        instance = serializer.save()
        after = {
            name: serializer.fields[name].to_representation(
                getattr(instance, name)
            )
            for name in serializer.fields
            if not serializer.fields[name].read_only
        }
        changed = [
            f for f in before
            if str(before[f]) != str(after[f])
        ]
        details = f'updated fields: {", ".join(changed) or "(none)"}'
        self._audit(AuditLog.Action.EDITED, instance, details)

    def perform_destroy(self, instance):
        # Capture provenance BEFORE the row vanishes. CASCADE on the
        # FKs will fire if either Person is later hard-deleted, but
        # the audit row is the only surviving trace of *this*
        # relationship regardless.
        details = (
            f'person_a_id={instance.person_a_id}; '
            f'person_b_id={instance.person_b_id}; '
            f'relationship_type={instance.relationship_type}'
        )
        self._audit(AuditLog.Action.DELETED, instance, details)
        instance.delete()


# --- Protected media ----------------------------------------------------
#    Routes /media/<path> through Django so we can enforce auth + the
#    matching Media.visibility tier (or, for profile images, that the
#    associated Person is published). nginx proxies /media/ to gunicorn
#    so the alias-based direct-from-disk path no longer exists. The previous
#    design — alias /opt/rtv-cases/backend/media/ + Cache-Control: public —
#    let anyone with a guessed URL download sensitive evidence files.

import os
import posixpath

from django.views import View


def _can_view_media(user, media: Media) -> bool:
    """Mirror MediaViewSet.get_queryset: anonymous sees only public;
    authenticated non-advocates see public+restricted; advocate/staff
    see everything. Centralized so the protected-media view and the
    viewset stay in sync.
    """
    if media.visibility == Media.Visibility.PUBLIC:
        return True
    if not user.is_authenticated:
        return False
    if media.visibility == Media.Visibility.RESTRICTED:
        return True
    # SENSITIVE — only advocates or staff.
    return user.is_staff or user.groups.filter(name='Advocate').exists()


class MediaDownloadView(View):
    """Authenticated media download gate at ``/media/<path>``.

    Replaces the previous function-based ``serve_protected_media`` so
    the security-critical "download a file off disk" path is a named
    class with explicit methods (``get`` only — POST/PUT/DELETE are
    405 by ``View``'s default dispatch). The previous implementation
    was a function that accepted ``(request, path)``; the URL config
    in ``testimonies/urls.py`` still passes the captured path as the
    second kwarg, which ``View.get(request, *args, **kwargs)``
    receives unchanged.

    Three buckets:

      1. ``/media/uploads/<file>`` — backed by a Media row. Visibility
         tier must permit the requester, per ``_can_view_media``.
      2. ``/media/profiles/<file>`` — legacy. Profile images now live
         under PUBLIC_MEDIA_ROOT and are served by nginx at
         ``/public-media/profiles/<file>`` with no auth gate, so this
         branch only redirects old links (indexed pages, bookmarks,
         copied image URLs) to their new home. The redirect is issued
         before the auth check below, because the target is public.
      3. Anything else — admin upload artifacts, manual imports, etc.
         Default-deny. Returning 404 (not 403) avoids leaking which
         paths exist.

    All branches audit-log sensitive downloads (matching the VIEWED
    rule for MediaViewSet / PersonViewSet).
    """

    http_method_names = ["get", "head", "options"]

    def get(self, request, *args, **kwargs):
        # The URL pattern is ``re_path(r'^media/(?P<path>.*)$', ...)``
        # so the captured path lands in kwargs. Fall back to positional
        # args for callers that pass ``path`` positionally.
        path = kwargs.get("path") or (args[0] if args else "")

        safe_path = posixpath.normpath(path).lstrip("/")
        if safe_path.startswith("..") or safe_path.startswith("/"):
            return HttpResponseNotFound()
        basename = os.path.basename(safe_path)

        # Legacy profile-image URLs. These moved to the public tree,
        # which has no auth gate, so redirect before the login check —
        # otherwise an anonymous visitor following an old link gets a
        # 401 for a file that is deliberately public. 301 so caches
        # and crawlers update.
        if safe_path.startswith("profiles/"):
            return HttpResponsePermanentRedirect(
                f"{settings.PUBLIC_MEDIA_URL}{safe_path}"
            )

        # Anything served from /media/ requires login. The auth gate
        # is the default — public files are served by nginx directly
        # at /public-media/ and never touch this view.
        if not request.user.is_authenticated:
            return HttpResponse("Authentication required.", status=401)

        # ---- Protected tiers: uploads/ (restricted) + sensitive/ ----
        # Public files live under PUBLIC_MEDIA_ROOT and are reached via
        # /public-media/ — see nginx config. They deliberately do NOT
        # pass through this gate, so an attacker with a guessed URL for
        # /media/public/<file> still gets a 404 (file not present at
        # that path) rather than an unauthenticated read.
        if safe_path.startswith("uploads/") or safe_path.startswith(
            "sensitive/"
        ):
            try:
                media = Media.objects.get(file__iendswith=basename)
            except Media.DoesNotExist:
                return HttpResponseNotFound("Not found.")

            if not _can_view_media(request.user, media):
                return HttpResponseForbidden(
                    "You do not have permission to view this media.",
                )

            if media.visibility == Media.Visibility.SENSITIVE:
                AuditLog.objects.create(
                    user=request.user,
                    action=AuditLog.Action.VIEWED,
                    target_type="media",
                    target_id=media.pk,
                    details="sensitive file download",
                    ip_address=(
                        request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
                        or request.META.get("REMOTE_ADDR")
                    ),
                )

            try:
                return FileResponse(media.file.open("rb"), filename=basename)
            except FileNotFoundError:
                return HttpResponseNotFound("File missing on disk.")

        # ---- Anything else: default-deny -----------------------------
        return HttpResponseNotFound("Not found.")


# Backwards-compat alias — ``testimonies.urls`` still names the
# function. Kept so a search for the old name returns a hit, and so
# any third-party code that imported it from this module keeps
# working until we cut over the URL config.
serve_protected_media = MediaDownloadView.as_view()


# ---------------------------------------------------------------------------
# AuditLog — staff-only read-only API powering the SvelteKit
# /dashboard/audit-logs page. Replaces the prior pattern of accessing
# audit history through Django admin only.
# ---------------------------------------------------------------------------


class AuditLogFilter(filters.FilterSet):
    """Custom filter set for AuditLog.

    django-filter's default exact-match filters cover `user__username`,
    `action`, and `target_type`. We add range filters on `timestamp`
    so the frontend can show "last 24h / last week / custom range"
    without dropping down to raw datetime strings.
    """

    timestamp_after = filters.IsoDateTimeFilter(
        field_name='timestamp', lookup_expr='gte',
    )
    timestamp_before = filters.IsoDateTimeFilter(
        field_name='timestamp', lookup_expr='lte',
    )

    class Meta:
        model = AuditLog
        fields = ['user__username', 'action', 'target_type']


class AuditLogPagination(PageNumberPagination):
    """Pagination tuned for the audit-log review page.

    Default page size is 25 (vs the global default of 10) so a reviewer
    scanning the last few weeks of activity sees a meaningful slice on
    page 1. `page_size_query_param='page_size'` lets the frontend ask
    for larger slices via `?page_size=N` (capped at `max_page_size=500`)
    so a single page can hold a week of activity at a glance without
    the user clicking "Next" 28 times.

    Why not just raise the global default? PersonViewSet and the rest
    of the API are sized for card-style list views where 10-25 rows
    fits a fold. The audit-log page is the only place that needs
    bigger pages, so the override stays scoped to this viewset.
    """

    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 500


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API for AuditLog rows.

    Permission: `IsAdminUser` (DRF built-in). Anonymous → 401,
    authenticated non-staff → 403, staff → 200. No write endpoints:
    audit rows are write-once by design (every row is created by an
    `_audit()` helper inside the originating viewset's perform_*
    method).

    Filters (via django-filter, all optional):
      ?user__username=...        exact match
      ?action=viewed|edited|...   exact match
      ?target_type=person|...    exact match
      ?timestamp_after=ISO       >= timestamp
      ?timestamp_before=ISO      <= timestamp
      ?search=...                text search over details, ip_address,
                                 user__username (DRF SearchFilter)
      ?ordering=timestamp        default is -timestamp
      ?page=N                    default page size 25
      ?page_size=N               override (capped at 500)
    """

    queryset = AuditLog.objects.select_related('user').order_by('-timestamp')
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_class = AuditLogFilter
    pagination_class = AuditLogPagination
    search_fields = ['details', 'ip_address', 'user__username']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']  # default
    # Audit-log list/retrieve is staff-only but still PII-adjacent
    # (the `details` column echoes case narratives, IPs, and user
    # activity). 120/min is 2/sec — well above a human reviewer's
    # pace; blocks scrapers that sweep the entire log.
    throttle_classes = [ActionScopedThrottle]
    throttle_scopes = {
        'list': 'audit_log',
        'retrieve': 'audit_log',
    }

    @extend_schema(
        description=(
            'Staff-only audit log. Paginated, filterable by user/action/'
            'target_type/timestamp range. Every CRUD op on a sensitive '
            'viewset writes a row here via the `_audit()` helper.'
        ),
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


# === Self-audit / debug endpoints =====================================
# These are deliberately scoped to staff — they're for the operator
# running smoke tests on the data lifecycle, not for the public UI.
# Keep them small and read-only.


class DebugRecentPersonsView(generics.ListAPIView):
    """GET /api/debug/recent-persons/ — last 5 created persons, staff-only.

    Self-audit endpoint for smoke-testing the create → DB → retrieve
    lifecycle: after a POST /api/persons/ with a unique name, hit this
    endpoint to confirm the row landed in PostgreSQL without scanning
    the full /api/persons/ list. Returns the 5 most recent persons
    (newest first) using PersonListSerializer so the response shape
    matches the public list endpoint.

    Permission: IsAdminUser (staff). Non-staff get 403. The path lives
    under /api/debug/ to make the operator-facing intent obvious and
    to keep it visually separate from production routes.

    Not paginated — the slice is hard-capped at 5 so the response
    payload is bounded regardless of caller intent.
    """

    permission_classes = [permissions.IsAdminUser]
    serializer_class = PersonListSerializer
    pagination_class = None  # we hand-pick 5; pagination_class=None disables DRF pagination

    def get_queryset(self):
        return Person.objects.order_by('-created_at')[:5]


# === Logout success / done screen =====================================
# Rendered as a plain Django view so the auth chrome (header, card,
# footer) lives in `account/logged_out.html` and matches the rest of
# /accounts/*. allauth redirects here via ACCOUNT_LOGOUT_REDIRECT_URL
# after the logout cookie is cleared.
from urllib.parse import urlparse as _urlparse
from django.shortcuts import render as _render


def logout_done(request):
    """GET /logout/done/ — success screen after the volunteer signs out.

    Reads `next` from the query string so the "Return to" button can
    take the user back where they were (e.g. `/persons/123/`). Falls
    back to the landing page if no `next` is present. The same-origin
    check is an open-redirect guard — without it, an attacker could
    craft `/logout/done/?next=https://evil.example` and use the
    success screen as a redirector.
    """
    raw_next = request.GET.get('next', '/')
    parsed = _urlparse(raw_next)
    safe_next = raw_next if (not parsed.netloc or parsed.netloc == request.get_host()) else '/'
    return _render(request, 'account/logged_out.html', {'next': safe_next})
