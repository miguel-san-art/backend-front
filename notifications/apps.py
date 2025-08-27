# notifications/apps.py
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    verbose_name = 'Notifications'
    
    def ready(self):
        # Importer les signaux si nécessaire
        try:
            import notifications.signals
        except ImportError:
            pass
        