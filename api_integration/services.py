# api_integration/services.py
import requests
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db import models

from .models import APIKey, APIRequest, Webhook, WebhookDelivery, ExternalService, ServiceHealthCheck

logger = logging.getLogger(__name__)


class APIKeyService:
    """Service de gestion des clés API"""
    
    @staticmethod
    def validate_api_key(key, ip_address=None, endpoint=None):
        """Valider une clé API"""
        try:
            api_key = APIKey.objects.get(key=key, is_active=True)
            
            # Vérifier l'expiration
            if api_key.is_expired:
                return False, "API key expired"
            
            # Vérifier le statut
            if api_key.status != 'active':
                return False, f"API key status: {api_key.status}"
            
            # Vérifier les IPs autorisées
            if ip_address and api_key.allowed_ips:
                allowed_ips = api_key.get_allowed_ips_list()
                if allowed_ips and ip_address not in allowed_ips:
                    return False, "IP address not allowed"
            
            # Vérifier les endpoints autorisés
            if endpoint and api_key.allowed_endpoints:
                if endpoint not in api_key.allowed_endpoints:
                    return False, "Endpoint not allowed"
            
            # Vérifier la limite de taux
            if not APIKeyService.check_rate_limit(api_key):
                return False, "Rate limit exceeded"
            
            # Mettre à jour la dernière utilisation
            api_key.last_used = timezone.now()
            api_key.save(update_fields=['last_used'])
            
            return True, api_key
            
        except APIKey.DoesNotExist:
            return False, "Invalid API key"
    
    @staticmethod
    def check_rate_limit(api_key):
        """Vérifier la limite de taux"""
        cache_key = f"api_rate_limit:{api_key.key}"
        current_hour = timezone.now().replace(minute=0, second=0, microsecond=0)
        
        # Obtenir le compteur actuel
        counter_key = f"{cache_key}:{current_hour.timestamp()}"
        current_count = cache.get(counter_key, 0)
        
        if current_count >= api_key.rate_limit:
            return False
        
        # Incrémenter le compteur
        cache.set(counter_key, current_count + 1, timeout=3600)
        return True
    
    @staticmethod
    def log_request(api_key, method, endpoint, ip_address, user_agent, 
                   status_code, response_time, response_size=None, 
                   request_data=None, error_message=None):
        """Enregistrer une requête API"""
        try:
            APIRequest.objects.create(
                api_key=api_key,
                method=method,
                endpoint=endpoint,
                ip_address=ip_address,
                user_agent=user_agent,
                status_code=status_code,
                response_time=response_time,
                response_size=response_size,
                request_data=request_data or {},
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"Erreur log requête API: {e}")


class WebhookService:
    """Service de gestion des webhooks"""
    
    @staticmethod
    def send_webhook(event, payload, webhook_id=None):
        """Envoyer un webhook pour un événement"""
        try:
            # Récupérer tous les webhooks actifs pour cet événement
            webhooks = Webhook.objects.filter(
                is_active=True,
                status='active',
                events__contains=event
            )
            
            if webhook_id:
                webhooks = webhooks.filter(id=webhook_id)
            
            for webhook in webhooks:
                WebhookService._deliver_webhook(webhook, event, payload)
                
        except Exception as e:
            logger.error(f"Erreur envoi webhook pour {event}: {e}")
    
    @staticmethod
    def _deliver_webhook(webhook, event, payload):
        """Livrer un webhook spécifique"""
        try:
            # Créer l'enregistrement de livraison
            delivery = WebhookDelivery.objects.create(
                webhook=webhook,
                event=event,
                payload=payload
            )
            
            # Préparer les données
            webhook_payload = {
                'event': event,
                'timestamp': timezone.now().isoformat(),
                'data': payload
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'TelecomSystem-Webhook/1.0'
            }
            
            # Ajouter les headers personnalisés
            if webhook.headers:
                headers.update(webhook.headers)
            
            # Ajouter la signature si un secret est défini
            if webhook.secret:
                signature = WebhookService._generate_signature(
                    json.dumps(webhook_payload, separators=(',', ':')),
                    webhook.secret
                )
                headers['X-Webhook-Signature'] = signature
            
            # Envoyer la requête
            response = requests.post(
                webhook.url,
                json=webhook_payload,
                headers=headers,
                timeout=30
            )
            
            # Traiter la réponse
            if 200 <= response.status_code < 300:
                # Succès
                delivery.status = 'success'
                delivery.http_status = response.status_code
                delivery.response_body = response.text[:1000]  # Limiter la taille
                delivery.delivered_at = timezone.now()
                
                webhook.success_count += 1
                webhook.last_success = timezone.now()
                
            else:
                # Échec HTTP
                delivery.status = 'failed'
                delivery.http_status = response.status_code
                delivery.response_body = response.text[:1000]
                delivery.error_message = f"HTTP {response.status_code}"
                
                webhook.failure_count += 1
                webhook.last_failure = timezone.now()
                webhook.last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            
            delivery.attempts = 1
            delivery.save()
            webhook.save()
            
        except requests.exceptions.RequestException as e:
            # Erreur de réseau
            delivery.status = 'failed'
            delivery.error_message = str(e)
            delivery.attempts = 1
            delivery.save()
            
            webhook.failure_count += 1
            webhook.last_failure = timezone.now()
            webhook.last_error = str(e)
            webhook.save()
            
        except Exception as e:
            logger.error(f"Erreur livraison webhook {webhook.id}: {e}")
    
    @staticmethod
    def _generate_signature(payload, secret):
        """Générer une signature HMAC pour le webhook"""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def retry_failed_deliveries():
        """Réessayer les livraisons échouées"""
        try:
            # Récupérer les livraisons à réessayer
            now = timezone.now()
            failed_deliveries = WebhookDelivery.objects.filter(
                status='failed',
                attempts__lt=models.F('max_attempts'),
                next_retry__lte=now
            )
            
            for delivery in failed_deliveries:
                WebhookService._retry_delivery(delivery)
                
        except Exception as e:
            logger.error(f"Erreur retry webhooks: {e}")
    
    @staticmethod
    def _retry_delivery(delivery):
        """Réessayer une livraison spécifique"""
        try:
            delivery.attempts += 1
            delivery.status = 'retry'
            
            # Calculer le prochain retry (backoff exponentiel)
            delay_minutes = 2 ** delivery.attempts  # 2, 4, 8 minutes
            delivery.next_retry = timezone.now() + timedelta(minutes=delay_minutes)
            delivery.save()
            
            # Réessayer la livraison
            WebhookService._deliver_webhook(
                delivery.webhook,
                delivery.event,
                delivery.payload
            )
            
        except Exception as e:
            logger.error(f"Erreur retry delivery {delivery.id}: {e}")


