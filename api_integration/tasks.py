# api_integration/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

from .services import WebhookService, ExternalServiceService
from .models import WebhookDelivery, APIRequest

logger = logging.getLogger(__name__)


@shared_task
def retry_failed_webhooks():
    """Tâche périodique pour réessayer les webhooks échoués"""
    try:
        WebhookService.retry_failed_deliveries()
        logger.info("Retry des webhooks échoués terminé")
        return True
    except Exception as e:
        logger.error(f"Erreur retry webhooks: {e}")
        return False


@shared_task
def check_external_services_health():
    """Tâche périodique pour vérifier la santé des services externes"""
    try:
        ExternalServiceService.check_service_health()
        logger.info("Vérification santé services externes terminée")
        return True
    except Exception as e:
        logger.error(f"Erreur vérification santé services: {e}")
        return False


@shared_task
def cleanup_old_api_requests():
    """Nettoyer les anciens logs de requêtes API (>90 jours)"""
    try:
        cutoff_date = timezone.now() - timedelta(days=90)
        
        deleted_count, _ = APIRequest.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()
        
        logger.info(f"Nettoyage API requests terminé: {deleted_count} requêtes supprimées")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Erreur nettoyage API requests: {e}")
        return 0


@shared_task
def cleanup_old_webhook_deliveries():
    """Nettoyer les anciennes livraisons de webhooks (>30 jours)"""
    try:
        cutoff_date = timezone.now() - timedelta(days=30)
        
        deleted_count, _ = WebhookDelivery.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['success', 'failed']
        ).delete()
        
        logger.info(f"Nettoyage webhook deliveries terminé: {deleted_count} livraisons supprimées")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Erreur nettoyage webhook deliveries: {e}")
        return 0


@shared_task
def send_webhook_notification(event, payload, webhook_ids=None):
    """Tâche asynchrone pour envoyer des notifications webhook"""
    try:
        if webhook_ids:
            for webhook_id in webhook_ids:
                WebhookService.send_webhook(event, payload, webhook_id)
        else:
            WebhookService.send_webhook(event, payload)
        
        logger.info(f"Webhook {event} envoyé avec succès")
        return True
        
    except Exception as e:
        logger.error(f"Erreur envoi webhook {event}: {e}")
        return False
    