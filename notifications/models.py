# notifications/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()

class Notification(models.Model):
    TYPE_CHOICES = [
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('error', 'Erreur'),
        ('success', 'Succès'),
        ('expiration', 'Expiration'),
        ('status_change', 'Changement de statut'),
        ('assignment', 'Assignation'),
        ('reminder', 'Rappel'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('medium', 'Moyenne'),
        ('high', 'Haute'),
        ('urgent', 'Urgente'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Relations optionnelles
    related_titre_id = models.UUIDField(null=True, blank=True)
    related_demande_id = models.UUIDField(null=True, blank=True)
    
    # État
    is_read = models.BooleanField(default=False)
    is_sent_email = models.BooleanField(default=False)
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['type']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.email}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

class EmailTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    subject_template = models.CharField(max_length=200)
    body_template = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Préférences par type
    email_expiration = models.BooleanField(default=True, help_text="Email pour les expirations")
    email_status_change = models.BooleanField(default=True, help_text="Email pour changement de statut")
    email_assignment = models.BooleanField(default=True, help_text="Email pour les assignations")
    email_reminders = models.BooleanField(default=True, help_text="Email pour les rappels")
    
    # Notifications in-app
    app_all_notifications = models.BooleanField(default=True, help_text="Toutes les notifications in-app")
    
    # Fréquence des rappels
    reminder_frequency_days = models.PositiveIntegerField(default=7, help_text="Fréquence des rappels en jours")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Préférences de {self.user.email}"
