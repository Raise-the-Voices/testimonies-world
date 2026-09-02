from rest_framework import serializers

from .models import CaseworkRecord, Notification, UserPreference


class CaseworkRecordSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(
        source='performed_by.get_full_name', read_only=True
    )
    seen_by = serializers.SerializerMethodField()

    class Meta:
        model = CaseworkRecord
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def get_seen_by(self, obj):
        """Compact list of advocates who have opened this record since
        it was last edited by the current author. Hidden from the record's
        own author — the signal is for accountability, not vanity."""
        request = self.context.get('request')
        author_id = obj.performed_by_id
        qs = obj.notifications.filter(
            kind=Notification.Kind.RECORD_SEEN,
            read_at__isnull=False,
        ).select_related('actor').order_by('read_at')
        # Only show 'seen by' for users other than the author — a self-seen
        # notification is a bug, not a signal.
        seen = []
        for n in qs:
            if n.actor_id and n.actor_id != author_id:
                seen.append({
                    'name': n.actor.get_full_name() or n.actor.get_username(),
                    'at': n.read_at.isoformat() if n.read_at else None,
                })
        return seen


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(
        source='actor.get_full_name', read_only=True, default=None
    )
    casework_action_type = serializers.CharField(
        source='casework.get_action_type_display', read_only=True, default=None
    )
    casework_persons = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'kind',
            'casework',
            'actor',
            'actor_name',
            'casework_action_type',
            'casework_persons',
            'is_read',
            'read_at',
            'created_at',
        ]
        read_only_fields = fields

    def get_casework_persons(self, obj):
        if not obj.casework:
            return []
        names = list(obj.casework.persons.values_list('name', flat=True)[:3])
        return names


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ['notify_email', 'notify_inapp']