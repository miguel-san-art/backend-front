# users/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Profile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Crée un profil utilisateur lorsqu'un utilisateur est créé."""
    if created and not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)
