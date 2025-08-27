# api_integration/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
import secrets


class APIKey(models.Model):
    """Clés d'API pour les intégrations externes"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expirée'),
        ('revoked', 'Révoquée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="Nom de la clé")
    key = models.CharField(max_length=64, unique=True, verbose_name="Clé API")
    secret = models.CharField(max_length=128, verbose_name="Secret")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Permissions et restrictions
    allowed_ips = models.TextField(blank=True, verbose_name="IPs autorisées (une par ligne)")
    allowed_endpoints = models.JSONField(default=list, verbose_name="Endpoints autorisés")
    rate_limit = models.IntegerField(default=1000, verbose_name="Limite de requêtes/heure")
    
    # État
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    is_active = models.BooleanField(default=True)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Date d'expiration")
    last_used = models.DateTimeField(null=True, blank=True)
    
    # Relations
    #created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = "Clé API"
        verbose_name_plural = "Clés API"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.key[:8]}...)"
    
    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        if not self.secret:
            self.secret = self.generate_secret()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_key():
        """Générer une clé API unique"""
        return f"tk_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def generate_secret():
        """Générer un secret API"""
        return secrets.token_urlsafe(64)
    
    @property
    def is_expired(self):
        """Vérifier si la clé a expiré"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def get_allowed_ips_list(self):
        """Retourner la liste des IPs autorisées"""
        if not self.allowed_ips:
            return []
        return [ip.strip() for ip in self.allowed_ips.split('\n') if ip.strip()]


class APIRequest(models.Model):
    """Log des requêtes API"""
    
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE, related_name='requests')
    
    # Détails de la requête
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    endpoint = models.CharField(max_length=500)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    # Réponse
    status_code = models.IntegerField()
    response_time = models.DecimalField(max_digits=10, decimal_places=3, verbose_name="Temps de réponse (ms)")
    response_size = models.BigIntegerField(null=True, blank=True, verbose_name="Taille de la réponse (bytes)")
    
    # Métadonnées
    timestamp = models.DateTimeField(auto_now_add=True)
    request_data = models.JSONField(default=dict, blank=True, verbose_name="Données de la requête")
    error_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Requête API"
        verbose_name_plural = "Requêtes API"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['api_key', '-timestamp']),
            models.Index(fields=['status_code', '-timestamp']),
            models.Index(fields=['endpoint', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.status_code}"


class Webhook(models.Model):
    """Configuration des webhooks pour les notifications"""
    
    EVENT_CHOICES = [
        ('titre.created', 'Titre créé'),
        ('titre.updated', 'Titre modifié'),
        ('titre.expired', 'Titre expiré'),
        ('demande.created', 'Demande créée'),
        ('demande.updated', 'Demande modifiée'),
        ('demande.approved', 'Demande approuvée'),
        ('demande.rejected', 'Demande rejetée'),
        ('user.created', 'Utilisateur créé'),
        ('system.maintenance', 'Maintenance système'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Actif'),
        ('inactive', 'Inactif'),
        ('failed', 'En échec'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="Nom du webhook")
    url = models.URLField(verbose_name="URL de destination")
    description = models.TextField(blank=True)
    
    # Configuration
    events = models.JSONField(default=list, verbose_name="Événements surveillés")
    secret = models.CharField(max_length=64, blank=True, verbose_name="Secret pour signature")
    headers = models.JSONField(default=dict, blank=True, verbose_name="Headers personnalisés")
    
    # État
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    is_active = models.BooleanField(default=True)
    
    # Statistiques
    success_count = models.IntegerField(default=0, verbose_name="Succès")
    failure_count = models.IntegerField(default=0, verbose_name="Échecs")
    last_success = models.DateTimeField(null=True, blank=True)
    last_failure = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    #created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = "Webhook"
        verbose_name_plural = "Webhooks"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.url})"
    
    def save(self, *args, **kwargs):
        if not self.secret:
            self.secret = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)


class WebhookDelivery(models.Model):
    """Logs des livraisons de webhooks"""
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('success', 'Succès'),
        ('failed', 'Échec'),
        ('retry', 'Retry'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook = models.ForeignKey(Webhook, on_delete=models.CASCADE, related_name='deliveries')
    
    # Détails de l'événement
    event = models.CharField(max_length=50)
    payload = models.JSONField()
    
    # Livraison
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    http_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    
    # Tentatives
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    next_retry = models.DateTimeField(null=True, blank=True)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Livraison Webhook"
        verbose_name_plural = "Livraisons Webhook"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.webhook.name} - {self.event} ({self.status})"


class ExternalService(models.Model):
    """Configuration des services externes"""
    
    SERVICE_TYPES = [
        ('sms', 'Service SMS'),
        ('email', 'Service Email'),
        ('payment', 'Service de Paiement'),
        ('document', 'Service de Documents'),
        ('notification', 'Service de Notifications'),
        ('storage', 'Service de Stockage'),
        ('other', 'Autre'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Actif'),
        ('inactive', 'Inactif'),
        ('maintenance', 'Maintenance'),
        ('error', 'Erreur'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="Nom du service")
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    base_url = models.URLField(verbose_name="URL de base")
    description = models.TextField(blank=True)
    
    # Configuration
    api_key = models.CharField(max_length=200, blank=True, verbose_name="Clé API")
    api_secret = models.CharField(max_length=200, blank=True, verbose_name="Secret API")
    config = models.JSONField(default=dict, verbose_name="Configuration additionnelle")
    headers = models.JSONField(default=dict, verbose_name="Headers par défaut")
    
    # État
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    is_active = models.BooleanField(default=True)
    
    # Monitoring
    last_check = models.DateTimeField(null=True, blank=True)
    response_time = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    uptime_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    #created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = "Service Externe"
        verbose_name_plural = "Services Externes"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_service_type_display()})"


class ServiceHealthCheck(models.Model):
    """Vérifications de santé des services externes"""
    
    STATUS_CHOICES = [
        ('up', 'Opérationnel'),
        ('down', 'Hors service'),
        ('degraded', 'Dégradé'),
        ('unknown', 'Inconnu'),
    ]
    
    service = models.ForeignKey(ExternalService, on_delete=models.CASCADE, related_name='health_checks')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    response_time = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    checked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Vérification de Santé"
        verbose_name_plural = "Vérifications de Santé"
        ordering = ['-checked_at']
    
    def __str__(self):
        return f"{self.service.name} - {self.get_status_display()}"
    