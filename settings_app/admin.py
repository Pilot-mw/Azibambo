from django.contrib import admin
from .models import SiteSettings, Backup

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'currency', 'theme', 'sidebar_color']

@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'notes']
