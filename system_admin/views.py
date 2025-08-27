# system_admin/views.py
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from django.http import HttpResponse, Http404
import json
import os

from .models import SystemConfiguration, AuditLog, SystemBackup, SystemMetrics, SystemMaintenance
from .serializers import (
    SystemConfigurationSerializer, AuditLogSerializer, SystemBackupSerializer,
    SystemMetricsSerializer, SystemMaintenanceSerializer
)
from .services import SystemConfigService, AuditService, BackupService, MetricsService, MaintenanceService


def admin_required(view_func):
    """Décorateur pour vérifier les permissions admin"""
    def wrapper(request, *args, **kwargs):
        if not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
            return Response(
                {'error': 'Admin access required'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper


class SystemConfigurationListView(generics.ListCreateAPIView):
    """Liste et création des configurations système"""
    serializer_class = SystemConfigurationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            queryset = SystemConfiguration.objects.all()
            
            category = self.request.query_params.get('category')
            if category:
                queryset = queryset.filter(category=category)
                
            return queryset.order_by('category', 'key')
        else:
            return SystemConfiguration.objects.none()
    
    def perform_create(self, serializer):
        if not (hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin'):
            raise PermissionError("Admin access required")
        
        serializer.save(updated_by=self.request.user)


class SystemConfigurationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Détail, modification et suppression des configurations"""
    serializer_class = SystemConfigurationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            return SystemConfiguration.objects.all()
        else:
            return SystemConfiguration.objects.none()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_config_categories(request):
    """Récupérer toutes les catégories de configuration"""
    if not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        return Response(
            {'error': 'Admin access required'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    categories = SystemConfiguration.objects.values_list('category', flat=True).distinct()
    return Response(list(categories))


class AuditLogListView(generics.ListAPIView):
    """Liste des logs d'audit"""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if not (hasattr(self.request.user, 'profile') and self.request.user.profile.role in ['admin', 'personnel']):
            return AuditLog.objects.none()
        
        queryset = AuditLog.objects.all()
        
        # Filtres
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)
        
        resource_type = self.request.query_params.get('resource_type')
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        
        # Période
        days = self.request.query_params.get('days', 30)
        try:
            days = int(days)
            start_date = timezone.now() - timezone.timedelta(days=days)
            queryset = queryset.filter(timestamp__gte=start_date)
        except ValueError:
            pass
        
        return queryset.order_by('-timestamp')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_statistics(request):
    """Statistiques des logs d'audit"""
    if not (hasattr(request.user, 'profile') and request.user.profile.role in ['admin', 'personnel']):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    days = int(request.query_params.get('days', 7))
    start_date = timezone.now() - timezone.timedelta(days=days)
    
    # Statistiques par action
    actions_stats = AuditLog.objects.filter(
        timestamp__gte=start_date
    ).values('action').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Statistiques par niveau
    levels_stats = AuditLog.objects.filter(
        timestamp__gte=start_date
    ).values('level').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Utilisateurs les plus actifs
    users_stats = AuditLog.objects.filter(
        timestamp__gte=start_date,
        user__isnull=False
    ).values('user__email', 'user__first_name', 'user__last_name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    return Response({
        'period_days': days,
        'actions': list(actions_stats),
        'levels': list(levels_stats),
        'top_users': list(users_stats)
    })


class SystemBackupListView(generics.ListCreateAPIView):
    """Liste et création des sauvegardes"""
    serializer_class = SystemBackupSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            return SystemBackup.objects.all().order_by('-created_at')
        else:
            return SystemBackup.objects.none()
    
    def perform_create(self, serializer):
        if not (hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin'):
            raise PermissionError("Admin access required")
        
        name = serializer.validated_data['name']
        backup_type = serializer.validated_data['backup_type']
        description = serializer.validated_data.get('description', '')
        
        backup = BackupService.create_backup(
            name=name,
            backup_type=backup_type,
            description=description,
            user=self.request.user
        )
        
        if not backup:
            raise Exception("Failed to create backup")
        
        return backup


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_backup(request, pk):
    """Télécharger un fichier de sauvegarde"""
    if not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        return Response(
            {'error': 'Admin access required'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    backup = get_object_or_404(SystemBackup, pk=pk)
    
    if backup.status != 'completed' or not backup.file_path:
        return Response(
            {'error': 'Backup file not available'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not os.path.exists(backup.file_path):
        return Response(
            {'error': 'Backup file not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Log de l'audit
    AuditService.log_action(
        user=request.user,
        action='export',
        resource_type='SystemBackup',
        resource_id=str(backup.id),
        description=f"Téléchargement sauvegarde: {backup.name}"
    )
    
    # Retourner le fichier
    with open(backup.file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/sql')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(backup.file_path)}"'
        return response


class SystemMetricsListView(generics.ListAPIView):
    """Liste des métriques système"""
    serializer_class = SystemMetricsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if not (hasattr(self.request.user, 'profile') and self.request.user.profile.role in ['admin', 'personnel']):
            return SystemMetrics.objects.none()
        
        queryset = SystemMetrics.objects.all()
        
        metric_type = self.request.query_params.get('metric_type')
        if metric_type:
            queryset = queryset.filter(metric_type=metric_type)
        
        # Période
        days = self.request.query_params.get('days', 7)
        try:
            days = int(days)
            start_date = timezone.now() - timezone.timedelta(days=days)
            queryset = queryset.filter(timestamp__gte=start_date)
        except ValueError:
            pass
        
        return queryset.order_by('-timestamp')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def collect_metrics(request):
    """Forcer la collecte des métriques"""
    if not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        return Response(
            {'error': 'Admin access required'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    success = MetricsService.collect_metrics()
    
    AuditService.log_action(
        user=request.user,
        action='config',
        resource_type='SystemMetrics',
        description="Collecte manuelle des métriques système"
    )
    
    return Response({
        'status': 'success' if success else 'error',
        'message': 'Metrics collected' if success else 'Failed to collect metrics'
    })


class SystemMaintenanceListView(generics.ListCreateAPIView):
    """Liste et création des maintenances"""
    serializer_class = SystemMaintenanceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            queryset = SystemMaintenance.objects.all()
            
            # Filtres
            status_filter = self.request.query_params.get('status')
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            return queryset.order_by('scheduled_start')
        else:
            return SystemMaintenance.objects.none()


class SystemMaintenanceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Détail, modification et suppression des maintenances"""
    serializer_class = SystemMaintenanceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            return SystemMaintenance.objects.all()
        else:
            return SystemMaintenance.objects.none()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_maintenance(request, pk):
    """Démarrer une maintenance"""
    if not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        return Response(
            {'error': 'Admin access required'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    success = MaintenanceService.start_maintenance(pk, request.user)
    
    return Response({
        'status': 'success' if success else 'error',
        'message': 'Maintenance started' if success else 'Failed to start maintenance'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_maintenance(request, pk):
    """Terminer une maintenance"""
    if not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        return Response(
            {'error': 'Admin access required'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    success = MaintenanceService.complete_maintenance(pk, request.user)
    
    return Response({
        'status': 'success' if success else 'error',
        'message': 'Maintenance completed' if success else 'Failed to complete maintenance'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_dashboard(request):
    """Tableau de bord système avec statistiques"""
    if not (hasattr(request.user, 'profile') and request.user.profile.role in ['admin', 'personnel']):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Statistiques générales
    from django.contrib.auth import get_user_model
    from titres.models import Titre
    from demandes.models import Demande
    
    User = get_user_model()
    
    stats = {
        'users_count': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'titres_count': Titre.objects.count(),
        'demandes_count': Demande.objects.count(),
        'recent_backups': SystemBackup.objects.filter(
            status='completed'
        ).count(),
        'pending_maintenances': SystemMaintenance.objects.filter(
            status='scheduled'
        ).count()
    }
    
    # Activité récente (7 derniers jours)
    start_date = timezone.now() - timezone.timedelta(days=7)
    recent_activity = AuditLog.objects.filter(
        timestamp__gte=start_date
    ).values('action').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Dernières métriques
    latest_metrics = {}
    for metric_type, _ in SystemMetrics.METRIC_TYPES:
        latest = SystemMetrics.objects.filter(
            metric_type=metric_type
        ).order_by('-timestamp').first()
        
        if latest:
            latest_metrics[metric_type] = {
                'value': float(latest.value),
                'unit': latest.unit,
                'timestamp': latest.timestamp
            }
    
    return Response({
        'statistics': stats,
        'recent_activity': list(recent_activity),
        'latest_metrics': latest_metrics
    })
