# notifications/admin.py
from django.contrib import admin
from .models import Notification, NotificationPreference, EmailTemplate


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'type', 'priority', 'is_read', 'created_at']
    list_filter = ['type', 'priority', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'recipient__email']
    readonly_fields = ['created_at', 'read_at']
    
    fieldsets = (
        ('Notification', {
            'fields': ('recipient', 'title', 'message', 'type', 'priority')
        }),
        ('Relations', {
            'fields': ('related_titre_id', 'related_demande_id')
        }),
        ('État', {
            'fields': ('is_read', 'is_sent_email', 'created_at', 'read_at')
        }),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_expiration', 'email_status_change', 'app_all_notifications']
    list_filter = ['email_expiration', 'email_status_change', 'app_all_notifications']
    search_fields = ['user__email']


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'subject_template']
    