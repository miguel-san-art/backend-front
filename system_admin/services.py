# system_admin/services.py
import os
import subprocess
import logging
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.db import connection
from django.core.management import call_command
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import models

from .models import SystemConfiguration, AuditLog, SystemBackup, SystemMetrics, SystemMaintenance

logger = logging.getLogger(__name__)


class SystemConfigService:
    """Service de gestion de la configuration système"""
    
    @staticmethod
    def get_config(key, default=None, category='general'):
        """Récupérer une valeur de configuration"""
        try:
            config = SystemConfiguration.objects.get(key=key, is_active=True)
            return config.get_value()
        except SystemConfiguration.DoesNotExist:
            return default
    
    @staticmethod
    def set_config(key, value, description='', category='general', user=None):
        """Définir une valeur de configuration"""
        try:
            config, created = SystemConfiguration.objects.get_or_create(
                key=key,
                defaults={
                    'value': value,
                    'description': description,
                    'category': category,
                    'updated_by': user
                }
            )
            
            if not created:
                config.set_value(value)
                config.description = description
                config.category = category
                config.updated_by = user
                config.save()
            
            # Log de l'audit
            AuditService.log_action(
                user=user,
                action='config',
                resource_type='SystemConfiguration',
                resource_id=str(config.id),
                description=f"Configuration modifiée: {key} = {value}"
            )
            
            return config
        except Exception as e:
            logger.error(f"Erreur configuration système {key}: {e}")
            return None
    
    @staticmethod
    def get_all_configs(category=None):
        """Récupérer toutes les configurations"""
        queryset = SystemConfiguration.objects.filter(is_active=True)
        if category:
            queryset = queryset.filter(category=category)
        
        return {config.key: config.get_value() for config in queryset}


class AuditService:
    """Service de gestion des logs d'audit"""
    
    @staticmethod
    def log_action(user=None, action='info', resource_type='', resource_id='',
                   description='', level='info', ip_address=None, user_agent='', 
                   extra_data=None):
        """Enregistrer une action dans le journal d'audit"""
        try:
            AuditLog.objects.create(
                user=user,
                action=action,
                level=level,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                extra_data=extra_data or {}
            )
            logger.info(f"Action auditée: {action} - {description}")
            return True
        except Exception as e:
            logger.error(f"Erreur enregistrement audit: {e}")
            return False
    
    @staticmethod
    def get_user_activity(user, days=30):
        """Récupérer l'activité d'un utilisateur"""
        start_date = timezone.now() - timedelta(days=days)
        return AuditLog.objects.filter(
            user=user,
            timestamp__gte=start_date
        ).order_by('-timestamp')
    
    @staticmethod
    def get_system_activity(days=7):
        """Récupérer l'activité générale du système"""
        start_date = timezone.now() - timedelta(days=days)
        return AuditLog.objects.filter(
            timestamp__gte=start_date
        ).values('action', 'level').annotate(
            count=models.Count('id')
        )


class BackupService:
    """Service de gestion des sauvegardes"""
    
    @staticmethod
    def create_backup(name, backup_type='full', description='', user=None):
        """Créer une nouvelle sauvegarde"""
        try:
            backup = SystemBackup.objects.create(
                name=name,
                backup_type=backup_type,
                description=description,
                created_by=user,
                status='pending'
            )
            
            # Lancer la sauvegarde en arrière-plan
            BackupService._execute_backup(backup)
            
            return backup
        except Exception as e:
            logger.error(f"Erreur création sauvegarde: {e}")
            return None
    
    @staticmethod
    def _execute_backup(backup):
        """Exécuter la sauvegarde"""
        try:
            backup.status = 'running'
            backup.started_at = timezone.now()
            backup.save()
            
            # Créer le répertoire de sauvegarde
            backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{backup.name}_{timestamp}.sql"
            file_path = os.path.join(backup_dir, filename)
            
            # Commande de sauvegarde MySQL
            db_settings = settings.DATABASES['default']
            cmd = [
                'mysqldump',
                f'--host={db_settings["HOST"]}',
                f'--port={db_settings.get("PORT", 3306)}',
                f'--user={db_settings["USER"]}',
                f'--password={db_settings["PASSWORD"]}',
                '--single-transaction',
                '--routines',
                '--triggers',
                db_settings['NAME']
            ]
            
            # Exécuter la commande
            with open(file_path, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                # Succès
                backup.status = 'completed'
                backup.completed_at = timezone.now()
                backup.file_path = file_path
                backup.file_size = os.path.getsize(file_path)
                
                AuditService.log_action(
                    user=backup.created_by,
                    action='backup',
                    resource_type='SystemBackup',
                    resource_id=str(backup.id),
                    description=f"Sauvegarde créée: {backup.name}"
                )
            else:
                # Erreur
                backup.status = 'failed'
                backup.error_message = result.stderr
                backup.completed_at = timezone.now()
                
            backup.save()
            
        except Exception as e:
            backup.status = 'failed'
            backup.error_message = str(e)
            backup.completed_at = timezone.now()
            backup.save()
            logger.error(f"Erreur exécution sauvegarde: {e}")


class MetricsService:
    """Service de collecte des métriques système"""
    
    @staticmethod
    def collect_metrics():
        """Collecter toutes les métriques système"""
        try:
            # Utilisateurs actifs (dernières 24h)
            from django.contrib.sessions.models import Session
            active_sessions = Session.objects.filter(
                expire_date__gte=timezone.now()
            ).count()
            
            MetricsService._record_metric('users_active', active_sessions)
            
            # Taille de la base de données
            db_size = MetricsService._get_database_size()
            if db_size:
                MetricsService._record_metric('database_size', db_size, 'MB')
            
            # Espace de stockage utilisé
            storage_size = MetricsService._get_storage_size()
            if storage_size:
                MetricsService._record_metric('storage_used', storage_size, 'MB')
            
            logger.info("Métriques système collectées")
            return True
            
        except Exception as e:
            logger.error(f"Erreur collecte métriques: {e}")
            return False
    
    @staticmethod
    def _record_metric(metric_type, value, unit=''):
        """Enregistrer une métrique"""
        SystemMetrics.objects.create(
            metric_type=metric_type,
            value=value,
            unit=unit
        )
    
    @staticmethod
    def _get_database_size():
        """Obtenir la taille de la base de données"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) 
                    as size_mb FROM information_schema.tables 
                    WHERE table_schema = %s
                """, [settings.DATABASES['default']['NAME']])
                
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Erreur calcul taille DB: {e}")
            return None
    
    @staticmethod
    def _get_storage_size():
        """Obtenir la taille du stockage utilisé"""
        try:
            total_size = 0
            media_root = settings.MEDIA_ROOT
            
            for dirpath, dirnames, filenames in os.walk(media_root):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    total_size += os.path.getsize(filepath)
            
            return round(total_size / (1024 * 1024), 2)  # MB
        except Exception as e:
            logger.error(f"Erreur calcul taille stockage: {e}")
            return None


