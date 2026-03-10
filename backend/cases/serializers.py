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
    class Meta:
        model = FamilyRelationship
        fields = '__all__'