class ExternalServiceService:
    """Service de gestion des services externes"""
    
    @staticmethod
    def check_service_health(service_id=None):
        """Vérifier la santé des services externes"""
        try:
            services = ExternalService.objects.filter(is_active=True)
            if service_id:
                services = services.filter(id=service_id)
            
            for service in services:
                ExternalServiceService._check_single_service(service)
                
        except Exception as e:
            logger.error(f"Erreur vérification santé services: {e}")
    
    @staticmethod
    def _check_single_service(service):
        """Vérifier un service spécifique"""
        try:
            start_time = timezone.now()
            
            # Préparer la requête de vérification
            headers = {'User-Agent': 'TelecomSystem-HealthCheck/1.0'}
            if service.headers:
                headers.update(service.headers)
            
            # Envoyer la requête de santé
            response = requests.get(
                f"{service.base_url}/health",
                headers=headers,
                timeout=30
            )
            
            response_time = (timezone.now() - start_time).total_seconds() * 1000
            
            # Déterminer le statut
            if response.status_code == 200:
                status = 'up'
                error_message = ''
                service.status = 'active'
            elif 500 <= response.status_code < 600:
                status = 'down'
                error_message = f"HTTP {response.status_code}"
                service.status = 'error'
            else:
                status = 'degraded'
                error_message = f"HTTP {response.status_code}"
                service.status = 'maintenance'
            
            # Enregistrer le résultat
            ServiceHealthCheck.objects.create(
                service=service,
                status=status,
                response_time=response_time,
                status_code=response.status_code,
                error_message=error_message
            )
            
            # Mettre à jour le service
            service.last_check = timezone.now()
            service.response_time = response_time
            service.save()
            
        except requests.exceptions.RequestException as e:
            # Erreur de réseau
            ServiceHealthCheck.objects.create(
                service=service,
                status='down',
                error_message=str(e)
            )
            
            service.status = 'error'
            service.last_check = timezone.now()
            service.save()
            
        except Exception as e:
            logger.error(f"Erreur vérification service {service.id}: {e}")
    
    @staticmethod
    def call_external_service(service, endpoint, method='GET', data=None, params=None):
        """Appeler un service externe"""
        try:
            url = f"{service.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            headers = {'User-Agent': 'TelecomSystem/1.0'}
            if service.headers:
                headers.update(service.headers)
            
            # Ajouter l'authentification si disponible
            auth = None
            if service.api_key and service.api_secret:
                auth = (service.api_key, service.api_secret)
            elif service.api_key:
                headers['Authorization'] = f'Bearer {service.api_key}'
            
            # Faire la requête
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                auth=auth,
                json=data,
                params=params,
                timeout=30
            )
            
            return {
                'success': response.status_code < 400,
                'status_code': response.status_code,
                'data': response.json() if response.content else {},
                'headers': dict(response.headers)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class APIDocumentationService:
    """Service de génération de documentation API"""
    
    @staticmethod
    def get_api_endpoints():
        """Récupérer tous les endpoints API documentés"""
        endpoints = [
            {
                'endpoint': '/api/auth/login/',
                'method': 'POST',
                'description': 'Authentification utilisateur',
                'parameters': {
                    'email': 'string (required)',
                    'password': 'string (required)'
                },
                'response_example': {
                    'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'user': {
                        'id': 1,
                        'email': 'user@example.com',
                        'role': 'operateur'
                    }
                },
                'authentication_required': False
            },
            {
                'endpoint': '/api/titres/',
                'method': 'GET',
                'description': 'Liste des titres',
                'parameters': {
                    'page': 'integer (optional)',
                    'page_size': 'integer (optional)',
                    'status': 'string (optional)',
                    'type': 'string (optional)'
                },
                'response_example': {
                    'count': 100,
                    'next': 'http://api.example.com/api/titres/?page=2',
                    'previous': None,
                    'results': [
                        {
                            'id': 'uuid',
                            'numero_titre': 'T-2023-001',
                            'type': 'licence_type1',
                            'status': 'approuve'
                        }
                    ]
                },
                'authentication_required': True
            },
            {
                'endpoint': '/api/titres/',
                'method': 'POST',
                'description': 'Créer un nouveau titre',
                'parameters': {
                    'type': 'string (required)',
                    'entreprise_nom': 'string (required)',
                    'proprietaire_id': 'uuid (required)',
                    'duree_ans': 'integer (required)'
                },
                'response_example': {
                    'id': 'uuid',
                    'numero_titre': 'T-2023-001',
                    'type': 'licence_type1',
                    'status': 'en_attente'
                },
                'authentication_required': True
            }
        ]
        
        return endpoints
    
    @staticmethod
    def get_authentication_info():
        """Informations sur l'authentification API"""
        return {
            'type': 'JWT Bearer Token',
            'description': 'Utilisez le token d\'accès dans le header Authorization',
            'header_format': 'Authorization: Bearer <access_token>',
            'token_lifetime': '1 hour',
            'refresh_endpoint': '/api/auth/refresh/'
        }


