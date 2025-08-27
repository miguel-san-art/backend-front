# system_admin/urls.py
from django.urls import path
from . import views

app_name = 'system_admin'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.system_dashboard, name='system-dashboard'),
    
    # Configuration système
    path('config/', views.SystemConfigurationListView.as_view(), name='config-list'),
    path('config/<int:pk>/', views.SystemConfigurationDetailView.as_view(), name='config-detail'),
    path('config/categories/', views.get_config_categories, name='config-categories'),
    
    # Logs d'audit
    path('audit/', views.AuditLogListView.as_view(), name='audit-list'),
    path('audit/statistics/', views.audit_statistics, name='audit-statistics'),
    
    # Sauvegardes
    path('backups/', views.SystemBackupListView.as_view(), name='backup-list'),
    path('backups/<int:pk>/download/', views.download_backup, name='backup-download'),
    
    # Métriques
    path('metrics/', views.SystemMetricsListView.as_view(), name='metrics-list'),
    path('metrics/collect/', views.collect_metrics, name='metrics-collect'),
    
    # Maintenances
    path('maintenance/', views.SystemMaintenanceListView.as_view(), name='maintenance-list'),
    path('maintenance/<int:pk>/', views.SystemMaintenanceDetailView.as_view(), name='maintenance-detail'),
    path('maintenance/<int:pk>/start/', views.start_maintenance, name='maintenance-start'),
    path('maintenance/<int:pk>/complete/', views.complete_maintenance, name='maintenance-complete'),
]
