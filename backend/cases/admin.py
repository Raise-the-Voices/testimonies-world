from django.contrib import admin

from .models import AuditLog, CaseCategory, FamilyRelationship, Media, Person, Report


class ReportInline(admin.TabularInline):
    model = Report
    extra = 0
    fields = ['source_type', 'source_attribution', 'date_start', 'narrative', 'is_private']
    show_change_link = True


class MediaInline(admin.TabularInline):
    model = Media
    fk_name = 'person'
    extra = 0
    fields = ['media_type', 'visibility', 'description', 'file', 'url']


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'current_status', 'medical_status',
                    'quality_tier', 'authoritative_source', 'is_published', 'updated_at']
    list_filter = ['current_status', 'medical_status', 'quality_tier',
                   'is_published', 'country', 'categories', 'authoritative_source']
    search_fields = ['name', 'legal_name', 'aliases', 'country',
                     'summary_narrative', 'authoritative_source']
    filter_horizontal = ['categories']
    inlines = [ReportInline, MediaInline]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        ('Identity', {
            'fields': ['name', 'legal_name', 'aliases', 'country',
                       'ethnicity', 'gender', 'date_of_birth', 'profile_image']
        }),
        ('Status', {
            'fields': ['current_status', 'medical_status', 'medical_notes']
        }),
        ('Location', {
            'fields': ['rough_location', 'precise_location', 'last_known_date']
        }),
        ('Narrative', {
            'fields': ['summary_narrative']
        }),
        ('Source', {
            'fields': ['authoritative_source', 'authoritative_url'],
            'description': 'For cases imported from external databases'
        }),
        ('Classification', {
            'fields': ['categories', 'quality_tier', 'is_published']
        }),
        ('Meta', {
            'fields': ['created_by', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['person', 'source_type', 'date_start', 'is_private', 'created_at']
    list_filter = ['source_type', 'is_private', 'date_start']
    search_fields = ['person__name', 'narrative', 'source_attribution']
    raw_id_fields = ['person']
    readonly_fields = ['created_at', 'updated_at']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'media_type', 'visibility', 'created_at']
    list_filter = ['media_type', 'visibility']
    raw_id_fields = ['person', 'report']


@admin.register(CaseCategory)
class CaseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']


@admin.register(FamilyRelationship)
class FamilyRelationshipAdmin(admin.ModelAdmin):
    list_display = ['person_a', 'relationship_type', 'person_b']
    raw_id_fields = ['person_a', 'person_b']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'target_type', 'target_id']
    list_filter = ['action', 'target_type']
    readonly_fields = ['user', 'action', 'target_type', 'target_id',
                       'details', 'ip_address', 'timestamp']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
