# titres/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import date
from .models import Titre, RedevanceTitre, HistoriqueTitre

@receiver(pre_save, sender=Titre)
def titre_pre_save(sender, instance, **kwargs):
    """Signal déclenché avant la sauvegarde d'un titre."""
    # Vérifier si le titre existe déjà (modification)
    if instance.pk:
        try:
            old_instance = Titre.objects.get(pk=instance.pk)
            
            # Vérifier si le statut change
            if old_instance.status != instance.status:
                # Stocker l'ancien statut pour l'historique
                instance._old_status = old_instance.status
            
            # Mettre à jour le statut si le titre est expiré
            if instance.is_expired and instance.status not in ['expire', 'rejete']:
                instance.status = 'expire'
                
        except Titre.DoesNotExist:
            pass

@receiver(post_save, sender=Titre)
def titre_post_save(sender, instance, created, **kwargs):
    """Signal déclenché après la sauvegarde d'un titre."""
    
    # Si c'est un nouveau titre approuvé, créer la redevance pour l'année courante
    if created and instance.status == 'approuve':
        current_year = date.today().year
        
        # Créer la redevance pour l'année courante si elle n'existe pas
        if not RedevanceTitre.objects.filter(titre=instance, annee=current_year).exists():
            RedevanceTitre.objects.create(
                titre=instance,
                annee=current_year,
                montant=instance.redevance_annuelle,
                date_echeance=date(current_year, 12, 31)
            )

@receiver(post_save, sender=RedevanceTitre)
def redevance_post_save(sender, instance, created, **kwargs):
    """Signal déclenché après la sauvegarde d'une redevance."""
    
    # Si c'est une nouvelle redevance, créer l'entrée d'historique correspondante
    if created:
        HistoriqueTitre.objects.create(
            titre=instance.titre,
            action='modification',
            commentaire=f"Redevance générée pour l'année {instance.annee} - Montant: {instance.montant} FCFA"
        )
    
    # Si la redevance est marquée comme payée, créer l'entrée d'historique
    elif instance.status_paiement == 'paye' and instance.date_paiement:
        # Vérifier s'il n'y a pas déjà une entrée d'historique pour ce paiement
        recent_payment_history = HistoriqueTitre.objects.filter(
            titre=instance.titre,
            action='modification',
            commentaire__contains=f"Redevance {instance.annee} payée"
        ).exists()
        
        if not recent_payment_history:
            HistoriqueTitre.objects.create(
                titre=instance.titre,
                action='modification',
                commentaire=f"Redevance {instance.annee} payée - Référence: {instance.reference_paiement or 'N/A'}"
            )
            