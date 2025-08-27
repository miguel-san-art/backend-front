# requests_management/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count, Avg
from django.db.models.functions import TruncMonth
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from datetime import date, timedelta
import django_filters

from .models import Demande, Document, HistoriqueDemande, CommentaireDemande
from .serializers import (
    DemandeSerializer, DemandeCreateSerializer, DemandeUpdateStatusSerializer,
    DocumentSerializer, CommentaireDemandeSerializer, DemandeStatisticsSerializer
)
from users.permissions import IsAdmin, IsPersonnel, IsOperateur

User = get_user_model()

class DemandeFilter(django_filters.FilterSet):
    """Filtres pour les demandes."""
    
    type_titre = django_filters.ChoiceFilter(choices=Demande.TYPE_TITRE_CHOICES)
    status = django_filters.ChoiceFilter(choices=Demande.STATUS_CHOICES)
    date_soumission_debut = django_filters.DateFilter(field_name='date_soumission', lookup_expr='gte')
    date_soumission_fin = django_filters.DateFilter(field_name='date_soumission', lookup_expr='lte')
    demandeur = django_filters.UUIDFilter(field_name='demandeur__id')
    assignee = django_filters.UUIDFilter(field_name='assignee__id')
    en_retard = django_filters.BooleanFilter(method='filter_en_retard')
    recherche = django_filters.CharFilter(method='filter_recherche')
    
    class Meta:
        model = Demande
        fields = ['type_titre', 'status', 'demandeur', 'assignee']
    
    def filter_en_retard(self, queryset, name, value):
        """Filtre les demandes en retard."""
        if value:
            date_limite = date.today() - timedelta(days=30)
            return queryset.filter(
                date_soumission__lte=date_limite,
                status__in=['soumise', 'en_examen']
            )
        return queryset
    
    def filter_recherche(self, queryset, name, value):
        """Recherche dans plusieurs champs."""
        if value:
            return queryset.filter(
                Q(numero_dossier__icontains=value) |
                Q(entreprise__icontains=value) |
                Q(email_contact__icontains=value) |
                Q(description__icontains=value)
            )
        return queryset

