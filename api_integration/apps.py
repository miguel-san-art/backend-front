# api_integration/apps.py
from django.apps import AppConfig


class ApiIntegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api_integration'
    verbose_name = 'Intégrations API'
    
    def ready(self):
        # Importer les signaux si nécessaire
        try:
            import api_integration.signals
        except ImportError:
            pass