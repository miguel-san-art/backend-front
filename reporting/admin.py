# reporting/admin.py
from django.contrib import admin
from .models import Report, Dashboard, AuditLog

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'format', 'created_by', 'created_at']
    list_filter = ['report_type', 'format', 'created_at']
    search_fields = ['name', 'created_by__email']
    readonly_fields = ['created_at']

@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_default', 'created_at']
    list_filter = ['is_default', 'created_at']
    search_fields = ['name', 'user__email']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model_name', 'timestamp']
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['user__email', 'description']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