class DemandePagination(PageNumberPagination):
    """Pagination personnalisée pour les demandes."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class DemandeViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des demandes."""
    
    queryset = Demande.objects.all().select_related('demandeur', 'assignee').prefetch_related(
        'documents', 'commentaires', 'historique'
    )
    pagination_class = DemandePagination
    filterset_class = DemandeFilter
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Choix du serializer selon l'action."""
        if self.action == 'create':
            return DemandeCreateSerializer
        elif self.action == 'update_status':
            return DemandeUpdateStatusSerializer
        return DemandeSerializer
    
    def get_permissions(self):
        """Permissions selon l'action."""
        if self.action in ['create', 'my_requests']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy', 'assign', 'update_status']:
            permission_classes = [IsAdmin | IsPersonnel]
        elif self.action in ['statistics', 'dashboard']:
            permission_classes = [IsAdmin | IsPersonnel]
        else:
            permission_classes = [IsAdmin]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filtrage selon le rôle de l'utilisateur."""
        user = self.request.user
        queryset = self.queryset
        
        # Les opérateurs ne voient que leurs demandes
        if hasattr(user, 'profile') and user.profile.role == 'operateur':
            queryset = queryset.filter(demandeur=user)
        
        # Le personnel voit toutes les demandes ou celles qui lui sont assignées
        elif hasattr(user, 'profile') and user.profile.role == 'personnel':
            if self.action == 'my_assigned':
                queryset = queryset.filter(assignee=user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Création d'une demande."""
        serializer.save(demandeur=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """Récupère les demandes de l'utilisateur connecté."""
        demandes = self.get_queryset().filter(demandeur=request.user)
        page = self.paginate_queryset(demandes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(demandes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_assigned(self, request):
        """Récupère les demandes assignées à l'utilisateur connecté."""
        demandes = self.get_queryset().filter(assignee=request.user)
        page = self.paginate_queryset(demandes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(demandes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assigner une demande à un utilisateur."""
        demande = self.get_object()
        assignee_id = request.data.get('assignee_id')
        
        if assignee_id:
            try:
                assignee = User.objects.get(id=assignee_id)
                if not hasattr(assignee, 'profile') or assignee.profile.role not in ['admin', 'personnel']:
                    return Response(
                        {'error': 'L\'utilisateur assigné doit être un administrateur ou du personnel.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except User.DoesNotExist:
                return Response(
                    {'error': 'Utilisateur non trouvé.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            assignee = None
        
        ancien_assignee = demande.assignee
        demande.assignee = assignee
        demande.save()
        
        # Créer l'historique d'assignation
        assignee_nom = "Non assigné"
        if assignee and hasattr(assignee, 'profile'):
            assignee_nom = f"{assignee.profile.nom} {assignee.profile.prenom}"
        elif assignee:
            assignee_nom = assignee.email
        
        HistoriqueDemande.objects.create(
            demande=demande,
            action='assignation',
            utilisateur=request.user,
            commentaire=f"Demande assignée à: {assignee_nom}"
        )
        
        serializer = self.get_serializer(demande)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Mettre à jour le statut d'une demande."""
        demande = self.get_object()
        serializer = DemandeUpdateStatusSerializer(data=request.data)
        
        if serializer.is_valid():
            ancien_status = demande.status
            nouveau_status = serializer.validated_data['status']
            commentaires = serializer.validated_data.get('commentaires_admin', '')
            assignee_id = serializer.validated_data.get('assignee_id')
            
            # Mise à jour de la demande
            demande.status = nouveau_status
            if commentaires:
                demande.commentaires_admin = commentaires
            
            if assignee_id:
                assignee = User.objects.get(id=assignee_id)
                demande.assignee = assignee
            
            # Définir la date de traitement si statut final
            if nouveau_status in ['approuvee', 'rejetee']:
                demande.date_traitement = date.today()
            
            demande.save()
            
            # Créer l'historique
            action = 'modification'
            if nouveau_status == 'en_examen':
                action = 'mise_en_examen'
            elif nouveau_status == 'approuvee':
                action = 'approbation'
            elif nouveau_status == 'rejetee':
                action = 'rejet'
            
            HistoriqueDemande.objects.create(
                demande=demande,
                action=action,
                utilisateur=request.user,
                ancien_status=ancien_status,
                nouveau_status=nouveau_status,
                commentaire=commentaires or f"Changement de statut: {ancien_status} → {nouveau_status}"
            )
            
            serializer = DemandeSerializer(demande, context={'request': request})
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Statistiques des demandes."""
        queryset = self.get_queryset()
        
        # Statistiques générales
        total_demandes = queryset.count()
        demandes_soumises = queryset.filter(status='soumise').count()
        demandes_en_examen = queryset.filter(status='en_examen').count()
        demandes_approuvees = queryset.filter(status='approuvee').count()
        demandes_rejetees = queryset.filter(status='rejetee').count()
        
        # Demandes en retard
        date_limite = date.today() - timedelta(days=30)
        demandes_en_retard = queryset.filter(
            date_soumission__lte=date_limite,
            status__in=['soumise', 'en_examen']
        ).count()
        
        # Délai moyen de traitement
        demandes_traitees = queryset.filter(date_traitement__isnull=False)
        delai_moyen = 0
        if demandes_traitees.exists():
            delais = []
            for demande in demandes_traitees:
                delai = (demande.date_traitement - demande.date_soumission).days
                delais.append(delai)
            delai_moyen = sum(delais) / len(delais) if delais else 0
        
        # Statistiques par type de titre
        par_type_titre = {}
        for choice in Demande.TYPE_TITRE_CHOICES:
            type_code, type_nom = choice
            count = queryset.filter(type_titre=type_code).count()
            par_type_titre[type_nom] = count
        
        # Statistiques par mois (6 derniers mois)
        six_mois_ago = date.today() - timedelta(days=180)
        par_mois = queryset.filter(
            date_soumission__gte=six_mois_ago
        ).annotate(
            mois=TruncMonth('date_soumission')
        ).values('mois').annotate(
            count=Count('id')
        ).order_by('mois')
        
        par_mois_dict = {}
        for item in par_mois:
            mois_str = item['mois'].strftime('%Y-%m')
            par_mois_dict[mois_str] = item['count']
        
        stats_data = {
            'total_demandes': total_demandes,
            'demandes_soumises': demandes_soumises,
            'demandes_en_examen': demandes_en_examen,
            'demandes_approuvees': demandes_approuvees,
            'demandes_rejetees': demandes_rejetees,
            'demandes_en_retard': demandes_en_retard,
            'delai_moyen_traitement': delai_moyen,
            'par_type_titre': par_type_titre,
            'par_mois': par_mois_dict
        }
        
        serializer = DemandeStatisticsSerializer(stats_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Tableau de bord avec informations importantes."""
        user = request.user
        queryset = self.get_queryset()
        
        # Données selon le rôle
        dashboard_data = {}
        
        if hasattr(user, 'profile') and user.profile.role == 'operateur':
            # Pour les opérateurs : leurs demandes
            mes_demandes = queryset.filter(demandeur=user)
            dashboard_data = {
                'mes_demandes_total': mes_demandes.count(),
                'mes_demandes_soumises': mes_demandes.filter(status='soumise').count(),
                'mes_demandes_en_examen': mes_demandes.filter(status='en_examen').count(),
                'mes_demandes_approuvees': mes_demandes.filter(status='approuvee').count(),
                'mes_demandes_rejetees': mes_demandes.filter(status='rejetee').count(),
                'dernières_demandes': DemandeSerializer(
                    mes_demandes.order_by('-created_at')[:5],
                    many=True,
                    context={'request': request}
                ).data
            }
        
        elif hasattr(user, 'profile') and user.profile.role in ['admin', 'personnel']:
            # Pour admin/personnel : vue globale
            mes_assignations = queryset.filter(assignee=user)
            demandes_urgentes = queryset.filter(
                date_soumission__lte=date.today() - timedelta(days=25),
                status__in=['soumise', 'en_examen']
            )
            
            dashboard_data = {
                'total_demandes': queryset.count(),
                'demandes_en_attente': queryset.filter(status='soumise').count(),
                'demandes_en_examen': queryset.filter(status='en_examen').count(),
                'mes_assignations': mes_assignations.count(),
                'demandes_urgentes': demandes_urgentes.count(),
                'demandes_recentes': DemandeSerializer(
                    queryset.order_by('-created_at')[:5],
                    many=True,
                    context={'request': request}
                ).data,
                'demandes_urgentes_list': DemandeSerializer(
                    demandes_urgentes.order_by('date_soumission')[:5],
                    many=True,
                    context={'request': request}
                ).data
            }
        
        return Response(dashboard_data)

class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des documents."""
    
    queryset = Document.objects.all().select_related('demande', 'titre', 'uploade_par')
    serializer_class = DocumentSerializer
    
    def get_permissions(self):
        """Permissions selon l'action."""
        if self.action in ['create', 'upload']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['list', 'retrieve', 'download']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [IsAdmin | IsPersonnel]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filtrage selon le rôle de l'utilisateur."""
        user = self.request.user
        queryset = self.queryset
        
        # Les opérateurs ne voient que les documents de leurs demandes
        if hasattr(user, 'profile') and user.profile.role == 'operateur':
            queryset = queryset.filter(demande__demandeur=user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Création d'un document."""
        serializer.save(uploade_par=self.request.user)
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Upload d'un document pour une demande."""
        demande_id = request.data.get('demande_id')
        
        if not demande_id:
            return Response(
                {'error': 'demande_id est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            demande = Demande.objects.get(id=demande_id)
            
            # Vérifier les permissions
            if hasattr(request.user, 'profile') and request.user.profile.role == 'operateur':
                if demande.demandeur != request.user:
                    return Response(
                        {'error': 'Vous ne pouvez uploader des documents que pour vos propres demandes.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
        except Demande.DoesNotExist:
            return Response(
                {'error': 'Demande non trouvée.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            document = serializer.save(
                demande=demande,
                uploade_par=request.user
            )
            
            # Créer l'historique
            HistoriqueDemande.objects.create(
                demande=demande,
                action='document_ajoute',
                utilisateur=request.user,
                commentaire=f"Document ajouté: {document.nom_fichier}"
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Téléchargement d'un document."""
        document = self.get_object()
        
        # Vérifier les permissions de téléchargement
        user = request.user
        if hasattr(user, 'profile') and user.profile.role == 'operateur':
            if document.demande and document.demande.demandeur != user:
                return Response(
                    {'error': 'Accès non autorisé à ce document.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        if document.fichier:
            from django.http import FileResponse
            return FileResponse(
                document.fichier.open('rb'),
                as_attachment=True,
                filename=document.nom_fichier
            )
        
        return Response(
            {'error': 'Fichier non trouvé.'},
            status=status.HTTP_404_NOT_FOUND
        )

class CommentaireDemandeViewSet(viewsets.ModelViewSet):
    """ViewSet pour les commentaires des demandes."""
    
    queryset = CommentaireDemande.objects.all().select_related('demande', 'auteur')
    serializer_class = CommentaireDemandeSerializer
    
    def get_permissions(self):
        """Permissions selon l'action."""
        permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filtrage selon le rôle de l'utilisateur."""
        user = self.request.user
        queryset = self.queryset
        
        # Les opérateurs ne voient que les commentaires publics de leurs demandes
        if hasattr(user, 'profile') and user.profile.role == 'operateur':
            queryset = queryset.filter(
                demande__demandeur=user,
                type_commentaire='public'
            )
        
        return queryset
    
    def perform_create(self, serializer):
        """Création d'un commentaire."""
        demande_id = self.request.data.get('demande_id')
        
        if not demande_id:
            raise serializers.ValidationError({'demande_id': 'Ce champ est requis.'})
        
        try:
            demande = Demande.objects.get(id=demande_id)
        except Demande.DoesNotExist:
            raise serializers.ValidationError({'demande_id': 'Demande non trouvée.'})
        
        # Vérifier les permissions
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role == 'operateur':
            if demande.demandeur != user:
                raise serializers.ValidationError({'error': 'Accès non autorisé.'})
            # Les opérateurs ne peuvent créer que des commentaires publics
            type_commentaire = 'public'
        else:
            type_commentaire = self.request.data.get('type_commentaire', 'public')
        
        commentaire = serializer.save(
            demande=demande,
            auteur=user,
            type_commentaire=type_commentaire
        )
        
        # Créer l'historique
        HistoriqueDemande.objects.create(
            demande=demande,
            action='commentaire',
            utilisateur=user,
            commentaire=f"Commentaire ajouté par {user.email}"
        )
        