class APIStatisticsService:
    """Service de statistiques API"""
    
    @staticmethod
    def get_api_statistics(days=30):
        """Récupérer les statistiques API"""
        try:
            start_date = timezone.now() - timedelta(days=days)
            
            # Requêtes totales
            total_requests = APIRequest.objects.filter(
                timestamp__gte=start_date
            ).count()
            
            # Requêtes réussies/échouées
            successful_requests = APIRequest.objects.filter(
                timestamp__gte=start_date,
                status_code__lt=400
            ).count()
            
            failed_requests = total_requests - successful_requests
            
            # Temps de réponse moyen
            avg_response_time = APIRequest.objects.filter(
                timestamp__gte=start_date
            ).aggregate(
                avg=models.Avg('response_time')
            )['avg'] or 0
            
            # Requêtes par endpoint
            requests_by_endpoint = list(APIRequest.objects.filter(
                timestamp__gte=start_date
            ).values('endpoint').annotate(
                count=models.Count('id')
            ).order_by('-count')[:10])
            
            # Requêtes par statut
            requests_by_status = list(APIRequest.objects.filter(
                timestamp__gte=start_date
            ).values('status_code').annotate(
                count=models.Count('id')
            ).order_by('-count'))
            
            # Top clés API
            top_api_keys = list(APIRequest.objects.filter(
                timestamp__gte=start_date
            ).values('api_key__name').annotate(
                count=models.Count('id')
            ).order_by('-count')[:10])
            
            return {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'success_rate': round((successful_requests / total_requests * 100), 2) if total_requests > 0 else 0,
                'average_response_time': round(float(avg_response_time), 3),
                'requests_by_endpoint': requests_by_endpoint,
                'requests_by_status': requests_by_status,
                'top_api_keys': top_api_keys
            }
            
        except Exception as e:
            logger.error(f"Erreur statistiques API: {e}")
            return {}


# Utilitaires pour les intégrations
class IntegrationUtils:
    """Utilitaires pour les intégrations"""
    
    @staticmethod
    def validate_webhook_signature(payload, signature, secret):
        """Valider la signature d'un webhook entrant"""
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    @staticmethod
    def format_api_response(data, success=True, message=None, status_code=200):
        """Formater une réponse API standardisée"""
        response = {
            'success': success,
            'timestamp': timezone.now().isoformat(),
            'data': data if success else None,
            'error': None if success else (message or 'An error occurred')
        }
        
        if message and success:
            response['message'] = message
            
        return response, status_code
    
    @staticmethod
    def paginate_response(queryset, page, page_size=20):
        """Paginer une réponse API"""
        try:
            from django.core.paginator import Paginator
            
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            
            return {
                'count': paginator.count,
                'num_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'results': list(page_obj)
            }
        except Exception as e:
            logger.error(f"Erreur pagination: {e}")
            return {
                'count': 0,
                'num_pages': 0,
                'current_page': 1,
                'has_next': False,
                'has_previous': False,
                'results': []
            }
        