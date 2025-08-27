# gestion_demandes/apps.py
from django.apps import AppConfig

class GestionDemandesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'demandes'
    verbose_name = 'Gestion des Demandes'
    
    def ready(self):
        import demandes.signals
