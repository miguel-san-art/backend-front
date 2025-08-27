# users/permissions.py
from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    """Autorisation uniquement pour les administrateurs."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'admin'

class IsPersonnel(BasePermission):
    """Autorisation uniquement pour le personnel."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'personnel'

class IsOperateur(BasePermission):
    """Autorisation uniquement pour les opérateurs."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'operateur'

class IsOwnerOrAdmin(BasePermission):
    """Autorisation pour modifier uniquement son propre profil ou pour admin."""
    def has_object_permission(self, request, view, obj):
        # Admins peuvent tout faire
        if hasattr(request.user, 'profile') and request.user.profile.role == 'admin':
            return True
            
        # Utilisateurs peuvent voir ou modifier leur propre profil
        return obj.id == request.user.id
