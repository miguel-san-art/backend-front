# notifications/services.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.template import Context, Template
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

from users.models import User
from titres.models import Titre
from demandes.models import Demande
from .models import Notification, EmailTemplate, NotificationPreference

logger = logging.getLogger(__name__)

class NotificationService:
    
    @staticmethod
    def create_notification(recipient, title, message, notification_type='info', 
                          priority='medium', related_titre_id=None, related_demande_id=None,
                          send_email=True):
        """Créer une nouvelle notification"""
        try:
            notification = Notification.objects.create(
                recipient=recipient,
                title=title,
                message=message,
                type=notification_type,
                priority=priority,
                related_titre_id=related_titre_id,
                related_demande_id=related_demande_id
            )
            
            # Envoyer par email si demandé
            if send_email:
                NotificationService.send_email_notification(notification)
            
            logger.info(f"Notification créée pour {recipient.email}: {title}")
            return notification
            
        except Exception as e:
            logger.error(f"Erreur création notification: {e}")
            return None
    
    @staticmethod
    def send_email_notification(notification):
        """Envoyer une notification par email"""
        try:
            # Vérifier les préférences utilisateur
            preferences, created = NotificationPreference.objects.get_or_create(
                user=notification.recipient
            )
            
            # Vérifier si l'utilisateur veut recevoir ce type d'email
            should_send = NotificationService._should_send_email(notification.type, preferences)
            
            if not should_send:
                logger.info(f"Email non envoyé selon préférences utilisateur: {notification.recipient.email}")
                return False
            
            # Préparer le contexte pour le template
            context = {
                'notification': notification,
                'recipient_name': notification.recipient.get_full_name() or notification.recipient.email,
                'site_url': getattr(settings, 'FRONTEND_URL', 'http://localhost:3000'),
                'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@telecom.com')
            }
            
            # Chercher un template personnalisé ou utiliser le template par défaut
            try:
                email_template = EmailTemplate.objects.get(
                    name=f'notification_{notification.type}',
                    is_active=True
                )
                subject = Template(email_template.subject_template).render(Context(context))
                html_message = Template(email_template.body_template).render(Context(context))
            except EmailTemplate.DoesNotExist:
                # Template par défaut
                subject = f"[Système Télécommunications] {notification.title}"
                html_message = NotificationService._get_default_email_template(context)
            
            # Version texte simple
            plain_message = f"""
Bonjour {context['recipient_name']},

{notification.message}

---
Système de Gestion des Titres de Télécommunications
{context['site_url']}
            """.strip()
            
            # Envoyer l'email
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.recipient.email],
                fail_silently=False
            )
            
            # Marquer comme envoyé
            notification.is_sent_email = True
            notification.save(update_fields=['is_sent_email'])
            
            logger.info(f"Email envoyé à {notification.recipient.email}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi email à {notification.recipient.email}: {e}")
            return False
    
    @staticmethod
    def _should_send_email(notification_type, preferences):
        """Vérifier si on doit envoyer l'email selon les préférences"""
        type_mapping = {
            'expiration': preferences.email_expiration,
            'status_change': preferences.email_status_change,
            'assignment': preferences.email_assignment,
            'reminder': preferences.email_reminders,
        }
        return type_mapping.get(notification_type, True)
    
    @staticmethod
    def _get_default_email_template(context):
        """Template email par défaut"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Notification</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #366092; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .footer {{ text-align: center; padding: 10px; font-size: 12px; color: #666; }}
        .button {{ display: inline-block; padding: 10px 20px; background-color: #366092; color: white; text-decoration: none; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Système de Gestion des Titres</h1>
        </div>
        <div class="content">
            <p>Bonjour {context['recipient_name']},</p>
            <p>{context['notification'].message}</p>
            <p>
                <a href="{context['site_url']}" class="button">Accéder au système</a>
            </p>
        </div>
        <div class="footer">
            <p>Ceci est un email automatique, merci de ne pas répondre.</p>
            <p>Pour toute question: {context['support_email']}</p>
        </div>
    </div>
</body>
</html>
        """.strip()
    
    @staticmethod
    def check_expiring_titles():
        """Vérifier et notifier les titres expirant bientôt"""
        try:
            # Titres expirant dans 30, 15, 7 et 1 jour(s)
            warning_days = [30, 15, 7, 1]
            
            for days in warning_days:
                target_date = timezone.now().date() + timedelta(days=days)
                
                expiring_titles = Titre.objects.filter(
                    date_expiration=target_date,
                    status='approuve'
                ).select_related('proprietaire')
                
                for titre in expiring_titles:
                    # Notification au propriétaire
                    NotificationService.create_notification(
                        recipient=titre.proprietaire,
                        title=f"Titre expirant dans {days} jour{'s' if days > 1 else ''}",
                        message=f"Votre titre {titre.numero_titre} ({titre.get_type_display()}) "
                               f"expire le {titre.date_expiration.strftime('%d/%m/%Y')}. "
                               f"Veuillez procéder au renouvellement dans les plus brefs délais.",
                        notification_type='expiration',
                        priority='high' if days <= 7 else 'medium',
                        related_titre_id=titre.id
                    )
                    
                    # Notification aux admins et personnel
                    admin_users = User.objects.filter(
                        profile__role__in=['admin', 'personnel']
                    )
                    
                    for admin in admin_users:
                        NotificationService.create_notification(
                            recipient=admin,
                            title=f"Titre expirant - {titre.proprietaire.get_full_name()}",
                            message=f"Le titre {titre.numero_titre} de {titre.entreprise_nom} "
                                   f"expire dans {days} jour{'s' if days > 1 else ''}.",
                            notification_type='expiration',
                            priority='medium',
                            related_titre_id=titre.id,
                            send_email=(days <= 7)  # Email seulement pour les cas urgents
                        )
            
            logger.info("Vérification des expirations terminée")
            return True
            
        except Exception as e:
            logger.error(f"Erreur vérification expirations: {e}")
            return False
    
    @staticmethod
    def notify_status_change(obj, old_status, new_status, changed_by):
        """Notifier un changement de statut"""
        try:
            if isinstance(obj, Titre):
                # Notifier le propriétaire
                NotificationService.create_notification(
                    recipient=obj.proprietaire,
                    title=f"Statut de votre titre modifié",
                    message=f"Le statut de votre titre {obj.numero_titre} est passé "
                           f"de '{old_status}' à '{new_status}' par {changed_by.get_full_name()}.",
                    notification_type='status_change',
                    priority='high',
                    related_titre_id=obj.id
                )
                
            elif isinstance(obj, Demande):
                # Notifier le demandeur
                NotificationService.create_notification(
                    recipient=obj.demandeur,
                    title=f"Statut de votre demande modifié",
                    message=f"Le statut de votre demande {obj.numero_dossier} est passé "
                           f"de '{old_status}' à '{new_status}' par {changed_by.get_full_name()}.",
                    notification_type='status_change',
                    priority='high',
                    related_demande_id=obj.id
                )
            
            logger.info(f"Notification changement statut envoyée pour {obj}")
            return True
                
        except Exception as e:
            logger.error(f"Erreur notification changement statut: {e}")
            return False
    
    @staticmethod
    def notify_assignment(demande, assignee, assigned_by):
        """Notifier une assignation de demande"""
        try:
            NotificationService.create_notification(
                recipient=assignee,
                title="Nouvelle demande assignée",
                message=f"La demande {demande.numero_dossier} de {demande.entreprise} "
                       f"vous a été assignée par {assigned_by.get_full_name()}. "
                       f"Type de titre: {demande.get_type_titre_display()}.",
                notification_type='assignment',
                priority='medium',
                related_demande_id=demande.id
            )
            
            logger.info(f"Notification assignation envoyée à {assignee.email}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur notification assignation: {e}")
            return False
    
    @staticmethod
    def check_overdue_requests():
        """Vérifier et notifier les demandes en retard"""
        try:
            overdue_date = timezone.now().date() - timedelta(days=30)
            
            overdue_requests = Demande.objects.filter(
                date_soumission__lte=overdue_date,
                status__in=['soumise', 'en_examen']
            ).select_related('demandeur', 'assignee')
            
            for demande in overdue_requests:
                # Notifier les responsables
                admin_users = User.objects.filter(
                    profile__role__in=['admin', 'personnel']
                )
                
                days_overdue = (timezone.now().date() - demande.date_soumission).days
                
                for admin in admin_users:
                    NotificationService.create_notification(
                        recipient=admin,
                        title="Demande en retard",
                        message=f"La demande {demande.numero_dossier} de {demande.entreprise} "
                               f"est en attente depuis {days_overdue} jours.",
                        notification_type='reminder',
                        priority='high',
                        related_demande_id=demande.id,
                        send_email=True
                    )
            
            logger.info(f"Vérification demandes en retard terminée: {len(overdue_requests)} demandes")
            return True
                    
        except Exception as e:
            logger.error(f"Erreur vérification demandes en retard: {e}")
            return False
    
    @staticmethod
    def bulk_notify(recipients, title, message, notification_type='info', priority='medium'):
        """Envoyer une notification à plusieurs destinataires"""
        try:
            notifications_created = 0
            for recipient in recipients:
                notification = NotificationService.create_notification(
                    recipient=recipient,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    priority=priority,
                    send_email=False  # Éviter le spam email
                )
                if notification:
                    notifications_created += 1
            
            logger.info(f"Notifications en masse créées: {notifications_created}")
            return notifications_created
            
        except Exception as e:
            logger.error(f"Erreur notifications en masse: {e}")
            return 0
    
    @staticmethod
    def notify_titre_created(titre):
        """Notifier la création d'un nouveau titre"""
        try:
            NotificationService.create_notification(
                recipient=titre.proprietaire,
                title="Nouveau titre créé",
                message=f"Votre titre {titre.numero_titre} ({titre.get_type_display()}) a été créé avec succès.",
                notification_type='info',
                priority='medium',
                related_titre_id=titre.id
            )
            logger.info(f"Notification création titre envoyée pour {titre.numero_titre}")
        except Exception as e:
            logger.error(f"Erreur notification création titre: {e}")
    
    @staticmethod
    def notify_titre_updated(titre):
        """Notifier la mise à jour d'un titre"""
        try:
            NotificationService.create_notification(
                recipient=titre.proprietaire,
                title="Titre mis à jour",
                message=f"Votre titre {titre.numero_titre} ({titre.get_type_display()}) a été mis à jour.",
                notification_type='info',
                priority='medium',
                related_titre_id=titre.id
            )
            logger.info(f"Notification mise à jour titre envoyée pour {titre.numero_titre}")
        except Exception as e:
            logger.error(f"Erreur notification mise à jour titre: {e}")

    @staticmethod
    def notify_demande_created(demande):
        """Notifier la création d'une nouvelle demande"""
        try:
            # Notification au demandeur
            NotificationService.create_notification(
                recipient=demande.demandeur,
                title="Nouvelle demande créée",
                message=f"Votre demande {demande.numero_dossier} a été enregistrée avec succès.",
                notification_type='info',
                priority='medium',
                related_demande_id=demande.id
            )
            
            # Notification aux admins/personnel
            admin_users = User.objects.filter(
                profile__role__in=['admin', 'personnel']
            )
            for admin in admin_users:
                NotificationService.create_notification(
                    recipient=admin,
                    title="Nouvelle demande soumise",
                    message=f"Une nouvelle demande {demande.numero_dossier} a été créée par {demande.demandeur.get_full_name()} ({demande.entreprise}).",
                    notification_type='info',
                    priority='medium',
                    related_demande_id=demande.id
                )
            
            logger.info(f"Notification création demande envoyée pour {demande.numero_dossier}")
        except Exception as e:
            logger.error(f"Erreur notification création demande: {e}")
