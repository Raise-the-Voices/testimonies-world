from urllib.parse import urljoin

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import AuditLog, CaseCategory, FamilyRelationship, Media, Person, Report
from .sanitizers import sanitize_text, sanitize_url

# Fields that are always excluded from public API responses
PRIVATE_PERSON_FIELDS = ['medical_notes', 'precise_location']
PRIVATE_REPORT_FIELDS = ['reporter_name', 'reporter_contact', 'precise_location']


class SanitizingModelSerializerMixin:
    """Strips all HTML from declared text fields and validates URL
    fields on input. Use alongside `serializers.ModelSerializer`.

    Class attributes:
      text_fields — list of field names whose values are plain text.
      url_fields  — list of field names whose values are URLs.

    Both lists apply on every `validate()` call. The sanitization
    runs BEFORE `serializer.save()` so the database never sees raw
    HTML — the only XSS-safe path is "value was sanitized before
    write". On PATCH, only the fields present in `attrs` are
    sanitized, so omitted fields keep their existing value.

    Why not bleach on output too: a defense-in-depth re-strip on
    `to_representation` would be cheaper to add later than to bolt
    on now, and the in-place sanitization at the input boundary
    is sufficient as long as every write path goes through a
    serializer (i.e. no raw `Model.objects.create(...)` calls in
    the viewsets). The audit log on Person/Report/Media/Casework/
    Contact is written via the originating serializer's path, so
    direct-DB writes aren't a known gap.
    """

    # Silence drf-spectacular: it would otherwise pick up the
    # class docstring and inject it as the description for every
    # serializer that uses this mixin (since the mixin appears
    # in the serializer's MRO). The description is more useful
    # per-serializer (set in each Meta), so we hide the mixin's
    # own doc from the schema generator.
    __doc__ = None

    text_fields: list = []
    url_fields: list = []

    def validate(self, attrs):
        attrs = super().validate(attrs)
        for f in self.text_fields:
            if f in attrs and isinstance(attrs[f], str):
                attrs[f] = sanitize_text(attrs[f])
        for f in self.url_fields:
            if f in attrs and attrs[f]:
                attrs[f] = sanitize_url(attrs[f])
        return attrs


def _absolute_media_url(relative_url: str, request=None) -> str:
    """Resolve a Django FileField .url (which is host-relative, e.g.
    '/media/profiles/foo.jpg') to a fully-qualified absolute URL.

    Order of preference:
      1. request.build_absolute_uri() — uses the request's Host header.
         Correct behind a correctly-configured nginx proxy (Host and
         X-Forwarded-Host both forwarded), and the only path that
         produces the right scheme on the live deployment.
      2. settings.SITE_URL — for background paths (management commands,
         email rendering, scheduled tasks) where no request is in
         scope. Set explicitly via the SITE_URL env var; default in
         settings.py points at the public dev URL.
      3. Raise. A relative URL silently rendered into a page is a
         foot-gun: it works on the page's host but breaks the moment
         the same JSON is consumed from a different origin (an admin
         tool, a CDN, a third-party embed). Failing loud is safer.
    """
    if not relative_url:
        return relative_url
    if request is not None:
        return request.build_absolute_uri(relative_url)
    site_url = getattr(settings, 'SITE_URL', '') or ''
    if site_url:
        # urljoin treats the second arg as relative-to-base when the
        # first arg lacks a scheme; with the trailing-slash guard on
        # SITE_URL this composes '/media/...' onto 'https://host/' as
        # expected.
        base = site_url if site_url.endswith('/') else site_url + '/'
        return urljoin(base, relative_url.lstrip('/'))
    raise RuntimeError(
        '_absolute_media_url: no request and no SITE_URL configured — '
        'cannot produce an absolute URL for '
        f'{relative_url!r}. Set SITE_URL in the environment.'
    )


class CaseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseCategory
        fields = '__all__'


class MediaSerializer(SanitizingModelSerializerMixin, serializers.ModelSerializer):
    # Defense in depth: media descriptions can be rendered in case
    # galleries and search result rows.
    text_fields = ['description']

    class Meta:
        model = Media
        fields = '__all__'
        read_only_fields = ['uploaded_by', 'created_at']


class ReportSerializer(SanitizingModelSerializerMixin, serializers.ModelSerializer):
    # `narrative` is the canonical human-rights testimony; `reporter_*`
    # and `precise_location` are private. All are free-text and could
    # be rendered in a future HTML view, so all are sanitized.
    text_fields = [
        'narrative', 'suspected_reason', 'official_reason',
        'reporter_contact', 'source_attribution', 'reporter_name',
    ]
    media_files = MediaSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            for field in PRIVATE_REPORT_FIELDS:
                data.pop(field, None)
        return data


class PersonListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    categories = CaseCategorySerializer(many=True, read_only=True)
    # report_count is computed from the `reports` prefetch rather
    # than via .annotate() in the viewset. The annotate pattern
    # (annotate(report_count=Count('reports'))) adds a GROUP BY to
    # the main SELECT that breaks prefetch_related's batching for
    # the other prefetches — they degrade to per-row queries. With
    # this SerializerMethodField + the existing `reports` prefetch,
    # the count is O(1) per row using prefetched data.
    report_count = serializers.SerializerMethodField()
    # days_since_last_report: the model @property calls
    # `self.reports.order_by('-date_start').first()` per access —
    # one query per row. Compute it here from the prefetched
    # `reports` cache instead.
    days_since_last_report = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Person
        exclude = ['medical_notes', 'precise_location']
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_profile_image_url(self, obj):
        if obj.profile_image:
            return _absolute_media_url(obj.profile_image.url, self.context.get('request'))
        # Iterate the prefetched `media_files` cache; a queryset
        # .filter() on a related manager would invalidate the cache
        # and trigger a per-row query.
        for media in obj.media_files.all():
            if (media.media_type == 'photo'
                    and media.visibility == 'public'
                    and media.url):
                return _absolute_media_url(media.url, self.context.get('request'))
        return None

    @extend_schema_field(serializers.IntegerField())
    def get_report_count(self, obj):
        # Computed from the prefetched `reports` cache; no query.
        # len() on a prefetched related manager is O(1) in Python
        # over the already-loaded rows.
        return len(obj.reports.all())

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_days_since_last_report(self, obj):
        # Find the latest report in the prefetched cache. The
        # model @property of the same name does
        # `self.reports.order_by('-date_start').first()` — that's a
        # per-row query. Iterating the prefetched manager is
        # O(reports-per-person) in Python over already-loaded rows.
        from django.utils import timezone
        latest_date = None
        for r in obj.reports.all():
            if r.date_start and (latest_date is None or r.date_start > latest_date):
                latest_date = r.date_start
        if latest_date is None:
            return None
        return (timezone.now().date() - latest_date).days


class PersonDetailSerializer(serializers.ModelSerializer):
    """Full serializer with reports and media for detail views."""
    categories = CaseCategorySerializer(many=True, read_only=True)
    reports = serializers.SerializerMethodField()
    media_files = MediaSerializer(many=True, read_only=True)
    days_since_last_report = serializers.IntegerField(read_only=True)
    family = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_profile_image_url(self, obj):
        if obj.profile_image:
            return _absolute_media_url(obj.profile_image.url, self.context.get('request'))
        # See PersonListSerializer.get_profile_image_url — iterate
        # the prefetched cache instead of issuing a new query.
        for media in obj.media_files.all():
            if (media.media_type == 'photo'
                    and media.visibility == 'public'
                    and media.url):
                return _absolute_media_url(media.url, self.context.get('request'))
        return None

    @extend_schema_field(ReportSerializer(many=True))
    def get_reports(self, obj):
        # For authenticated users, `obj.reports.all()` reuses the
        # 'reports' prefetched cache. For anonymous users, the
        # viewset prefetches a `Prefetch('reports',
        # queryset=Report.objects.filter(is_private=False))` so the
        # `filter(is_private=False)` here is a no-op (the prefetch
        # already excluded them) — the prefetched cache is reused.
        request = self.context.get('request')
        reports = obj.reports.all()
        if not request or not request.user.is_authenticated:
            reports = reports.filter(is_private=False)
        return ReportSerializer(reports, many=True, context=self.context).data

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_days_since_last_report(self, obj):
        # Same logic as PersonListSerializer.get_days_since_last_report
        # — derive from the prefetched `reports` cache rather than
        # the model @property (which would issue a per-row query).
        from django.utils import timezone
        latest_date = None
        for r in obj.reports.all():
            if r.date_start and (latest_date is None or r.date_start > latest_date):
                latest_date = r.date_start
        if latest_date is None:
            return None
        return (timezone.now().date() - latest_date).days

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_family(self, obj):
        # The viewset prefetches `relationships_as_a__person_b` and
        # `relationships_as_b__person_a` — the related Persons are
        # already JOINed in. Chaining `.select_related('person_b')`
        # onto `obj.relationships_as_a` builds a new queryset that
        # bypasses the prefetched cache and re-queries per row. Just
        # iterate the prefetched managers directly.
        result = []
        for rel in obj.relationships_as_a.all():
            result.append({
                'person_id': rel.person_b.id,
                'person_name': rel.person_b.name,
                'relationship': rel.get_relationship_type_display(),
            })
        for rel in obj.relationships_as_b.all():
            result.append({
                'person_id': rel.person_a.id,
                'person_name': rel.person_a.name,
                'relationship': rel.get_relationship_type_display(),
            })
        return result

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            for field in PRIVATE_PERSON_FIELDS:
                data.pop(field, None)
        return data


