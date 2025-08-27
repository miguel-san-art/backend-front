# users/serializers.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Profile

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['nom', 'prenom', 'telephone', 'role', 'entreprise', 'adresse', 'created_at']
        read_only_fields = ['created_at']

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'is_active', 'profile']
        read_only_fields = ['id']
        
    def update(self, instance, validated_data):
        """Méthode pour mettre à jour un utilisateur existant"""
        profile_data = validated_data.pop('profile', None)
        
        # Mise à jour des champs de l'utilisateur
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Gérer le changement de mot de passe séparément pour le hacher
        password = validated_data.get('password', None)
        if password:
            instance.set_password(password)
        
        instance.save()
        
        # Mise à jour du profil si des données sont fournies
        if profile_data and hasattr(instance, 'profile'):
            for attr, value in profile_data.items():
                setattr(instance.profile, attr, value)
            instance.profile.save()
        
        return instance

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    profile = ProfileSerializer(required=True)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'profile']
        
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        return attrs
        
    def create(self, validated_data):
        profile_data = validated_data.pop('profile')
        password = validated_data.pop('password')
        password_confirm = validated_data.pop('password_confirm', None)  # Remove from validated data
        
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        
        Profile.objects.create(user=user, **profile_data)
        return user

class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Les nouveaux mots de passe ne correspondent pas."})
        return attrs
    