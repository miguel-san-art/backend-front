# demandes/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from datetime import date
from .models import Demande, Document, HistoriqueDemande, CommentaireDemande

User = get_user_model()

class DemandeurSerializer(serializers.ModelSerializer):
    """Serializer pour les informations du demandeur."""
    nom_complet = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'nom_complet']
    
    def get_nom_complet(self, obj):
        if hasattr(obj, 'profile'):
            return f"{obj.profile.nom} {obj.profile.prenom}"
        return obj.email

class DocumentSerializer(serializers.ModelSerializer):
    """Serializer pour les documents."""
    uploade_par_nom = serializers.SerializerMethodField()
    taille_fichier_readable = serializers.ReadOnlyField()
    url_telechargement = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'nom_fichier', 'type_document', 'fichier', 'taille_fichier',
            'taille_fichier_readable', 'hash_fichier', 'uploade_par', 'uploade_par_nom',
            'description', 'version', 'est_actif', 'url_telechargement',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['taille_fichier', 'hash_fichier', 'created_at', 'updated_at']
    
    def get_uploade_par_nom(self, obj):
        if obj.uploade_par and hasattr(obj.uploade_par, 'profile'):
            return f"{obj.uploade_par.profile.nom} {obj.uploade_par.profile.prenom}"
        elif obj.uploade_par:
            return obj.uploade_par.email
        return "Inconnu"
    
    def get_url_telechargement(self, obj):
        if obj.fichier:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.fichier.url)
            return obj.fichier.url
        return None
    
    def validate_fichier(self, value):
        """Validation du fichier uploadé."""
        # Vérifier la taille (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError("La taille du fichier ne peut pas dépasser 10MB.")
        
        # Vérifier l'extension
        allowed_extensions = Document.ALLOWED_EXTENSIONS
        extension = value.name.split('.')[-1].lower()
        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"Extension de fichier non autorisée. Extensions autorisées: {', '.join(allowed_extensions)}"
            )
        
        return value

