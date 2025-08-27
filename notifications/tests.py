# notifications/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Notification, NotificationPreference, EmailTemplate
from .services import NotificationService

User = get_user_model()


class NotificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_notification_creation(self):
        notification = Notification.objects.create(
            recipient=self.user,
            title='Test Notification',
            message='This is a test message',
            type='info'
        )
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.title, 'Test Notification')
        self.assertFalse(notification.is_read)
    
    def test_notification_mark_as_read(self):
        notification = Notification.objects.create(
            recipient=self.user,
            title='Test Notification',
            message='This is a test message'
        )
        notification.mark_as_read()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)


class NotificationServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_notification(self):
        result = NotificationService.create_notification(
            recipient=self.user,
            title='Test Notification',
            message='Test message',
            notification_type='info'
        )
        self.assertTrue(result)
        self.assertEqual(Notification.objects.count(), 1)


class EmailTemplateTest(TestCase):
    def test_email_template_creation(self):
        template = EmailTemplate.objects.create(
            name='test_template',
            subject_template='Test Subject: {title}',
            body_template='Hello {user}, this is a test: {message}'
        )
        self.assertEqual(template.name, 'test_template')
        self.assertTrue(template.is_active)
        