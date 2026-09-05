from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from contacts.permissions import IsAdvocate

from . import notifications
from .models import CaseworkRecord, Notification, UserPreference
from .serializers import (
    CaseworkRecordSerializer,
    NotificationSerializer,
    UserPreferenceSerializer,
)


class CaseworkRecordViewSet(viewsets.ModelViewSet):
    serializer_class = CaseworkRecordSerializer
    filterset_fields = ['action_type', 'status', 'performed_by']
    search_fields = ['description', 'notes', 'next_steps']
    ordering_fields = ['date', 'created_at', 'status']
    # Tightened to IsAdvocate to match CLAUDE.md:56-59 ("Advocate:
    # casework, contacts, restricted media"). The previous
    # IsAuthenticated gate let any volunteer read & write sensitive
    # casework narratives — including Notes / Next Steps that often
    # contain PII about family contacts and un-redacted sources.
    permission_classes = [permissions.IsAuthenticated, IsAdvocate]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CaseworkRecord.objects.prefetch_related('persons').select_related('performed_by')

    def perform_create(self, serializer):
        record = serializer.save(performed_by=self.request.user)
        event = notifications.build_create_event(record, self.request.user)
        notifications.emit_event(event)
        notifications.record_seen_by(record, self.request.user)

    def perform_update(self, serializer):
        prior_status = serializer.instance.status if serializer.instance else None
        record = serializer.save()
        became_done = (
            prior_status != CaseworkRecord.Status.DONE
            and record.status == CaseworkRecord.Status.DONE
        )
        event = notifications.build_update_event(
            record, self.request.user, became_done=became_done
        )
        notifications.emit_event(event)
        notifications.record_seen_by(record, self.request.user)

    def retrieve(self, request, *args, **kwargs):
        """GET a record. Side effect: mark the caller's own notifications
        on this record as read, and emit a 'seen by' notification to the
        author — the human-sense "verification" the feature is named for."""
        # Pull through get_queryset() instead of self.get_object() so the
        # prefetch_related('persons') / select_related('performed_by') on
        # get_queryset is honored — otherwise the serializer's read of
        # `instance.persons` and `instance.performed_by.get_full_name()`
        # would each fire a separate query.
        instance = self.get_queryset().get(pk=kwargs.get(self.lookup_field))
        Notification.objects.filter(
            recipient=request.user,
            casework=instance,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())
        notifications.record_seen_by(instance, request.user)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """List, mark-read, read-all, unread-count. No write endpoint from
    the client other than 'mark read' — notifications are server-generated
    only."""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_read', 'kind']

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user).select_related(
            'actor', 'casework'
        ).prefetch_related('casework__persons')
        if self.request.query_params.get('unread') in ('1', 'true', 'True'):
            qs = qs.filter(is_read=False)
        return qs

    @action(detail=True, methods=['post'], url_path='read')
    def mark_one_read(self, request, pk=None):
        notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notifications.mark_read(notif, request.user)
        return Response(NotificationSerializer(notif).data)

    @action(detail=False, methods=['post'], url_path='read-all')
    def mark_all_read(self, request):
        count = notifications.mark_all_read(request.user)
        return Response({'updated': count})

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        return Response({'count': notifications.unread_count(request.user)})


class UserPreferenceViewSet(viewsets.ModelViewSet):
    """One row per user; we look it up by `me` rather than pk so the
    client never has to know its preference row id."""
    serializer_class = UserPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        pref, _ = UserPreference.objects.get_or_create(user=self.request.user)
        return pref

    def list(self, request, *args, **kwargs):
        pref = self.get_object()
        return Response(UserPreferenceSerializer(pref).data)

    def update(self, request, *args, **kwargs):
        pref = self.get_object()
        serializer = UserPreferenceSerializer(pref, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)