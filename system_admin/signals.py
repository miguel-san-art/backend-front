# system_admin/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.auth import get_user_model
from .services import AuditService
from .models import SystemConfiguration

User = get_user_model()


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Enregistrer les connexions utilisateur"""
    ip_address = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    AuditService.log_action(
        user=user,
        action='login',
        resource_type='user',
        resource_id=str(user.id),
        description=f'Connexion utilisateur: {user.email}',
        ip_address=ip_address,
        user_agent=user_agent
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Enregistrer les déconnexions utilisateur"""
    if user:
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        AuditService.log_action(
            user=user,
            action='logout',
            resource_type='user',
            resource_id=str(user.id),
            description=f'Déconnexion utilisateur: {user.email}',
            ip_address=ip_address,
            user_agent=user_agent
        )


@receiver(pre_save, sender=SystemConfiguration)
def log_config_changes(sender, instance, **kwargs):
    """Enregistrer les changements de configuration"""
    if instance.pk:  # Update existing config
        try:
            old_instance = SystemConfiguration.objects.get(pk=instance.pk)
            if old_instance.value != instance.value:
                AuditService.log_action(
                    user=instance.updated_by,
                    action='config',
                    resource_type='system_configuration',
                    resource_id=instance.key,
                    description=f'Configuration modifiée: {instance.key}',
                    extra_data={
                        'old_value': old_instance.value,
                        'new_value': instance.value
                    }
                )
        except SystemConfiguration.DoesNotExist:
            pass


# Signaux pour les modèles principaux (si disponibles)
try:
    from titres.models import Titre
    
    @receiver(post_save, sender=Titre)
    def log_titre_changes(sender, instance, created, **kwargs):
        """Enregistrer les changements de titres"""
        action = 'create' if created else 'update'
        description = f'Titre {action}: {instance.numero_titre}'
        
        AuditService.log_action(
            user=getattr(instance, 'updated_by', None),
            action=action,
            resource_type='titre',
            resource_id=str(instance.id),
            description=description
        )
    
    @receiver(post_delete, sender=Titre)
    def log_titre_deletion(sender, instance, **kwargs):
        """Enregistrer les suppressions de titres"""
        AuditService.log_action(
            user=None,  # L'utilisateur n'est pas disponible dans post_delete
            action='delete',
            resource_type='titre',
            resource_id=str(instance.id),
            description=f'Titre supprimé: {instance.numero_titre}'
        )

except ImportError:
    pass


try:
    from demandes.models import Demande
    
    @receiver(post_save, sender=Demande)
    def log_demande_changes(sender, instance, created, **kwargs):
        """Enregistrer les changements de demandes"""
        action = 'create' if created else 'update'
        description = f'Demande {action}: {instance.numero_dossier}'
        
        AuditService.log_action(
            user=getattr(instance, 'updated_by', None),
            action=action,
            resource_type='demande',
            resource_id=str(instance.id),
            description=description
        )

except ImportError:
    pass
