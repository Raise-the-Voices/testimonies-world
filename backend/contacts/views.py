"""
Contacts API viewset.

Behavior changes vs. the original:
- Permission: `IsAdvocate` (Advocate group OR staff). The previous
  `IsAuthenticated` let any logged-in user see / write contact data.
- Soft-delete: DELETE sets `deleted_at` instead of removing the row.
  Contacts appear in historical casework narratives; we preserve
  provenance. `get_queryset` filters out soft-deleted rows by default.
- Audit log: every create / update / delete writes an `AuditLog` row
  with the actor, action, target, and request IP. Matches the privacy
  model in CLAUDE.md (contacts are always-private).
"""

from django.utils import timezone

from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from cases.models import AuditLog
from .models import Contact
from .permissions import IsAdvocate
from .serializers import ContactSerializer


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.prefetch_related('persons')
    serializer_class = ContactSerializer
    filterset_fields = ['role']
    search_fields = ['name', 'email', 'notes']
    permission_classes = [IsAdvocate]

    def get_queryset(self):
        # Soft-delete: deleted contacts are excluded from the default
        # queryset. To see them, callers can filter explicitly via the
        # `?deleted=true` parameter (intended for a future admin view;
        # the frontend never sends it today).
        qs = Contact.objects.prefetch_related('persons')
        if self.action != 'list':
            # Detail / update / delete — keep the soft-deleted rows
            # reachable so PATCH on a soft-deleted row returns 404
            # (rather than mysteriously succeeding) and the audit log
            # can still see what happened.
            return qs
        if self.request.query_params.get('deleted') != 'true':
            qs = qs.filter(deleted_at__isnull=True)
        return qs

    # --- Audit log helpers -------------------------------------------------

    def _client_ip(self) -> str | None:
        # X-Forwarded-For arrives as "client, proxy1, proxy2"; take the
        # first hop. SECURE_PROXY_SSL_HEADER is already configured in
        # settings, but X-Forwarded-For is the canonical IP source.
        xff = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR')

    def _audit(self, action: str, instance: Contact, details: str = '') -> None:
        AuditLog.objects.create(
            user=self.request.user if self.request.user.is_authenticated else None,
            action=action,
            target_type='contact',
            target_id=instance.pk,
            details=details,
            ip_address=self._client_ip(),
        )

    # --- Write hooks --------------------------------------------------------

    def perform_create(self, serializer):
        instance = serializer.save()
        self._audit(AuditLog.Action.EDITED, instance, 'created')

    def perform_update(self, serializer):
        # Capture the field-level delta so the audit row tells us what
        # actually changed, not just that something did.
        before = {f: getattr(serializer.instance, f) for f in serializer.fields}
        instance = serializer.save()
        after = {f: getattr(instance, f) for f in serializer.fields}
        changed = [
            f for f in before
            if str(before[f]) != str(after[f]) and f != 'persons'
        ]
        details = f'updated fields: {", ".join(changed) or "(none)"}'
        self._audit(AuditLog.Action.EDITED, instance, details)

    def perform_destroy(self, instance):
        # Soft-delete: mark tombstone instead of removing the row.
        # Refuse to soft-delete an already-deleted contact — that's a
        # double-tap and would corrupt audit-log semantics.
        if instance.deleted_at is not None:
            raise PermissionDenied('Contact has already been deleted.')
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at'])
        self._audit(AuditLog.Action.DELETED, instance, 'soft-deleted')