class CommentaireDemandeSerializer(serializers.ModelSerializer):
    """Serializer pour les commentaires de demandes."""
    auteur_nom = serializers.SerializerMethodField()
    
    class Meta:
        model = CommentaireDemande
        fields = [
            'id', 'auteur', 'auteur_nom', 'type_commentaire', 'contenu',
            'est_resolu', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_auteur_nom(self, obj):
        if obj.auteur and hasattr(obj.auteur, 'profile'):
            return f"{obj.auteur.profile.nom} {obj.auteur.profile.prenom}"
        elif obj.auteur:
            return obj.auteur.email
        return "Inconnu"

class HistoriqueDemandeSerializer(serializers.ModelSerializer):
    """Serializer pour l'historique des demandes."""
    utilisateur_nom = serializers.SerializerMethodField()
    
    class Meta:
        model = HistoriqueDemande
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

class DemandeSerializer(serializers.ModelSerializer):
    """Serializer principal pour les demandes."""
    demandeur_info = DemandeurSerializer(source='demandeur', read_only=True)
    assignee_info = DemandeurSerializer(source='assignee', read_only=True)
    type_titre_display = serializers.CharField(source='get_type_titre_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    days_since_submission = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    
    # Relations
    documents = DocumentSerializer(many=True, read_only=True)
    commentaires = CommentaireDemandeSerializer(many=True, read_only=True)
    historique = HistoriqueDemandeSerializer(many=True, read_only=True)
    
    class Meta:
        model = Demande
        fields = [
            'id', 'demandeur', 'demandeur_info', 'entreprise', 'email_contact',
            'telephone', 'adresse', 'type_titre', 'type_titre_display', 'description',
            'motivations', 'status', 'status_display', 'numero_dossier',
            'date_soumission', 'date_traitement', 'commentaires_admin', 'assignee',
            'assignee_info', 'documents_urls', 'days_since_submission', 'is_overdue',
            'documents', 'commentaires', 'historique', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'numero_dossier', 'date_soumission', 'created_at', 'updated_at',
            'days_since_submission', 'is_overdue'
        ]
    
    def validate_email_contact(self, value):
        """Validation de l'email de contact."""
        if not value:
            raise serializers.ValidationError("L'email de contact est requis.")
        return value
    
    def validate_entreprise(self, value):
        """Validation du nom de l'entreprise."""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Le nom de l'entreprise doit contenir au moins 3 caractères.")
        return value.strip()
    
    def create(self, validated_data):
        """Création d'une nouvelle demande avec historique."""
        demande = super().create(validated_data)
        
        # Créer l'entrée d'historique pour la soumission
        HistoriqueDemande.objects.create(
            demande=demande,
            action='soumission',
            utilisateur=self.context['request'].user,
            nouveau_status=demande.status,
            commentaire=f"Demande soumise: {demande.numero_dossier}"
        )
        
        return demande
    
    def update(self, instance, validated_data):
        """Mise à jour d'une demande avec historique."""
        ancien_status = instance.status
        ancien_assignee = instance.assignee
        
        demande = super().update(instance, validated_data)
        
        # Créer l'historique selon les changements
        user = self.context['request'].user
        
        # Changement de statut
        if ancien_status != demande.status:
            action = 'modification'
            if demande.status == 'en_examen':
                action = 'mise_en_examen'
            elif demande.status == 'approuvee':
                action = 'approbation'
                demande.date_traitement = date.today()
                demande.save()
            elif demande.status == 'rejetee':
                action = 'rejet'
                demande.date_traitement = date.today()
                demande.save()
            
            HistoriqueDemande.objects.create(
                demande=demande,
                action=action,
                utilisateur=user,
                ancien_status=ancien_status,
                nouveau_status=demande.status,
                commentaire=f"Changement de statut: {ancien_status} → {demande.status}"
            )
        
        # Changement d'assignation
        if ancien_assignee != demande.assignee:
            assignee_nom = "Non assigné"
            if demande.assignee and hasattr(demande.assignee, 'profile'):
                assignee_nom = f"{demande.assignee.profile.nom} {demande.assignee.profile.prenom}"
            elif demande.assignee:
                assignee_nom = demande.assignee.email
            
            HistoriqueDemande.objects.create(
                demande=demande,
                action='assignation',
                utilisateur=user,
                commentaire=f"Demande assignée à: {assignee_nom}"
            )
        
        return demande

class DemandeCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de demandes."""
    
    class Meta:
        model = Demande
        fields = [
            'entreprise', 'email_contact', 'telephone', 'adresse',
            'type_titre', 'description', 'motivations'
        ]
    
    def validate_entreprise(self, value):
        """Validation du nom de l'entreprise."""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Le nom de l'entreprise doit contenir au moins 3 caractères.")
        return value.strip()
    
    def validate_email_contact(self, value):
        """Validation de l'email de contact."""
        if not value:
            raise serializers.ValidationError("L'email de contact est requis.")
        return value
    
    def create(self, validated_data):
        """Création d'une demande avec le demandeur actuel."""
        demande = Demande.objects.create(
            demandeur=self.context['request'].user,
            **validated_data
        )
        
        # Créer l'historique de soumission
        HistoriqueDemande.objects.create(
            demande=demande,
            action='soumission',
            utilisateur=self.context['request'].user,
            nouveau_status=demande.status,
            commentaire=f"Nouvelle demande soumise: {demande.numero_dossier}"
        )
        
        return demande

class DemandeUpdateStatusSerializer(serializers.Serializer):
    """Serializer pour la mise à jour du statut d'une demande."""
    status = serializers.ChoiceField(choices=Demande.STATUS_CHOICES)
    commentaires_admin = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    assignee_id = serializers.UUIDField(required=False, allow_null=True)
    
    def validate_assignee_id(self, value):
        """Validation de l'assignation."""
        if value:
            try:
                user = User.objects.get(id=value)
                if not hasattr(user, 'profile') or user.profile.role not in ['admin', 'personnel']:
                    raise serializers.ValidationError("L'utilisateur assigné doit être un administrateur ou du personnel.")
                return value
            except User.DoesNotExist:
                raise serializers.ValidationError("Utilisateur non trouvé.")
        return value

class DemandeStatisticsSerializer(serializers.Serializer):
    """Serializer pour les statistiques des demandes."""
    total_demandes = serializers.IntegerField()
    demandes_soumises = serializers.IntegerField()
    demandes_en_examen = serializers.IntegerField()
    demandes_approuvees = serializers.IntegerField()
    demandes_rejetees = serializers.IntegerField()
    demandes_en_retard = serializers.IntegerField()
    delai_moyen_traitement = serializers.FloatField()
    par_type_titre = serializers.DictField()
    par_mois = serializers.DictField()
    