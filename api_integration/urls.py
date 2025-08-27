# api_integration/urls.py
from django.urls import path
from . import views

app_name = 'api_integration'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.integration_dashboard, name='integration-dashboard'),
    path('documentation/', views.api_documentation, name='api-documentation'),
    
    # Clés API
    path('api-keys/', views.APIKeyListView.as_view(), name='apikey-list'),
    path('api-keys/<uuid:pk>/', views.APIKeyDetailView.as_view(), name='apikey-detail'),
    path('api-keys/<uuid:pk>/regenerate/', views.regenerate_api_key, name='apikey-regenerate'),
    
    # Logs des requêtes API
    path('requests/', views.APIRequestListView.as_view(), name='apirequest-list'),
    path('requests/statistics/', views.api_statistics, name='api-statistics'),
    
    # Webhooks
    path('webhooks/', views.WebhookListView.as_view(), name='webhook-list'),
    path('webhooks/<uuid:pk>/', views.WebhookDetailView.as_view(), name='webhook-detail'),
    path('webhooks/<uuid:pk>/test/', views.test_webhook, name='webhook-test'),
    
    # Livraisons de webhooks
    path('webhook-deliveries/', views.WebhookDeliveryListView.as_view(), name='webhook-delivery-list'),
    path('webhook-deliveries/<uuid:pk>/retry/', views.retry_webhook_delivery, name='webhook-delivery-retry'),
    
    # Services externes
    path('external-services/', views.ExternalServiceListView.as_view(), name='external-service-list'),
    path('external-services/<uuid:pk>/', views.ExternalServiceDetailView.as_view(), name='external-service-detail'),
    path('external-services/<uuid:pk>/health/', views.check_service_health, name='service-health-check'),
    path('external-services/health-check-all/', views.check_service_health, name='all-services-health-check'),
    
    # Vérifications de santé
    path('health-checks/', views.ServiceHealthCheckListView.as_view(), name='health-check-list'),
    
    # Webhooks entrants (exemples)
    path('webhooks/receive/<str:source>/', views.receive_webhook, name='receive-webhook'),
]
