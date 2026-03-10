from rest_framework import serializers

from .models import CaseworkRecord


class CaseworkRecordSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(
        source='performed_by.get_full_name', read_only=True
    )

    class Meta:
        model = CaseworkRecord
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
