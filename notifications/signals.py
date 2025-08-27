# notifications/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import NotificationPreference
from .services import NotificationService

User = get_user_model()


@receiver(post_save, sender=User)
def create_notification_preferences(sender, instance, created, **kwargs):
    """Créer les préférences de notification pour un nouvel utilisateur"""
    if created:
        NotificationPreference.objects.get_or_create(
            user=instance,
            defaults={
                'email_expiration': True,
                'email_status_change': True,
                'email_assignment': True,
                'email_reminders': True,
                'app_all_notifications': True,
                'reminder_frequency_days': 7
            }
        )


# Signal pour les titres (si le module existe)
try:
    from titres.models import Titre
    
    @receiver(post_save, sender=Titre)
    def notify_titre_changes(sender, instance, created, **kwargs):
        """Notifier les changements de titres"""
        if created:
            # Nouveau titre créé
            NotificationService.notify_titre_created(instance)
        else:
            # Titre modifié
            NotificationService.notify_titre_updated(instance)
    
    @receiver(post_delete, sender=Titre)
    def notify_titre_deleted(sender, instance, **kwargs):
        """Notifier la suppression d'un titre"""
        NotificationService.notify_titre_deleted(instance)

except ImportError:
    # Module titres non disponible
    pass


# Signal pour les demandes (si le module existe)
try:
    from demandes.models import Demande
    
    @receiver(post_save, sender=Demande)
    def notify_demande_changes(sender, instance, created, **kwargs):
        """Notifier les changements de demandes"""
        if created:
            # Nouvelle demande créée
            NotificationService.notify_demande_created(instance)
        else:
            # Demande modifiée (probablement changement de statut)
            NotificationService.notify_demande_status_changed(instance)

except ImportError:
    # Module demandes non disponible
    pass
