# system_admin/apps.py
from django.apps import AppConfig


class SystemAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'system_admin'
    verbose_name = 'Administration Système'
    
    def ready(self):
        # Importer les signaux si nécessaire
        try:
            import system_admin.signals
        except ImportError:
            pass
        