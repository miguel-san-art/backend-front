# titres/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import date, timedelta
from .models import Titre, HistoriqueTitre, RedevanceTitre
from .serializers import (
    TitreSerializer, TitreCreateSerializer, TitreRenewalSerializer,
    HistoriqueTitreSerializer, RedevanceTitreSerializer, TitreStatisticsSerializer
)
from users.permissions import IsAdmin, IsPersonnel, IsOperateur, IsOwnerOrAdmin

class TitreViewSet(viewsets.ModelViewSet):
    """API endpoint pour la gestion des titres."""
    queryset = Titre.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TitreCreateSerializer
        elif self.action == 'renew':
            return TitreRenewalSerializer
        return TitreSerializer
    
    def get_permissions(self):
        """Définir les permissions selon l'action."""
        if self.action in ['list', 'retrieve']:
            # Personnel et Admin peuvent voir tous les titres
            # Opérateurs ne voient que leurs titres
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Seuls Admin et Personnel peuvent créer/modifier/supprimer
            permission_classes = [IsAdmin | IsPersonnel]
        elif self.action in ['renew', 'suspend', 'reactivate']:
            # Actions spéciales réservées au Personnel et Admin
            permission_classes = [IsAdmin | IsPersonnel]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filtrer les titres selon le rôle de l'utilisateur."""
        user = self.request.user
        queryset = Titre.objects.select_related('proprietaire__profile').prefetch_related(
            'redevances', 'historique__utilisateur__profile'
        )
        
        # Si l'utilisateur est un opérateur, ne voir que ses propres titres
        if hasattr(user, 'profile') and user.profile.role == 'operateur':
            queryset = queryset.filter(proprietaire=user)
        
        # Filtres de recherche
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(numero_titre__icontains=search) |
                Q(entreprise_nom__icontains=search) |
                Q(proprietaire__profile__nom__icontains=search) |
                Q(proprietaire__profile__prenom__icontains=search)
            )
        
        # Filtre par type
        type_titre = self.request.query_params.get('type', None)
        if type_titre:
            queryset = queryset.filter(type=type_titre)
        
        # Filtre par statut
        status_titre = self.request.query_params.get('status', None)
        if status_titre:
            queryset = queryset.filter(status=status_titre)
        
        # Filtre par propriétaire (pour Admin/Personnel)
        proprietaire_id = self.request.query_params.get('proprietaire', None)
        if proprietaire_id and user.profile.role in ['admin', 'personnel']:
            queryset = queryset.filter(proprietaire__id=proprietaire_id)
        
        # Filtre par expiration proche
        expiring_soon = self.request.query_params.get('expiring_soon', None)
        if expiring_soon == 'true':
            date_limite = date.today() + timedelta(days=30)
            queryset = queryset.filter(
                date_expiration__lte=date_limite,
                date_expiration__gte=date.today(),
                status='approuve'
            )
        
        # Filtre par titres expirés
        expired = self.request.query_params.get('expired', None)
        if expired == 'true':
            queryset = queryset.filter(date_expiration__lt=date.today())
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def renew(self, request, pk=None):
        """Renouveler un titre."""
        titre = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            duree_ans = serializer.validated_data.get('duree_ans', titre.duree_ans)
            commentaire = serializer.validated_data.get('commentaire', '')
            
            # Effectuer le renouvellement
            ancien_status = titre.status
            titre.renew(duree_ans)
            
            # Créer l'historique
            HistoriqueTitre.objects.create(
                titre=titre,
                action='renouvellement',
                utilisateur=request.user,
                ancien_status=ancien_status,
                nouveau_status=titre.status,
                commentaire=commentaire or f"Titre renouvelé pour {duree_ans} ans"
            )
            
            return Response({
                'message': f'Titre {titre.numero_titre} renouvelé avec succès',
                'nouvelle_date_expiration': titre.date_expiration,
                'nouvelle_redevance': titre.redevance_annuelle
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspendre un titre."""
        titre = self.get_object()
        commentaire = request.data.get('commentaire', '')
        
        if titre.status in ['approuve', 'en_cours']:
            ancien_status = titre.status
            titre.status = 'rejete'  # Utiliser 'rejete' comme statut de suspension
            titre.save()
            
            # Créer l'historique
            HistoriqueTitre.objects.create(
                titre=titre,
                action='suspension',
                utilisateur=request.user,
                ancien_status=ancien_status,
                nouveau_status=titre.status,
                commentaire=commentaire or f"Titre {titre.numero_titre} suspendu"
            )
            
            return Response({'message': f'Titre {titre.numero_titre} suspendu avec succès'})
        
        return Response(
            {'error': 'Ce titre ne peut pas être suspendu dans son état actuel'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        """Réactiver un titre suspendu."""
        titre = self.get_object()
        commentaire = request.data.get('commentaire', '')
        
        if titre.status == 'rejete':
            ancien_status = titre.status
            titre.status = 'approuve'
            titre.save()
            
            # Créer l'historique
            HistoriqueTitre.objects.create(
                titre=titre,
                action='reactivation',
                utilisateur=request.user,
                ancien_status=ancien_status,
                nouveau_status=titre.status,
                commentaire=commentaire or f"Titre {titre.numero_titre} réactivé"
            )
            
            return Response({'message': f'Titre {titre.numero_titre} réactivé avec succès'})
        
        return Response(
            {'error': 'Ce titre ne peut pas être réactivé dans son état actuel'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Obtenir les statistiques des titres."""
        user = request.user
        queryset = self.get_queryset()
        
        # Calculs de base
        total_titres = queryset.count()
        titres_actifs = queryset.filter(status='approuve').count()
        titres_expires = queryset.filter(date_expiration__lt=date.today()).count()
        
        # Titres expirant dans les 30 jours
        date_limite = date.today() + timedelta(days=30)
        titres_expirant_bientot = queryset.filter(
            date_expiration__lte=date_limite,
            date_expiration__gte=date.today(),
            status='approuve'
        ).count()
        
        # Statistiques des redevances
        redevances_stats = RedevanceTitre.objects.filter(
            titre__in=queryset
        ).aggregate(
            en_attente=Sum('montant', filter=Q(status_paiement='en_attente')) or 0,
            en_retard=Sum('montant', filter=Q(status_paiement='en_retard')) or 0
        )
        
        # Répartition par type
        par_type = dict(queryset.values('type').annotate(count=Count('id')).values_list('type', 'count'))
        
        # Répartition par statut
        par_status = dict(queryset.values('status').annotate(count=Count('id')).values_list('status', 'count'))
        
        stats_data = {
            'total_titres': total_titres,
            'titres_actifs': titres_actifs,
            'titres_expires': titres_expires,
            'titres_expirant_bientot': titres_expirant_bientot,
            'redevances_en_attente': redevances_stats['en_attente'] or 0,
            'redevances_en_retard': redevances_stats['en_retard'] or 0,
            'par_type': par_type,
            'par_status': par_status
        }
        
        serializer = TitreStatisticsSerializer(stats_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Obtenir les titres qui expirent bientôt."""
        days = int(request.query_params.get('days', 30))
        date_limite = date.today() + timedelta(days=days)
        
        queryset = self.get_queryset().filter(
            date_expiration__lte=date_limite,
            date_expiration__gte=date.today(),
            status='approuve'
        ).order_by('date_expiration')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class RedevanceTitreViewSet(viewsets.ModelViewSet):
    """API endpoint pour la gestion des redevances."""
    serializer_class = RedevanceTitreSerializer
    permission_classes = [IsAdmin | IsPersonnel]
    
    def get_queryset(self):
        """Filtrer les redevances selon les paramètres."""
        queryset = RedevanceTitre.objects.select_related('titre__proprietaire__profile')
        
        # Filtre par titre
        titre_id = self.request.query_params.get('titre', None)
        if titre_id:
            queryset = queryset.filter(titre__id=titre_id)
        
        # Filtre par année
        annee = self.request.query_params.get('annee', None)
        if annee:
            queryset = queryset.filter(annee=annee)
        
        # Filtre par statut de paiement
        status_paiement = self.request.query_params.get('status', None)
        if status_paiement:
            queryset = queryset.filter(status_paiement=status_paiement)
        
        # Filtre par redevances en retard
        overdue = self.request.query_params.get('overdue', None)
        if overdue == 'true':
            queryset = queryset.filter(
                date_echeance__lt=date.today(),
                status_paiement__in=['en_attente', 'en_retard']
            )
        
        return queryset.order_by('-annee', '-date_echeance')
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Marquer une redevance comme payée."""
        redevance = self.get_object()
        reference_paiement = request.data.get('reference_paiement', '')
        date_paiement = request.data.get('date_paiement', date.today())
        
        redevance.status_paiement = 'paye'
        redevance.date_paiement = date_paiement
        redevance.reference_paiement = reference_paiement
        redevance.save()
        
        # Créer l'historique pour le titre
        HistoriqueTitre.objects.create(
            titre=redevance.titre,
            action='modification',
            utilisateur=request.user,
            commentaire=f"Redevance {redevance.annee} marquée comme payée - Ref: {reference_paiement}"
        )
        
        return Response({
            'message': f'Redevance {redevance.annee} marquée comme payée',
            'reference': reference_paiement
        })
    
    @action(detail=False, methods=['post'])
    def generate_annual_fees(self, request):
        """Générer les redevances annuelles pour tous les titres actifs."""
        annee = int(request.data.get('annee', date.today().year))
        
        titres_actifs = Titre.objects.filter(status='approuve')
        redevances_creees = 0
        
        for titre in titres_actifs:
            # Vérifier si la redevance n'existe pas déjà
            if not RedevanceTitre.objects.filter(titre=titre, annee=annee).exists():
                RedevanceTitre.objects.create(
                    titre=titre,
                    annee=annee,
                    montant=titre.redevance_annuelle,
                    date_echeance=date(annee, 12, 31)  # 31 décembre de l'année
                )
                redevances_creees += 1
        
        return Response({
            'message': f'{redevances_creees} redevances générées pour l\'année {annee}',
            'annee': annee,
            'total_genere': redevances_creees
        })


class HistoriqueTitreViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint pour consulter l'historique des titres."""
    serializer_class = HistoriqueTitreSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filtrer l'historique selon les paramètres et les permissions."""
        user = self.request.user
        queryset = HistoriqueTitre.objects.select_related(
            'titre__proprietaire__profile', 'utilisateur__profile'
        )
        
        # Si l'utilisateur est un opérateur, ne voir que l'historique de ses titres
        if hasattr(user, 'profile') and user.profile.role == 'operateur':
            queryset = queryset.filter(titre__proprietaire=user)
        
        # Filtre par titre
        titre_id = self.request.query_params.get('titre', None)
        if titre_id:
            queryset = queryset.filter(titre__id=titre_id)
        
        # Filtre par action
        action = self.request.query_params.get('action', None)
        if action:
            queryset = queryset.filter(action=action)
        
        # Filtre par utilisateur (pour Admin/Personnel)
        utilisateur_id = self.request.query_params.get('utilisateur', None)
        if utilisateur_id and user.profile.role in ['admin', 'personnel']:
            queryset = queryset.filter(utilisateur__id=utilisateur_id)
        
        return queryset.order_by('-date_action')
    