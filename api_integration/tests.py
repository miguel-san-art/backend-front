# api_integration/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import APIKey, APIRequest, Webhook, ExternalService
from .services import APIKeyService, WebhookService

User = get_user_model()


class APIKeyTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_api_key_creation(self):
        api_key = APIKey.objects.create(
            name='Test API Key',
            created_by=self.user
        )
        self.assertIsNotNone(api_key.key)
        self.assertIsNotNone(api_key.secret)
        self.assertTrue(api_key.key.startswith('tk_'))
    
    def test_api_key_validation(self):
        api_key = APIKey.objects.create(
            name='Test API Key',
            created_by=self.user
        )
        
        is_valid, result = APIKeyService.validate_api_key(api_key.key)
        self.assertTrue(is_valid)
        self.assertEqual(result, api_key)


class WebhookTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_webhook_creation(self):
        webhook = Webhook.objects.create(
            name='Test Webhook',
            url='https://example.com/webhook',
            events=['test.event'],
            created_by=self.user
        )
        self.assertEqual(webhook.name, 'Test Webhook')
        self.assertIsNotNone(webhook.secret)
        self.assertEqual(webhook.status, 'active')


class ExternalServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_external_service_creation(self):
        service = ExternalService.objects.create(
            name='Test Service',
            service_type='sms',
            base_url='https://api.example.com',
            created_by=self.user
        )
        self.assertEqual(service.name, 'Test Service')
        self.assertEqual(service.status, 'active')
        self.assertTrue(service.is_active)


class APIRequestTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.api_key = APIKey.objects.create(
            name='Test API Key',
            created_by=self.user
        )
    
    def test_api_request_logging(self):
        APIKeyService.log_request(
            api_key=self.api_key,
            method='GET',
            endpoint='/api/test/',
            ip_address='127.0.0.1',
            user_agent='Test Agent',
            status_code=200,
            response_time=150.5
        )
        
        request = APIRequest.objects.first()
        self.assertEqual(request.api_key, self.api_key)
        self.assertEqual(request.method, 'GET')
        self.assertEqual(request.status_code, 200)
        