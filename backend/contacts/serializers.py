from rest_framework import serializers

from cases.serializers import SanitizingModelSerializerMixin

from .models import Contact


class ContactSerializer(SanitizingModelSerializerMixin, serializers.ModelSerializer):
    # Contacts are advocate-only and always-private. `name` and
    # `notes` are the canonical PII columns; sanitizing at the
    # input boundary keeps the audit trail (which echoes these
    # values) and any future export path XSS-safe.
    text_fields = ['name', 'notes']

    class Meta:
        model = Contact
        fields = '__all__'
        # Mass-assignment guards:
        # - deleted_at is the soft-delete tombstone. Only
        #   perform_destroy may set it; an authenticated advocate
        #   PATCH-ing {"deleted_at": null} would otherwise undelete
        #   a row and corrupt audit-log semantics.
        # - created_at is set by the framework.
        read_only_fields = ['deleted_at', 'created_at']
