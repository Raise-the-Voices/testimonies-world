"""Serializers for the testimonials workflow.

Layered per the cases convention:

  TestimonialPublicSerializer     — anonymous / public read shape
  TestimonialInternalSerializer   — Advocate+ audit-friendly read
  TestimonialWriteSerializer      — create / update (Volunteer)
  TestimonialTagSerializer        — lookup table

Source / location ciphertext (`source_encrypted`,
`precise_location_encrypted`) is NEVER serialized in any of these.
Decrypted plaintext only flows through dedicated endpoints behind
`CanViewEncryptedSource` — see views.py.
"""

from rest_framework import serializers

from cases.models import Testimonial, TestimonialTag


class TestimonialTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestimonialTag
        fields = ['id', 'name', 'description']


class TestimonialPublicSerializer(serializers.ModelSerializer):
    """Public-facing payload — masks source + location by visibility flags.

    Server-side masking is the security boundary (SYSTEM_RULES §10).
    The frontend never sees redacted fields in the first place.

    The `source_visible` boolean captures whether *any* source
    descriptor is shown publicly (public_named / public_anonymous).
    Hidden rows surface `null`.
    """

    source_visible = serializers.SerializerMethodField()
    tags = TestimonialTagSerializer(many=True, read_only=True)
    linked_person_id = serializers.IntegerField(source='person_id', read_only=True)
    linked_report_id = serializers.IntegerField(source='report_id', read_only=True)

    class Meta:
        model = Testimonial
        fields = [
            'id',
            'slug',
            'title',
            'language',
            'country',
            'region',
            'public_location_display',
            'incident_date',
            'incident_types',
            'summary',
            'narrative',
            'outcome',
            'verification_level',
            'source_visible',
            'public_source_label',
            'family_protected',
            'contact_protected',
            'status',
            'published_at',
            'tags',
            'translation_group',
            'linked_person_id',
            'linked_report_id',
            'schema_version',
        ]
        read_only_fields = fields  # public reads — never write

    def get_source_visible(self, obj):
        """True iff the public surface shows any source descriptor.

        Hidden means: no name, no anonymous tag, no metadata leak.
        Replaced with `null` because `source_visible: false` is more
        searchable than the string "hidden" — and the latter reads
        like an error to UI consumers.
        """
        return obj.source_visibility != Testimonial.SourceVisibility.HIDDEN


class TestimonialInternalSerializer(TestimonialPublicSerializer):
    """Advocate+ read shape — same as public PLUS workflow metadata.

    Does NOT include ciphertext columns. The encrypted columns have
    no business being on a JSON response, even for admins; decrypted
    plaintext flows through the dedicated endpoint only.
    """

    class Meta(TestimonialPublicSerializer.Meta):
        fields = TestimonialPublicSerializer.Meta.fields + [
            'source_visibility',
            'location_visibility',
            'submitted_by',
            'submitted_at',
            'reviewed_by',
            'reviewed_at',
            'review_notes',
            'approved_by',
            'approved_at',
            'archived_at',
            'created_by',
            'created_at',
            'updated_at',
            'is_exported',
        ]
        read_only_fields = fields


class TestimonialWriteSerializer(serializers.ModelSerializer):
    """Create / update shape for any role (Volunteer can create drafts).

    Server-controlled fields are read-only and silently dropped on
    input (SYSTEM_RULES §5):
      - status + all `*_by` + `*_at` workflow fields: only mutated
        via the transition actions, never via direct PATCH.
      - schema_version + is_exported: server-pinned.
      - created_by / created_at / updated_at: server-pinned.
      - source_encrypted + precise_location_encrypted: never
        serialized. Caller uses `set_source` / `set_precise_location`
        accessors (exposed via dedicated action endpoints when
        permission is held).
    """

    text_fields = ['summary', 'narrative', 'outcome', 'review_notes']
    url_fields = []  # no user-supplied URLs

    class Meta:
        model = Testimonial
        exclude = [
            # Server-controlled (transition actions only):
            'status', 'submitted_by', 'submitted_at',
            'reviewed_by', 'reviewed_at', 'review_notes',
            'approved_by', 'approved_at',
            'published_by', 'published_at', 'archived_at',
            # Server-pinned:
            'schema_version', 'is_exported',
            'created_by', 'created_at', 'updated_at',
            'translation_group',
            # Ciphertext: dedicated accessors only.
            'source_encrypted', 'precise_location_encrypted',
        ]

    def validate(self, attrs):
        """Run sanitize_text on free-text fields (defense in depth)."""
        attrs = super().validate(attrs)
        for f in self.text_fields:
            if f in attrs and isinstance(attrs[f], str):
                # Imported lazily so this serializer can be imported
                # without dragging in the sanitizer module
                # unconditionally (it imports bleach).
                from cases.sanitizers import sanitize_text
                attrs[f] = sanitize_text(attrs[f])
        return attrs

    def validate_source_visibility(self, value):
        # Volunteers may set hidden / public_anonymous but never
        # public_named — a volunteer should not be able to unilaterally
        # publish a source's name. Advocate+ can override.
        request = self.context.get('request')
        if value == Testimonial.SourceVisibility.PUBLIC_NAMED:
            user = getattr(request, 'user', None)
            if not (user and user.is_authenticated
                    and (user.is_staff
                         or user.groups.filter(name='Advocate').exists())):
                raise serializers.ValidationError(
                    'Only Advocates or Admins may mark a source as '
                    'publicly named — use "public_anonymous" or '
                    '"hidden" for the draft.'
                )
        return value