class MaintenanceService:
    """Service de gestion des maintenances"""
    
    @staticmethod
    def schedule_maintenance(title, description, start_time, end_time, 
                           priority='medium', impact_description='', user=None):
        """Planifier une maintenance"""
        try:
            maintenance = SystemMaintenance.objects.create(
                title=title,
                description=description,
                scheduled_start=start_time,
                scheduled_end=end_time,
                priority=priority,
                impact_description=impact_description,
                created_by=user
            )
            
            AuditService.log_action(
                user=user,
                action='create',
                resource_type='SystemMaintenance',
                resource_id=str(maintenance.id),
                description=f"Maintenance planifiée: {title}"
            )
            
            return maintenance
        except Exception as e:
            logger.error(f"Erreur planification maintenance: {e}")
            return None
    
    @staticmethod
    def start_maintenance(maintenance_id, user=None):
        """Démarrer une maintenance"""
        try:
            maintenance = SystemMaintenance.objects.get(id=maintenance_id)
            maintenance.status = 'in_progress'
            maintenance.actual_start = timezone.now()
            maintenance.save()
            
            # Notification des utilisateurs si configuré
            if not maintenance.notification_sent:
                MaintenanceService._notify_users_maintenance(maintenance)
                maintenance.notification_sent = True
                maintenance.save()
            
            AuditService.log_action(
                user=user,
                action='update',
                resource_type='SystemMaintenance',
                resource_id=str(maintenance.id),
                description=f"Maintenance démarrée: {maintenance.title}"
            )
            
            return True
        except Exception as e:
            logger.error(f"Erreur démarrage maintenance: {e}")
            return False
    
    @staticmethod
    def complete_maintenance(maintenance_id, user=None):
        """Terminer une maintenance"""
        try:
            maintenance = SystemMaintenance.objects.get(id=maintenance_id)
            maintenance.status = 'completed'
            maintenance.actual_end = timezone.now()
            maintenance.save()
            
            AuditService.log_action(
                user=user,
                action='update',
                resource_type='SystemMaintenance',
                resource_id=str(maintenance.id),
                description=f"Maintenance terminée: {maintenance.title}"
            )
            
            return True
        except Exception as e:
            logger.error(f"Erreur fin maintenance: {e}")
            return False
    
    @staticmethod
    def _notify_users_maintenance(maintenance):
        """Notifier les utilisateurs d'une maintenance"""
        try:
            from notifications.services import NotificationService
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            all_users = User.objects.filter(is_active=True)
            
            message = f"""
Une maintenance système est programmée:
📅 Du {maintenance.scheduled_start.strftime('%d/%m/%Y %H:%M')} 
   au {maintenance.scheduled_end.strftime('%d/%m/%Y %H:%M')}

🔧 Description: {maintenance.description}

{f'⚠️ Impact: {maintenance.impact_description}' if maintenance.impact_description else ''}

Nous nous excusons pour la gêne occasionnée.
            """.strip()
            
            NotificationService.bulk_notify(
                recipients=all_users,
                title=f"Maintenance programmée: {maintenance.title}",
                message=message,
                notification_type='warning',
                priority=maintenance.priority
            )
            
        except Exception as e:
            logger.error(f"Erreur notification maintenance: {e}")
            