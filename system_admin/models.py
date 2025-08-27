# system_admin/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
import json


class SystemConfiguration(models.Model):
    """Configuration générale du système"""
    
    key = models.CharField(max_length=100, unique=True, verbose_name="Clé de configuration")
    value = models.TextField(verbose_name="Valeur")
    description = models.TextField(blank=True, verbose_name="Description")
    category = models.CharField(max_length=50, default='general', verbose_name="Catégorie")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    #updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = "Configuration Système"
        verbose_name_plural = "Configurations Système"
        ordering = ['category', 'key']
    
    def __str__(self):
        return f"{self.category}: {self.key}"
    
    def get_value(self):
        """Retourner la valeur parsée selon le type"""
        try:
            # Essayer de parser comme JSON pour les objets/arrays
            return json.loads(self.value)
        except (json.JSONDecodeError, TypeError):
            # Retourner comme string si ce n'est pas du JSON
            return self.value
    
    def set_value(self, value):
        """Définir la valeur en la convertissant si nécessaire"""
        if isinstance(value, (dict, list)):
            self.value = json.dumps(value, ensure_ascii=False)
        else:
            self.value = str(value)


class AuditLog(models.Model):
    """Journal d'audit des actions système"""
    
    ACTION_CHOICES = [
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('login', 'Connexion'),
        ('logout', 'Déconnexion'),
        ('export', 'Export'),
        ('import', 'Import'),
        ('config', 'Configuration'),
        ('backup', 'Sauvegarde'),
        ('restore', 'Restauration'),
    ]
    
    LEVEL_CHOICES = [
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('error', 'Erreur'),
        ('critical', 'Critique'),
    ]
    
    #user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='info')
    resource_type = models.CharField(max_length=50, verbose_name="Type de ressource")
    resource_id = models.CharField(max_length=100, blank=True, verbose_name="ID de ressource")
    description = models.TextField(verbose_name="Description")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Journal d'Audit"
        verbose_name_plural = "Journaux d'Audit"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['level', '-timestamp']),
            models.Index(fields=['resource_type', '-timestamp']),
        ]
    
    def __str__(self):
        user_str = self.user.get_full_name() if self.user else "Système"
        return f"[{self.timestamp}] {user_str} - {self.get_action_display()}: {self.description[:50]}"


class SystemBackup(models.Model):
    """Gestion des sauvegardes système"""
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('running', 'En cours'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
    ]
    
    TYPE_CHOICES = [
        ('full', 'Complète'),
        ('incremental', 'Incrémentale'),
        ('data_only', 'Données seules'),
        ('config_only', 'Configuration seule'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Nom de la sauvegarde")
    backup_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='full')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file_path = models.CharField(max_length=500, blank=True, verbose_name="Chemin du fichier")
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name="Taille (bytes)")
    description = models.TextField(blank=True, verbose_name="Description")
    #created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Sauvegarde Système"
        verbose_name_plural = "Sauvegardes Système"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    @property
    def duration(self):
        """Durée de la sauvegarde"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def formatted_file_size(self):
        """Taille formatée du fichier"""
        if not self.file_size:
            return "N/A"
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"


class SystemMetrics(models.Model):
    """Métriques système pour le monitoring"""
    
    METRIC_TYPES = [
        ('users_active', 'Utilisateurs actifs'),
        ('requests_count', 'Nombre de requêtes'),
        ('response_time', 'Temps de réponse (ms)'),
        ('error_rate', 'Taux d\'erreur (%)'),
        ('database_size', 'Taille base de données (MB)'),
        ('storage_used', 'Stockage utilisé (MB)'),
        ('memory_usage', 'Utilisation mémoire (%)'),
        ('cpu_usage', 'Utilisation CPU (%)'),
    ]
    
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES)
    value = models.DecimalField(max_digits=15, decimal_places=2)
    unit = models.CharField(max_length=20, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = "Métrique Système"
        verbose_name_plural = "Métriques Système"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['metric_type', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_metric_type_display()}: {self.value} {self.unit}"


class SystemMaintenance(models.Model):
    """Planification des maintenances système"""
    
    STATUS_CHOICES = [
        ('scheduled', 'Planifiée'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminée'),
        ('cancelled', 'Annulée'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('medium', 'Moyenne'),
        ('high', 'Haute'),
        ('critical', 'Critique'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(verbose_name="Description")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    scheduled_start = models.DateTimeField(verbose_name="Début planifié")
    scheduled_end = models.DateTimeField(verbose_name="Fin planifiée")
    actual_start = models.DateTimeField(null=True, blank=True, verbose_name="Début réel")
    actual_end = models.DateTimeField(null=True, blank=True, verbose_name="Fin réelle")
    impact_description = models.TextField(blank=True, verbose_name="Description de l'impact")
    notification_sent = models.BooleanField(default=False, verbose_name="Notification envoyée")
    #created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Maintenance Système"
        verbose_name_plural = "Maintenances Système"
        ordering = ['scheduled_start']
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    @property
    def is_active(self):
        """Vérifier si la maintenance est actuellement active"""
        now = timezone.now()
        return (self.status == 'in_progress' or 
                (self.scheduled_start <= now <= self.scheduled_end))
    