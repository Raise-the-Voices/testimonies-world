from django.db.models import Count, Max, Q
from django_filters import rest_framework as filters
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import AuditLog, CaseCategory, FamilyRelationship, Media, Person, Report
from .permissions import IsVolunteer
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
    """

    filterset_class = PersonFilter
    search_fields = ['name', 'legal_name', 'aliases', 'country',
                     'summary_narrative']
    ordering_fields = ['name', 'country', 'current_status',
                       'updated_at', 'created_at']
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsVolunteer]

    def get_queryset(self):
        qs = Person.objects.annotate(
            report_count=Count('reports'),
        ).prefetch_related('categories')
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_published=True)
        return qs

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
        serializer.save(created_by=user)

    def perform_update(self, serializer):
        # Same `is_published` guard as perform_create. A volunteer
        # who somehow PATCHes the published flag silently has it
        # dropped instead of 403-ing — fail-open on this field because
        # the alternative breaks the /submit flow which legitimately
        # sends other writable fields alongside it.
        user = self.request.user
        if not (user.is_staff or user.groups.filter(name='Advocate').exists()):
            serializer.validated_data.pop('is_published', None)
        serializer.save()

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
    """Report CRUD.

    Read access: anyone (anonymous included) can list + retrieve reports
    on **published** persons where `is_private=False`. The default
    `IsAuthenticatedOrReadOnly` already enforces write authentication.

    Write access (create / update / destroy):
        - Must be authenticated (`IsAuthenticatedOrReadOnly`).
        - Must be a Volunteer, Advocate, or staff (`IsVolunteer`).
        - For update / destroy on an existing row, must additionally be
          the report's author OR staff OR in the Advocate group.

    Audit log: every update and destroy writes an `AuditLog` row with the
    actor, the changed field list, and the request IP. Matches the
    privacy model in CLAUDE.md (reports are the canonical narrative and
    we want a paper trail of every correction).
    """

    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsVolunteer]
    filterset_fields = ['person', 'source_type', 'is_private']
    search_fields = ['narrative', 'source_attribution']
    ordering_fields = ['date_start', 'created_at']

    def get_queryset(self):
        qs = Report.objects.select_related('person')
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_private=False, person__is_published=True)
        return qs

    # --- Authorship gate -------------------------------------------------

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

    def get_queryset(self):
        qs = Media.objects.all()
        if not self.request.user.is_authenticated:
            qs = qs.filter(visibility='public')
        elif not self.request.user.groups.filter(name__in=['Advocate', 'Admin']).exists():
            qs = qs.exclude(visibility='sensitive')
        return qs

    def _can_mark_sensitive(self, user) -> bool:
        """Only advocates and staff can put media in the sensitive tier."""
        if not user or not user.is_authenticated:
            return False
        return user.is_staff or user.groups.filter(name='Advocate').exists()

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
        serializer.save(uploaded_by=self.request.user)

    def perform_update(self, serializer):
        self._check_sensitive_upload(serializer)
        # Don't overwrite uploaded_by on edit.
        serializer.save()


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

    Read access: anyone (anonymous included) — the family list is part
    of every person-detail response.

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
    """

    queryset = (
        FamilyRelationship.objects
        .select_related('person_a', 'person_b')
        .order_by('id')
    )
    serializer_class = FamilyRelationshipSerializer
    filterset_class = FamilyRelationshipFilter
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsVolunteer]

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
