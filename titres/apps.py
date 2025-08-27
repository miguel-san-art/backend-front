# titres/apps.py
from django.apps import AppConfig

class TitresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'titres'
    verbose_name = 'Gestion des Titres'
    
    def ready(self):
        import titres.signals