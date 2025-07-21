# File: src/core/admin.py
from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import SiteSettings

# Register your models here.

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for the SiteSettings model.
    This configuration prevents users from adding new settings objects,
    enforcing the singleton pattern (only one settings entry is allowed).
    """
    list_display = ('__str__', 'coming_soon_mode')

    def has_add_permission(self, request):
        # Prevent adding new settings if one already exists.
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deleting the settings object.
        return False
