# api_integration/middleware.py
import time
import json
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone

from .services import APIKeyService


class APIKeyMiddleware(MiddlewareMixin):
    """Middleware pour valider les clés API"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        # Vérifier seulement les endpoints API
        if not request.path.startswith('/api/'):
            return None
        
        # Ignorer certains endpoints (documentation, auth, etc.)
        excluded_paths = [
            '/api/auth/',
            '/api/documentation/',
            '/api/webhooks/receive/',
        ]
        
        for path in excluded_paths:
            if request.path.startswith(path):
                return None
        
        # Récupérer la clé API
        api_key = self._extract_api_key(request)
        
        if not api_key:
            return JsonResponse({
                'error': 'API key required',
                'message': 'Provide API key in X-API-Key header'
            }, status=401)
        
        # Valider la clé API
        is_valid, result = APIKeyService.validate_api_key(
            key=api_key,
            ip_address=self._get_client_ip(request),
            endpoint=request.path
        )
        
        if not is_valid:
            return JsonResponse({
                'error': 'Invalid API key',
                'message': result
            }, status=403)
        
        # Stocker la clé API validée dans la requête
        request.api_key = result
        
        # Enregistrer le début de la requête pour les métriques
        request._api_start_time = time.time()
        
        return None
    
    def process_response(self, request, response):
        # Enregistrer les métriques de la requête API
        if hasattr(request, 'api_key') and hasattr(request, '_api_start_time'):
            response_time = (time.time() - request._api_start_time) * 1000
            
            # Extraire les données de la requête (limitées)
            request_data = {}
            if request.method == 'POST':
                try:
                    if hasattr(request, 'data'):
                        request_data = dict(request.data)
                    elif request.content_type == 'application/json':
                        request_data = json.loads(request.body.decode('utf-8'))
                except:
                    pass
            
            # Log de la requête
            APIKeyService.log_request(
                api_key=request.api_key,
                method=request.method,
                endpoint=request.path,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                status_code=response.status_code,
                response_time=response_time,
                response_size=len(response.content) if hasattr(response, 'content') else None,
                request_data=request_data,
                error_message=None if response.status_code < 400 else 'API Error'
            )
        
        return response
    
    def _extract_api_key(self, request):
        """Extraire la clé API de la requête"""
        # Vérifier le header X-API-Key
        api_key = request.META.get('HTTP_X_API_KEY')
        
        if not api_key:
            # Vérifier le paramètre de requête
            api_key = request.GET.get('api_key')
        
        return api_key
    
    def _get_client_ip(self, request):
        """Obtenir l'adresse IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class APIResponseMiddleware(MiddlewareMixin):
    """Middleware pour standardiser les réponses API"""
    
    def process_response(self, request, response):
        # Appliquer seulement aux endpoints API
        if not request.path.startswith('/api/'):
            return response
        
        # Ajouter des headers CORS si nécessaire
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-API-Key'
        
        # Ajouter des headers de sécurité
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Middleware pour la limitation de taux global"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        # Vérifier seulement les endpoints API
        if not request.path.startswith('/api/'):
            return None
        
        # Implémenter une limitation de taux basique par IP
        from django.core.cache import cache
        
        ip_address = self._get_client_ip(request)
        cache_key = f"rate_limit:{ip_address}"
        current_hour = timezone.now().replace(minute=0, second=0, microsecond=0)
        counter_key = f"{cache_key}:{current_hour.timestamp()}"
        
        # Limite globale: 10000 requêtes par heure par IP
        current_count = cache.get(counter_key, 0)
        max_requests = 10000
        
        if current_count >= max_requests:
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': f'Maximum {max_requests} requests per hour allowed'
            }, status=429)
        
        # Incrémenter le compteur
        cache.set(counter_key, current_count + 1, timeout=3600)
        
        return None
    
    def _get_client_ip(self, request):
        """Obtenir l'adresse IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    