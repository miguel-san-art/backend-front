# users/views.py
from rest_framework import viewsets, status, generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .models import User, Profile
from .serializers import UserSerializer, UserCreateSerializer, ProfileSerializer, PasswordChangeSerializer
from .permissions import IsAdmin, IsOwnerOrAdmin

class UserViewSet(viewsets.ModelViewSet):
    """API endpoint pour les utilisateurs."""
    queryset = User.objects.all()
    permission_classes = [IsAdmin]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    def get_queryset(self):
        # Filtrage par rôle si spécifié
        role = self.request.query_params.get('role', None)
        queryset = User.objects.all()
        
        if role:
            queryset = queryset.filter(profile__role=role)
            
        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[IsOwnerOrAdmin])
    def change_password(self, request, pk=None):
        user = self.get_object()
        serializer = PasswordChangeSerializer(data=request.data)
        
        if serializer.is_valid():
            # Vérifier l'ancien mot de passe
            if not user.check_password(serializer.validated_data.get("current_password")):
                return Response({"current_password": ["Mot de passe incorrect."]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Définir le nouveau mot de passe
            user.set_password(serializer.validated_data.get("new_password"))
            user.save()
            return Response({"status": "Mot de passe modifié avec succès."})
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get', 'put', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Retourne ou modifie les informations de l'utilisateur connecté."""
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        
        elif request.method in ['PUT', 'PATCH']:
            partial = request.method == 'PATCH'
            serializer = self.get_serializer(request.user, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Supprimer un utilisateur (soft delete)"""
        user = self.get_object()
        # Option 1: Désactivation (soft delete)
        user.is_active = False
        user.save()
        return Response({"detail": "Utilisateur désactivé avec succès"}, status=status.HTTP_204_NO_CONTENT)
        
        # Option 2: Suppression physique (décommentez si nécessaire)
        # return super().destroy(request, *args, **kwargs)    

class ProfileViewSet(viewsets.ModelViewSet):
    """API endpoint pour les profils d'utilisateurs."""
    serializer_class = ProfileSerializer
    permission_classes = [IsOwnerOrAdmin]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            return Profile.objects.all()
        return Profile.objects.filter(user=self.request.user)

class RegisterView(generics.CreateAPIView):
    """API pour l'inscription des opérateurs."""
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserCreateSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Force le rôle à 'operateur' pour l'inscription
        profile_data = serializer.validated_data.get('profile', {})
        profile_data['role'] = 'operateur'
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({"message": "Utilisateur créé avec succès."}, status=status.HTTP_201_CREATED, headers=headers)