# gestion_demandes/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Demande, Document, HistoriqueDemande

User = get_user_model()

@receiver(pre_save, sender=Demande)
def demande_pre_save(sender, instance, **kwargs):
    """Signal avant sauvegarde d'une demande."""
    # Stocker l'ancien statut pour l'historique
    if instance.pk:
        try:
            old_instance = Demande.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
            instance._old_assignee = old_instance.assignee
        except Demande.DoesNotExist:
            instance._old_status = None
            instance._old_assignee = None
    else:
        instance._old_status = None
        instance._old_assignee = None

@receiver(post_save, sender=Document)
def document_post_save(sender, instance, created, **kwargs):
    """Signal après création/modification d'un document."""
    if created and instance.demande:
        # Créer une entrée d'historique pour l'ajout du document
        HistoriqueDemande.objects.create(
            demande=instance.demande,
            action='document_ajoute',
            utilisateur=instance.uploade_par,
            commentaire=f"Document ajouté: {instance.nom_fichier} ({instance.get_type_document_display()})"
        )

@receiver(post_save, sender=Demande)
def demande_post_save(sender, instance, created, **kwargs):
    """Signal après création/modification d'une demande."""
    if created:
        # Créer l'historique de soumission
        HistoriqueDemande.objects.create(
            demande=instance,
            action='soumission',
            utilisateur=instance.demandeur,
            nouveau_status=instance.status,
            commentaire=f"Nouvelle demande créée: {instance.numero_dossier}"
        )
    else:
        # Vérifier les changements de statut et d'assignation
        if hasattr(instance, '_old_status') and instance._old_status != instance.status:
            action = 'modification'
            if instance.status == 'en_examen':
                action = 'mise_en_examen'
            elif instance.status == 'approuvee':
                action = 'approbation'
            elif instance.status == 'rejetee':
                action = 'rejet'
            
            # Note: L'utilisateur qui fait la modification devrait être passé via le context
            # Pour l'instant, on utilise None et cela sera géré dans les vues
            if not HistoriqueDemande.objects.filter(
                demande=instance,
                ancien_status=instance._old_status,
                nouveau_status=instance.status
            ).exists():
                HistoriqueDemande.objects.create(
                    demande=instance,
                    action=action,
                    utilisateur=None,  # Sera mis à jour dans les vues
                    ancien_status=instance._old_status,
                    nouveau_status=instance.status,
                    commentaire=f"Changement de statut: {instance._old_status} → {instance.status}"
                )
                