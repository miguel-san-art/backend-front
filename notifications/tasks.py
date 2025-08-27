# notifications/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

from .services import NotificationService

logger = logging.getLogger(__name__)


@shared_task
def check_expiring_titles():
    """Tâche périodique pour vérifier les titres expirant"""
    try:
        success = NotificationService.check_expiring_titles()
        if success:
            logger.info("Vérification des titres expirant terminée avec succès")
        else:
            logger.error("Erreur lors de la vérification des titres expirant")
        return success
    except Exception as e:
        logger.error(f"Erreur dans la tâche check_expiring_titles: {e}")
        return False


@shared_task
def check_overdue_requests():
    """Tâche périodique pour vérifier les demandes en retard"""
    try:
        success = NotificationService.check_overdue_requests()
        if success:
            logger.info("Vérification des demandes en retard terminée avec succès")
        else:
            logger.error("Erreur lors de la vérification des demandes en retard")
        return success
    except Exception as e:
        logger.error(f"Erreur dans la tâche check_overdue_requests: {e}")
        return False


@shared_task
def send_daily_digest():
    """Envoyer un résumé quotidien aux administrateurs"""
    try:
        from users.models import User
        from titres.models import Titre
        from demandes.models import Demande
        
        # Obtenir les statistiques du jour
        today = timezone.now().date()
        
        # Nouvelles demandes du jour
        new_requests = Demande.objects.filter(
            date_soumission=today
        ).count()
        
        # Titres expirant dans les 7 prochains jours
        expiring_soon = Titre.objects.filter(
            date_expiration__lte=today + timedelta(days=7),
            date_expiration__gte=today,
            status='approuve'
        ).count()
        
        # Demandes en attente
        pending_requests = Demande.objects.filter(
            status__in=['soumise', 'en_examen']
        ).count()
        
        # Envoyer aux administrateurs
        admin_users = User.objects.filter(
            profile__role='admin'
        )
        
        message = f"""
Résumé quotidien du système de gestion des titres:

📊 Statistiques du jour ({today.strftime('%d/%m/%Y')}):
- Nouvelles demandes: {new_requests}
- Titres expirant dans 7 jours: {expiring_soon}
- Demandes en attente: {pending_requests}

🔔 Actions recommandées:
{f'- Traiter {pending_requests} demandes en attente' if pending_requests > 0 else '- Aucune demande en attente'}
{f'- Contacter les propriétaires de {expiring_soon} titres expirant bientôt' if expiring_soon > 0 else '- Aucun titre expirant bientôt'}
        """.strip()
        
        for admin in admin_users:
            NotificationService.create_notification(
                recipient=admin,
                title=f"Résumé quotidien - {today.strftime('%d/%m/%Y')}",
                message=message,
                notification_type='info',
                priority='low',
                send_email=True
            )
        
        logger.info(f"Résumé quotidien envoyé à {admin_users.count()} administrateurs")
        return True
        
    except Exception as e:
        logger.error(f"Erreur dans la tâche send_daily_digest: {e}")
        return False


@shared_task
def cleanup_old_notifications():
    """Nettoyer les anciennes notifications (>90 jours)"""
    try:
        cutoff_date = timezone.now() - timedelta(days=90)
        
        deleted_count, _ = NotificationService.objects.filter(
            created_at__lt=cutoff_date,
            is_read=True
        ).delete()
        
        logger.info(f"Nettoyage terminé: {deleted_count} notifications supprimées")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Erreur dans la tâche cleanup_old_notifications: {e}")
        return 0
    