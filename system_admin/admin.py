# system_admin/admin.py
from django.contrib import admin
from .models import SystemConfiguration, AuditLog, SystemBackup, SystemMetrics, SystemMaintenance


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ['key', 'category', 'is_active', 'updated_at', 'updated_by']
    list_filter = ['category', 'is_active']
    search_fields = ['key', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'level', 'resource_type', 'timestamp']
    list_filter = ['action', 'level', 'resource_type', 'timestamp']
    search_fields = ['user__email', 'description', 'resource_type']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(SystemBackup)
class SystemBackupAdmin(admin.ModelAdmin):
    list_display = ['name', 'backup_type', 'status', 'created_at', 'created_by']
    list_filter = ['backup_type', 'status', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'started_at', 'completed_at', 'file_size']


@admin.register(SystemMetrics)
class SystemMetricsAdmin(admin.ModelAdmin):
    list_display = ['metric_type', 'value', 'unit', 'timestamp']
    list_filter = ['metric_type', 'timestamp']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(SystemMaintenance)
class SystemMaintenanceAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'priority', 'scheduled_start', 'created_by']
    list_filter = ['status', 'priority', 'scheduled_start']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    