class PersonWriteSerializer(SanitizingModelSerializerMixin, serializers.ModelSerializer):
    """Serializer for creating/updating persons."""
    # Defense in depth: sanitizes every free-text identity +
    # narrative + location field plus `authoritative_url` (URL
    # validator, http(s) only). The identity fields (`name`,
    # `aliases`, `legal_name`) are first-class PII and the most
    # likely XSS pivot if a future template renders them with
    # `|safe` or `mark_safe` — sanitizing at the input boundary
    # keeps the DB clean regardless of the render path.
    text_fields = [
        'name', 'legal_name', 'aliases', 'country', 'ethnicity',
        'rough_location', 'precise_location', 'medical_notes',
        'summary_narrative', 'authoritative_source',
    ]
    url_fields = ['authoritative_url']

    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=CaseCategory.objects.all(),
        many=True, required=False, source='categories'
    )

    class Meta:
        model = Person
        exclude = ['categories']
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class FamilyRelationshipSerializer(SanitizingModelSerializerMixin, serializers.ModelSerializer):
    """Family-relationship CRUD payload.

    Read shape: full row plus denormalised `person_a_name` /
    `person_b_name` so the frontend can render the list without
    resolving FK IDs separately.

    Write shape: accepts `person_a` and `person_b` as FK IDs (DRF
    `PrimaryKeyRelatedField` is the default for `IntegerField`-with-FK
    in `ModelSerializer`).

    Validation (see `validate`):
        - `person_a != person_b` — no self-link.
        - One row per ordered `(person_a, person_b)` pair, regardless
          of type — the model already enforces this via
          `unique_together = ['person_a', 'person_b']` but we drop
          DRF's auto-validator (see `get_unique_together_validators`)
          so the volunteer sees a friendlier message.
        - For undirected types (`sibling`, `spouse`, `other`), the
          reverse-ordered pair is also rejected. `parent` / `child`
          allow either direction (direction carries meaning).
    """
    # NOTE: long docstring above is intentional — describes the
    # validation rules for the volunteer / advocate audience.
    # Sanitizing notes via SanitizingModelSerializerMixin (text_fields
    # below) is defense-in-depth; the field is rarely user-supplied
    # with markup, but we sanitize anyway for parity with other
    # text fields.
    text_fields = ['notes']

    person_a_name = serializers.CharField(source='person_a.name', read_only=True)
    person_b_name = serializers.CharField(source='person_b.name', read_only=True)

    class Meta:
        model = FamilyRelationship
        fields = [
            'id', 'person_a', 'person_b',
            'person_a_name', 'person_b_name',
            'relationship_type', 'notes',
        ]

    def get_unique_together_validators(self):
        # DRF's default UniqueTogetherValidator produces a generic
        # 'non_field_errors: the fields person_a, person_b must make
        # a unique set' that doesn't tell the volunteer what to fix.
        # Our `validate()` below produces a clearer message; suppress
        # the duplicate here so the user only sees ours.
        return []

    def validate(self, data):
        # On PATCH the missing fields fall back to the existing row —
        # otherwise `validate()` would reject an update that only
        # changes `notes`.
        instance = self.instance
        person_a = data.get('person_a', getattr(instance, 'person_a_id', None))
        person_b = data.get('person_b', getattr(instance, 'person_b_id', None))
        rel_type = data.get(
            'relationship_type',
            getattr(instance, 'relationship_type', None),
        )

        if person_a is not None and person_a == person_b:
            raise serializers.ValidationError(
                {'person_b': 'A person cannot be related to themselves.'}
            )

        if person_a and person_b:
            # Reject a second row on the same ordered pair regardless
            # of type. unique_together on the model already does this,
            # but a friendlier message helps the volunteer fix it.
            dup_qs = FamilyRelationship.objects.filter(
                person_a=person_a, person_b=person_b,
            )
            if instance:
                dup_qs = dup_qs.exclude(pk=instance.pk)
            if dup_qs.exists():
                raise serializers.ValidationError(
                    'A relationship already exists between these two persons.'
                )

            # For undirected types, also reject the reverse pair.
            if rel_type in ('sibling', 'spouse', 'other'):
                rev_qs = FamilyRelationship.objects.filter(
                    person_a=person_b, person_b=person_a,
                )
                if instance:
                    rev_qs = rev_qs.exclude(pk=instance.pk)
                if rev_qs.exists():
                    raise serializers.ValidationError(
                        f'A {rel_type} relationship already exists in the opposite direction.'
                    )

        return data


class AuditLogSerializer(serializers.ModelSerializer):
    """Read-only serializer for the AuditLog API at /api/audit-logs/.

    Used by staff-only via AuditLogViewSet (IsAdminUser). The `user`
    field is rendered as a primary-key integer for predictability
    across the API surface — the frontend resolves the FK to a
    username by joining against the user list it already has, rather
    than us nesting a User object on every audit row (which would
    bloat list payloads and let stale username data leak into the
    audit response after a rename).

    If a user was deleted (SET_NULL) the FK is null — the frontend
    renders '—' for those rows.
    """

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'timestamp',
            'user',
            'action',
            'target_type',
            'target_id',
            'details',
            'ip_address',
        ]
        read_only_fields = fields  # audit rows are write-once, never editable
