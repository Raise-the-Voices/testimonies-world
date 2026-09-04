from rest_framework import serializers

from .models import CaseCategory, FamilyRelationship, Media, Person, Report

# Fields that are always excluded from public API responses
PRIVATE_PERSON_FIELDS = ['medical_notes', 'precise_location']
PRIVATE_REPORT_FIELDS = ['reporter_name', 'reporter_contact', 'precise_location']


class CaseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseCategory
        fields = '__all__'


class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = '__all__'
        read_only_fields = ['uploaded_by', 'created_at']


class ReportSerializer(serializers.ModelSerializer):
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

    def get_profile_image_url(self, obj):
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        photo = obj.media_files.filter(media_type='photo', visibility='public').first()
        if photo and photo.url:
            return photo.url
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

    def get_profile_image_url(self, obj):
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        photo = obj.media_files.filter(media_type='photo', visibility='public').first()
        if photo and photo.url:
            return photo.url
        return None

    def get_reports(self, obj):
        request = self.context.get('request')
        reports = obj.reports.all()
        if not request or not request.user.is_authenticated:
            reports = reports.filter(is_private=False)
        return ReportSerializer(reports, many=True, context=self.context).data

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


class PersonWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating persons."""
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=CaseCategory.objects.all(),
        many=True, required=False, source='categories'
    )

    class Meta:
        model = Person
        exclude = ['categories']
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class FamilyRelationshipSerializer(serializers.ModelSerializer):
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
