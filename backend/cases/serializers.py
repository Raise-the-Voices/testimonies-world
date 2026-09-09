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
    report_count = serializers.IntegerField(read_only=True)
    days_since_last_report = serializers.IntegerField(read_only=True)
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Person
        exclude = ['medical_notes', 'precise_location']
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_profile_image_url(self, obj):
        if obj.profile_image:
            return _absolute_media_url(obj.profile_image.url, self.context.get('request'))
        photo = obj.media_files.filter(media_type='photo', visibility='public').first()
        if photo and photo.url:
            return _absolute_media_url(photo.url, self.context.get('request'))
        return None


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
        photo = obj.media_files.filter(media_type='photo', visibility='public').first()
        if photo and photo.url:
            return _absolute_media_url(photo.url, self.context.get('request'))
        return None

    @extend_schema_field(ReportSerializer(many=True))
    def get_reports(self, obj):
        request = self.context.get('request')
        reports = obj.reports.all()
        if not request or not request.user.is_authenticated:
            reports = reports.filter(is_private=False)
        return ReportSerializer(reports, many=True, context=self.context).data

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_family(self, obj):
        rels_a = obj.relationships_as_a.select_related('person_b')
        rels_b = obj.relationships_as_b.select_related('person_a')
        result = []
        for rel in rels_a:
            result.append({
                'person_id': rel.person_b.id,
                'person_name': rel.person_b.name,
                'relationship': rel.get_relationship_type_display(),
            })
        for rel in rels_b:
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
    """Serializer for creating/updating persons.

    Sanitizes every free-text identity + narrative + location field
    plus `authoritative_url` (URL validator, http(s) only). The
    identity fields (`name`, `aliases`, `legal_name`) are first-class
    PII and the most likely XSS pivot if a future template renders
    them with `|safe` or `mark_safe` — sanitizing at the input
    boundary keeps the DB clean regardless of the render path.
    """
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
