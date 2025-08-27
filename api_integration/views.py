# api_integration/views.py
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse
import json

from .models import APIKey, APIRequest, Webhook, WebhookDelivery, ExternalService, ServiceHealthCheck
from .serializers import (
    APIKeySerializer, APIRequestSerializer, WebhookSerializer, WebhookDeliverySerializer,
    ExternalServiceSerializer, ServiceHealthCheckSerializer, APIDocumentationSerializer,
    APIStatisticsSerializer
)
from .services import APIKeyService, WebhookService, ExternalServiceService, APIDocumentationService, APIStatisticsService


def admin_required(view_func):
    """Décorateur pour vérifier les permissions admin"""
    def wrapper(request, *args, **kwargs):
        if not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
            return Response(
                {'error': 'Admin access required'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper


class APIKeyListView(generics.ListCreateAPIView):
    """Liste et création des clés API"""
    serializer_class = APIKeySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            return APIKey.objects.all().order_by('-created_at')
        else:
            return APIKey.objects.none()


class APIKeyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Détail, modification et suppression des clés API"""
    serializer_class = APIKeySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            return APIKey.objects.all()
        else:
            return APIKey.objects.none()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerate_api_key(request, pk):
    """Régénérer une clé API"""
    if not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        return Response(
            {'error': 'Admin access required'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    api_key = get_object_or_404(APIKey, pk=pk)
    
    # Générer nouvelles clés
    api_key.key = APIKey.generate_key()
    api_key.secret = APIKey.generate_secret()
    api_key.save()
    
    return Response({
        'message': 'API key regenerated successfully',
        'new_key': api_key.key
    })


class APIRequestListView(generics.ListAPIView):
    """Liste des requêtes API"""
    serializer_class = APIRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if not (hasattr(self.request.user, 'profile') and self.request.user.profile.role in ['admin', 'personnel']):
            return APIRequest.objects.none()
        
        queryset = APIRequest.objects.all()
        
        # Filtres
        api_key_id = self.request.query_params.get('api_key_id')
        if api_key_id:
            queryset = queryset.filter(api_key_id=api_key_id)
        
        method = self.request.query_params.get('method')
        if method:
            queryset = queryset.filter(method=method)
        
        status_code = self.request.query_params.get('status_code')
        if status_code:
            queryset = queryset.filter(status_code=status_code)
        
        # Période
        days = self.request.query_params.get('days', 7)
        try:
            days = int(days)
            start_date = timezone.now() - timezone.timedelta(days=days)
            queryset = queryset.filter(timestamp__gte=start_date)
        except ValueError:
            pass
        
        return queryset.order_by('-timestamp')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_statistics(request):
    """Statistiques des requêtes API"""
    if not (hasattr(request.user, 'profile') and request.user.profile.role in ['admin', 'personnel']):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    days = int(request.query_params.get('days', 30))
    stats = APIStatisticsService.get_api_statistics(days)
    
    serializer = APIStatisticsSerializer(stats)
    return Response(serializer.data)


class WebhookListView(generics.ListCreateAPIView):
    """Liste et création des webhooks"""
    serializer_class = WebhookSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            return Webhook.objects.all().order_by('-created_at')
        else:
            return Webhook.objects.none()


class WebhookDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Détail, modification et suppression des webhooks"""
    serializer_class = WebhookSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            return Webhook.objects.all()
        else:
            return Webhook.objects.none()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_webhook(request, pk):
    """Tester un webhook"""
    if not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        return Response(
            {'error': 'Admin access required'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    webhook = get_object_or_404(Webhook, pk=pk)
    
    # Payload de test
    test_payload = {
        'test': True,
        'message': 'Ceci est un test de webhook',
        'timestamp': timezone.now().isoformat(),
        'webhook_id': str(webhook.id)
    }
    
    # Envoyer le webhook de test
    WebhookService.send_webhook('test.webhook', test_payload, webhook.id)
    
    return Response({
        'message': 'Test webhook sent successfully'
    })


class WebhookDeliveryListView(generics.ListAPIView):
    """Liste des livraisons de webhooks"""
    serializer_class = WebhookDeliverySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if not (hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin'):
            return WebhookDelivery.objects.none()
        
        queryset = WebhookDelivery.objects.all()
        
        webhook_id = self.request.query_params.get('webhook_id')
        if webhook_id:
            queryset = queryset.filter(webhook_id=webhook_id)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def retry_webhook_delivery(request, pk):
    """Réessayer une livraison de webhook"""
    if not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        return Response(
            {'error': 'Admin access required'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    delivery = get_object_or_404(WebhookDelivery, pk=pk)
    
    if delivery.status == 'success':
        return Response(
            {'error': 'Cannot retry successful delivery'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Réinitialiser pour retry
    delivery.status = 'pending'
    delivery.attempts = 0
    delivery.next_retry = timezone.now()
    delivery.save()
    
    # Réessayer
    WebhookService.send_webhook(
        delivery.event, 
        delivery.payload, 
        delivery.webhook.id
    )
    
    return Response({
        'message': 'Webhook delivery retry initiated'
    })


class ExternalServiceListView(generics.ListCreateAPIView):
    """Liste et création des services externes"""
    serializer_class = ExternalServiceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            return ExternalService.objects.all().order_by('name')
        else:
            return ExternalService.objects.none()


class ExternalServiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Détail, modification et suppression des services externes"""
    serializer_class = ExternalServiceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            return ExternalService.objects.all()
        else:
            return ExternalService.objects.none()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_service_health(request, pk=None):
    """Vérifier la santé d'un service"""
    if not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        return Response(
            {'error': 'Admin access required'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    if pk:
        service = get_object_or_404(ExternalService, pk=pk)
        ExternalServiceService.check_service_health(service.id)
        message = f'Health check initiated for {service.name}'
    else:
        ExternalServiceService.check_service_health()
        message = 'Health check initiated for all services'
    
    return Response({
        'message': message
    })


class ServiceHealthCheckListView(generics.ListAPIView):
    """Liste des vérifications de santé"""
    serializer_class = ServiceHealthCheckSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if not (hasattr(self.request.user, 'profile') and self.request.user.profile.role in ['admin', 'personnel']):
            return ServiceHealthCheck.objects.none()
        
        queryset = ServiceHealthCheck.objects.all()
        
        service_id = self.request.query_params.get('service_id')
        if service_id:
            queryset = queryset.filter(service_id=service_id)
        
        return queryset.order_by('-checked_at')


@api_view(['GET'])
def api_documentation(request):
    """Documentation interactive de l'API"""
    endpoints = APIDocumentationService.get_api_endpoints()
    auth_info = APIDocumentationService.get_authentication_info()
    
    return Response({
        'title': 'API Système de Gestion des Télécommunications',
        'version': '1.0',
        'description': 'API REST pour la gestion des titres et licences de télécommunications',
        'base_url': request.build_absolute_uri('/api/'),
        'authentication': auth_info,
        'endpoints': endpoints
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def integration_dashboard(request):
    """Tableau de bord des intégrations"""
    if not (hasattr(request.user, 'profile') and request.user.profile.role in ['admin', 'personnel']):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Statistiques générales
    stats = {
        'active_api_keys': APIKey.objects.filter(is_active=True, status='active').count(),
        'total_api_requests': APIRequest.objects.count(),
        'active_webhooks': Webhook.objects.filter(is_active=True, status='active').count(),
        'external_services': ExternalService.objects.filter(is_active=True).count(),
        'services_up': ServiceHealthCheck.objects.filter(
            status='up'
        ).values('service').distinct().count(),
    }
    
    # Requêtes récentes (dernières 24h)
    last_24h = timezone.now() - timezone.timedelta(hours=24)
    recent_requests = APIRequest.objects.filter(
        timestamp__gte=last_24h
    ).count()
    
    # Webhooks récents
    recent_deliveries = WebhookDelivery.objects.filter(
        created_at__gte=last_24h
    ).values('status').annotate(count=Count('id'))
    
    # Services avec problèmes
    problematic_services = ExternalService.objects.filter(
        status__in=['error', 'maintenance']
    ).values('name', 'status')
    
    return Response({
        'statistics': stats,
        'recent_requests_24h': recent_requests,
        'recent_webhook_deliveries': list(recent_deliveries),
        'problematic_services': list(problematic_services)
    })


# Endpoint pour recevoir des webhooks (exemple)
@api_view(['POST'])
def receive_webhook(request, source):
    """Recevoir un webhook d'un service externe"""
    try:
        # Ici vous pouvez traiter les webhooks entrants
        # Par exemple, d'un service de paiement, SMS, etc.
        
        payload = request.data
        headers = request.headers
        
        # Traitement selon la source
        if source == 'payment':
            # Traiter webhook de paiement
            pass
        elif source == 'sms':
            # Traiter webhook SMS
            pass
        
        return JsonResponse({
            'status': 'received',
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)
    