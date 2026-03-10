from django.contrib import admin

from .models import CaseworkRecord


@admin.register(CaseworkRecord)
class CaseworkRecordAdmin(admin.ModelAdmin):
    list_display = ['action_type', 'status', 'date', 'performed_by']
    list_filter = ['action_type', 'status', 'date']
    search_fields = ['description', 'notes']
    filter_horizontal = ['persons']
    readonly_fields = ['created_at', 'updated_at']
