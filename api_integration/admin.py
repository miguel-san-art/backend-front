# api_integration/admin.py
from django.contrib import admin
from .models import APIKey, APIRequest, Webhook, WebhookDelivery, ExternalService, ServiceHealthCheck


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'key', 'status', 'rate_limit', 'created_at', 'last_used']
    list_filter = ['status', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['key', 'secret', 'created_at', 'updated_at', 'last_used']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('Clés', {
            'fields': ('key', 'secret')
        }),
        ('Permissions', {
            'fields': ('allowed_ips', 'allowed_endpoints', 'rate_limit')
        }),
        ('État', {
            'fields': ('status', 'is_active', 'expires_at')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'last_used')
        }),
    )


@admin.register(APIRequest)
class APIRequestAdmin(admin.ModelAdmin):
    list_display = ['api_key', 'method', 'endpoint', 'status_code', 'response_time', 'timestamp']
    list_filter = ['method', 'status_code', 'timestamp']
    search_fields = ['endpoint', 'ip_address', 'api_key__name']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'status', 'success_count', 'failure_count', 'created_at']
    list_filter = ['status', 'is_active', 'created_at']
    search_fields = ['name', 'url', 'description']
    readonly_fields = ['secret', 'success_count', 'failure_count', 'last_success', 'last_failure']


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ['webhook', 'event', 'status', 'attempts', 'created_at']
    list_filter = ['status', 'event', 'created_at']
    search_fields = ['webhook__name', 'event']
    readonly_fields = ['created_at', 'delivered_at']


@admin.register(ExternalService)
class ExternalServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'service_type', 'status', 'uptime_percentage', 'last_check']
    list_filter = ['service_type', 'status', 'is_active']
    search_fields = ['name', 'description', 'base_url']
    readonly_fields = ['last_check', 'response_time', 'uptime_percentage']


@admin.register(ServiceHealthCheck)
class ServiceHealthCheckAdmin(admin.ModelAdmin):
    list_display = ['service', 'status', 'response_time', 'checked_at']
    list_filter = ['status', 'checked_at']
    search_fields = ['service__name']
    readonly_fields = ['checked_at']
    date_hierarchy = 'checked_at'
    