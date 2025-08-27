# notifications/views.py
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from .models import Notification, NotificationPreference, EmailTemplate
from .serializers import NotificationSerializer, NotificationPreferenceSerializer, EmailTemplateSerializer
from .services import NotificationService


class NotificationListView(generics.ListAPIView):
    """Liste des notifications de l'utilisateur connecté"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Notification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')
        
        # Filtrage par type
        notification_type = self.request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(type=notification_type)
            
        # Filtrage par statut lu/non lu
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
            
        return queryset


class NotificationDetailView(generics.RetrieveUpdateAPIView):
    """Détail d'une notification (principalement pour marquer comme lue)"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, pk):
    """Marquer une notification comme lue"""
    notification = get_object_or_404(
        Notification, 
        pk=pk, 
        recipient=request.user
    )
    
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])
    
    return Response({'status': 'marked_as_read'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """Marquer toutes les notifications comme lues"""
    updated_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    return Response({
        'status': 'success',
        'updated_count': updated_count
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_counts(request):
    """Compteurs de notifications"""
    user_notifications = Notification.objects.filter(recipient=request.user)
    
    counts = {
        'total': user_notifications.count(),
        'unread': user_notifications.filter(is_read=False).count(),
        'by_type': {}
    }
    
    # Compter par type
    for notification_type, _ in Notification.TYPE_CHOICES:
        counts['by_type'][notification_type] = user_notifications.filter(
            type=notification_type
        ).count()
    
    return Response(counts)


class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    """Gestion des préférences de notification de l'utilisateur"""
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        preference, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preference


class EmailTemplateListView(generics.ListCreateAPIView):
    """Liste et création des templates d'email (admin seulement)"""
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Seuls les admins peuvent voir tous les templates
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            return EmailTemplate.objects.all()
        else:
            return EmailTemplate.objects.filter(is_active=True)


class EmailTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Détail, modification et suppression des templates d'email"""
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Seuls les admins peuvent modifier/supprimer
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            return EmailTemplate.objects.all()
        else:
            return EmailTemplate.objects.none()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_bulk_notification(request):
    """Envoyer une notification à plusieurs utilisateurs (admin seulement)"""
    if not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    title = request.data.get('title')
    message = request.data.get('message')
    notification_type = request.data.get('type', 'info')
    priority = request.data.get('priority', 'medium')
    user_ids = request.data.get('user_ids', [])
    
    if not title or not message:
        return Response(
            {'error': 'Title and message are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    from django.contrib.auth.models import User
    recipients = User.objects.filter(id__in=user_ids)
    
    if not recipients.exists():
        return Response(
            {'error': 'No valid recipients found'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    count = NotificationService.bulk_notify(
        recipients=recipients,
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority
    )
    
    return Response({
        'status': 'success',
        'notifications_sent': count
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_email_template(request, pk):
    """Tester un template d'email (admin seulement)"""
    if not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    template = get_object_or_404(EmailTemplate, pk=pk)
    test_email = request.data.get('test_email', request.user.email)
    
    # Créer une notification de test
    test_notification = Notification(
        recipient=request.user,
        title="Test Email Template",
        message="Ceci est un test du template d'email.",
        type='info'
    )
    
    try:
        success = NotificationService.send_email_notification(test_notification)
        return Response({
            'status': 'success' if success else 'error',
            'message': 'Test email sent' if success else 'Failed to send test email'
        })
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    