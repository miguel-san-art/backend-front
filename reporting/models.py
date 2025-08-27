# reporting/models.py
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class Report(models.Model):
    REPORT_TYPES = [
        ('titres', 'Rapport des Titres'),
        ('demandes', 'Rapport des Demandes'),
        ('users', 'Rapport des Utilisateurs'),
        ('statistiques', 'Rapport Statistiques'),
        ('expiration', 'Rapport d\'Expiration'),
    ]
    
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    filters = models.JSONField(default=dict, blank=True)
    file_path = models.CharField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name} - {self.get_report_type_display()}"

class Dashboard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    config = models.JSONField(default=dict)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        
    def __str__(self):
        return f"Dashboard: {self.name} - {self.user.email}"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('view', 'Consultation'),
        ('export', 'Export'),
        ('login', 'Connexion'),
        ('logout', 'Déconnexion'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='system_admin_audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.user} - {self.get_action_display()} - {self.model_name}"
