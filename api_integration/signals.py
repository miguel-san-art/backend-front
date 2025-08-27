# api_integration/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import APIKey, Webhook
from .services import WebhookService


@receiver(post_save, sender=APIKey)
def log_api_key_changes(sender, instance, created, **kwargs):
    """Enregistrer les changements de clés API"""
    try:
        from system_admin.services import AuditService
        
        action = 'create' if created else 'update'
        description = f'Clé API {action}: {instance.name}'
        
        AuditService.log_action(
            user=instance.created_by,
            action=action,
            resource_type='api_key',
            resource_id=str(instance.id),
            description=description,
            extra_data={
                'api_key_name': instance.name,
                'status': instance.status
            }
        )
    except ImportError:
        # Module system_admin non disponible
        pass


@receiver(post_delete, sender=APIKey)
def log_api_key_deletion(sender, instance, **kwargs):
    """Enregistrer la suppression de clés API"""
    try:
        from system_admin.services import AuditService
        
        AuditService.log_action(
            user=None,
            action='delete',
            resource_type='api_key',
            resource_id=str(instance.id),
            description=f'Clé API supprimée: {instance.name}'
        )
    except ImportError:
        pass


# Signaux pour déclencher des webhooks
try:
    from titres.models import Titre
    
    @receiver(post_save, sender=Titre)
    def trigger_titre_webhooks(sender, instance, created, **kwargs):
        """Déclencher les webhooks pour les titres"""
        event = 'titre.created' if created else 'titre.updated'
        
        payload = {
            'id': str(instance.id),
            'numero_titre': instance.numero_titre,
            'type': instance.type_titre,
            'status': instance.status,
            'entreprise_nom': instance.entreprise_nom
        }
        
        WebhookService.send_webhook(event, payload)

except ImportError:
    pass


try:
    from demandes.models import Demande
    
    @receiver(post_save, sender=Demande)
    def trigger_demande_webhooks(sender, instance, created, **kwargs):
        """Déclencher les webhooks pour les demandes"""
        if created:
            event = 'demande.created'
        else:
            # Déterminer le type d'événement selon le statut
            if instance.status == 'approuve':
                event = 'demande.approved'
            elif instance.status == 'rejete':
                event = 'demande.rejected'
            else:
                event = 'demande.updated'
        
        payload = {
            'id': str(instance.id),
            'numero_demande': instance.numero_dossier,
            'type': instance.type_titre,
            'status': instance.status,
            'demandeur': instance.demandeur.email if instance.demandeur else None
        }
        
        WebhookService.send_webhook(event, payload)

except ImportError:
    pass


from django.contrib.auth import get_user_model
User = get_user_model()

@receiver(post_save, sender=User)
def trigger_user_webhooks(sender, instance, created, **kwargs):
    """Déclencher les webhooks pour les utilisateurs"""
    if created:
        payload = {
            'id': str(instance.id),
            'email': instance.email,
            'first_name': instance.first_name,
            'last_name': instance.last_name,
            'is_active': instance.is_active
        }
        
        WebhookService.send_webhook('user.created', payload)
        