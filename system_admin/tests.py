# system_admin/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import SystemConfiguration, AuditLog, SystemBackup, SystemMetrics, SystemMaintenance
from .services import SystemConfigService, AuditService

User = get_user_model()


class SystemConfigurationTest(TestCase):
    def test_config_creation(self):
        config = SystemConfiguration.objects.create(
            key='test_setting',
            value='test_value',
            description='Test configuration',
            category='test'
        )
        self.assertEqual(config.key, 'test_setting')
        self.assertEqual(config.get_value(), 'test_value')
    
    def test_json_value_handling(self):
        config = SystemConfiguration.objects.create(
            key='json_setting',
            value='{"key": "value", "number": 123}',
            category='test'
        )
        parsed_value = config.get_value()
        self.assertIsInstance(parsed_value, dict)
        self.assertEqual(parsed_value['key'], 'value')
        self.assertEqual(parsed_value['number'], 123)


class AuditLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_audit_log_creation(self):
        log = AuditLog.objects.create(
            user=self.user,
            action='create',
            resource_type='test_resource',
            description='Test audit log'
        )
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.level, 'info')


class SystemBackupTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_backup_creation(self):
        backup = SystemBackup.objects.create(
            name='Test Backup',
            backup_type='full',
            created_by=self.user
        )
        self.assertEqual(backup.name, 'Test Backup')
        self.assertEqual(backup.status, 'pending')


class SystemMetricsTest(TestCase):
    def test_metrics_creation(self):
        metrics = SystemMetrics.objects.create(
            metric_type='users_active',
            value=150,
            unit='count'
        )
        self.assertEqual(metrics.metric_type, 'users_active')
        self.assertEqual(float(metrics.value), 150.0)
        