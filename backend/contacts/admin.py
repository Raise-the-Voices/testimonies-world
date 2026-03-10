from django.contrib import admin

from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'role', 'email', 'phone']
    list_filter = ['role']
    search_fields = ['name', 'email', 'notes']
    filter_horizontal = ['persons']
