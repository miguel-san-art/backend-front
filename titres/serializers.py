# titres/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from .models import Titre, HistoriqueTitre, RedevanceTitre

User = get_user_model()

class ProprietaireSerializer(serializers.ModelSerializer):
    """Serializer pour les informations basiques du propriétaire."""
    nom_complet = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'nom_complet']
    
    def get_nom_complet(self, obj):
        if hasattr(obj, 'profile'):
            return f"{obj.profile.nom} {obj.profile.prenom}"
        return obj.email

class RedevanceTitreSerializer(serializers.ModelSerializer):
    """Serializer pour les redevances des titres."""
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = RedevanceTitre
        fields = [
            'id', 'annee', 'montant', 'date_echeance', 'date_paiement',
            'status_paiement', 'reference_paiement', 'commentaires',
            'is_overdue', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class HistoriqueTitreSerializer(serializers.ModelSerializer):
    """Serializer pour l'historique des titres."""
    utilisateur_nom = serializers.SerializerMethodField()
    
    class Meta:
        model = HistoriqueTitre
        fields = [
            'id', 'action', 'utilisateur', 'utilisateur_nom', 'commentaire',
            'ancien_status', 'nouveau_status', 'date_action', 'donnees_modifiees'
        ]
        read_only_fields = ['date_action']
    
    def get_utilisateur_nom(self, obj):
        if obj.utilisateur and hasattr(obj.utilisateur, 'profile'):
            return f"{obj.utilisateur.profile.nom} {obj.utilisateur.profile.prenom}"
        elif obj.utilisateur:
            return obj.utilisateur.email
        return "Système"

class TitreSerializer(serializers.ModelSerializer):
    """Serializer principal pour les titres."""
    proprietaire_info = ProprietaireSerializer(source='proprietaire', read_only=True)
    is_expired = serializers.ReadOnlyField()
    days_until_expiration = serializers.ReadOnlyField()
    is_expiring_soon = serializers.ReadOnlyField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    redevances = RedevanceTitreSerializer(many=True, read_only=True)
    historique = HistoriqueTitreSerializer(many=True, read_only=True)
    
    class Meta:
        model = Titre
        fields = [
            'id', 'numero_titre', 'type', 'type_display', 'proprietaire', 'proprietaire_info',
            'entreprise_nom', 'date_emission', 'date_expiration', 'duree_ans', 'status',
            'status_display', 'description', 'conditions_specifiques', 'redevance_annuelle',
            'is_expired', 'days_until_expiration', 'is_expiring_soon', 'redevances',
            'historique', 'created_at', 'updated_at'
        ]
        read_only_fields = ['numero_titre', 'redevance_annuelle', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validation des données du titre."""
        # Vérifier que la date d'expiration est après la date d'émission
        if attrs.get('date_expiration') and attrs.get('date_emission'):
            if attrs['date_expiration'] <= attrs['date_emission']:
                raise serializers.ValidationError({
                    "date_expiration": "La date d'expiration doit être postérieure à la date d'émission."
                })
        
        # Vérifier que la durée est cohérente avec les dates
        if attrs.get('duree_ans') and attrs.get('date_emission') and attrs.get('date_expiration'):
            expected_expiration = attrs['date_emission'] + timedelta(days=attrs['duree_ans'] * 365)
            if abs((attrs['date_expiration'] - expected_expiration).days) > 7:  # Tolérance de 7 jours
                raise serializers.ValidationError({
                    "duree_ans": "La durée n'est pas cohérente avec les dates d'émission et d'expiration."
                })
        
        return attrs
    
    def create(self, validated_data):
        """Création d'un nouveau titre avec historique."""
        titre = super().create(validated_data)
        
        # Créer l'entrée d'historique pour la création
        HistoriqueTitre.objects.create(
            titre=titre,
            action='creation',
            utilisateur=self.context['request'].user,
            nouveau_status=titre.status,
            commentaire=f"Titre créé: {titre.numero_titre}"
        )
        
        return titre
    
    def update(self, instance, validated_data):
        """Mise à jour d'un titre avec historique."""
        ancien_status = instance.status
        ancien_data = {
            'status': instance.status,
            'description': instance.description,
            'conditions_specifiques': instance.conditions_specifiques,
        }
        
        titre = super().update(instance, validated_data)
        
        # Créer l'entrée d'historique pour la modification
        if ancien_status != titre.status or any(ancien_data[k] != getattr(titre, k) for k in ancien_data):
            HistoriqueTitre.objects.create(
                titre=titre,
                action='modification',
                utilisateur=self.context['request'].user,
                ancien_status=ancien_status,
                nouveau_status=titre.status,
                donnees_modifiees=ancien_data,
                commentaire="Titre modifié"
            )
        
        return titre

class TitreCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de titres."""
    proprietaire_email = serializers.EmailField(required=True)
    
    class Meta:
        model = Titre
        fields = [
            'type', 'proprietaire_email', 'entreprise_nom', 'date_emission',
            'date_expiration', 'duree_ans', 'description', 'conditions_specifiques'
        ]
    
    def validate_proprietaire_email(self, value):
        """Validation de l'email du propriétaire."""
        try:
            user = User.objects.get(email=value)
            if not hasattr(user, 'profile') or user.profile.role != 'operateur':
                raise serializers.ValidationError("L'utilisateur doit être un opérateur.")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Aucun utilisateur trouvé avec cet email.")
    
    def validate(self, attrs):
        """Validation des données."""
        # Vérifier les dates
        if attrs['date_expiration'] <= attrs['date_emission']:
            raise serializers.ValidationError({
                "date_expiration": "La date d'expiration doit être postérieure à la date d'émission."
            })
        
        # Calculer la durée automatiquement si pas fournie
        if not attrs.get('duree_ans'):
            delta = attrs['date_expiration'] - attrs['date_emission']
            attrs['duree_ans'] = max(1, delta.days // 365)
        
        return attrs
    
    def create(self, validated_data):
        """Création du titre avec assignation du propriétaire."""
        proprietaire_email = validated_data.pop('proprietaire_email')
        proprietaire = User.objects.get(email=proprietaire_email)
        
        titre = Titre.objects.create(
            proprietaire=proprietaire,
            **validated_data
        )
        
        # Créer l'historique
        HistoriqueTitre.objects.create(
            titre=titre,
            action='creation',
            utilisateur=self.context['request'].user,
            nouveau_status=titre.status,
            commentaire=f"Titre créé pour {proprietaire.email}"
        )
        
        return titre

class TitreRenewalSerializer(serializers.Serializer):
    """Serializer pour le renouvellement de titres."""
    duree_ans = serializers.IntegerField(min_value=1, max_value=10, required=False)
    commentaire = serializers.CharField(max_length=500, required=False)
    
    def validate_duree_ans(self, value):
        """Validation de la durée de renouvellement."""
        if value and (value < 1 or value > 10):
            raise serializers.ValidationError("La durée doit être entre 1 et 10 ans.")
        return value

class TitreStatisticsSerializer(serializers.Serializer):
    """Serializer pour les statistiques des titres."""
    total_titres = serializers.IntegerField()
    titres_actifs = serializers.IntegerField()
    titres_expires = serializers.IntegerField()
    titres_expirant_bientot = serializers.IntegerField()
    redevances_en_attente = serializers.DecimalField(max_digits=15, decimal_places=2)
    redevances_en_retard = serializers.DecimalField(max_digits=15, decimal_places=2)
    par_type = serializers.DictField()
    par_status = serializers.DictField()
    