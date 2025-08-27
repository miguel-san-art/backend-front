# users/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
import uuid

class UserManager(BaseUserManager):
    """Manager personnalisé pour User."""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Un email est requis')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    """Modèle utilisateur personnalisé avec email comme identifiant."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None  # Supprimer username par défaut
    email = models.EmailField(_('email address'), unique=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    def __str__(self):
        return self.email

class Profile(models.Model):
    """Profil étendu de l'utilisateur."""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('personnel', 'Personnel'),
        ('operateur', 'Opérateur'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    nom = models.CharField(max_length=255)
    prenom = models.CharField(max_length=255)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='operateur')
    entreprise = models.CharField(max_length=255, blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.role})"
