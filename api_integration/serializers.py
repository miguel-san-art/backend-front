# api_integration/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import APIKey, APIRequest, Webhook, WebhookDelivery, ExternalService, ServiceHealthCheck


class APIKeySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    allowed_ips_list = serializers.ListField(source='get_allowed_ips_list', read_only=True)
    
    class Meta:
        model = APIKey
        fields = [
            'id', 'name', 'key', 'description', 'allowed_ips', 'allowed_ips_list',
            'allowed_endpoints', 'rate_limit', 'status', 'is_active',
            'created_at', 'updated_at', 'expires_at', 'last_used',
            'created_by', 'created_by_name', 'is_expired'
        ]
        read_only_fields = ['key', 'secret', 'created_at', 'updated_at', 'last_used']
        extra_kwargs = {
            'secret': {'write_only': True}
        }
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class APIRequestSerializer(serializers.ModelSerializer):
    api_key_name = serializers.CharField(source='api_key.name', read_only=True)
    
    class Meta:
        model = APIRequest
        fields = [
            'id', 'api_key', 'api_key_name', 'method', 'endpoint',
            'ip_address', 'user_agent', 'status_code', 'response_time',
            'response_size', 'timestamp', 'error_message'
        ]
        read_only_fields = ['timestamp']


class WebhookSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Webhook
        fields = [
            'id', 'name', 'url', 'description', 'events', 'headers',
            'status', 'is_active', 'success_count', 'failure_count',
            'success_rate', 'last_success', 'last_failure', 'last_error',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = [
            'secret', 'success_count', 'failure_count', 'last_success',
            'last_failure', 'last_error', 'created_at', 'updated_at'
        ]
    
    def get_success_rate(self, obj):
        """Calculer le taux de succès"""
        total = obj.success_count + obj.failure_count
        if total == 0:
            return 0
        return round((obj.success_count / total) * 100, 2)
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class WebhookDeliverySerializer(serializers.ModelSerializer):
    webhook_name = serializers.CharField(source='webhook.name', read_only=True)
    webhook_url = serializers.CharField(source='webhook.url', read_only=True)
    
    class Meta:
        model = WebhookDelivery
        fields = [
            'id', 'webhook', 'webhook_name', 'webhook_url', 'event',
            'status', 'http_status', 'response_body', 'error_message',
            'attempts', 'max_attempts', 'next_retry',
            'created_at', 'delivered_at'
        ]
        read_only_fields = ['created_at', 'delivered_at']


class ExternalServiceSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ExternalService
        fields = [
            'id', 'name', 'service_type', 'service_type_display', 'base_url',
            'description', 'config', 'headers', 'status', 'status_display',
            'is_active', 'last_check', 'response_time', 'uptime_percentage',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = [
            'last_check', 'response_time', 'uptime_percentage',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'api_key': {'write_only': True},
            'api_secret': {'write_only': True}
        }
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ServiceHealthCheckSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ServiceHealthCheck
        fields = [
            'service', 'service_name', 'status', 'status_display',
            'response_time', 'status_code', 'error_message', 'checked_at'
        ]
        read_only_fields = ['checked_at']


class APIDocumentationSerializer(serializers.Serializer):
    """Serializer pour la documentation API"""
    endpoint = serializers.CharField()
    method = serializers.CharField()
    description = serializers.CharField()
    parameters = serializers.JSONField()
    response_example = serializers.JSONField()
    authentication_required = serializers.BooleanField()


class APIStatisticsSerializer(serializers.Serializer):
    """Serializer pour les statistiques API"""
    total_requests = serializers.IntegerField()
    successful_requests = serializers.IntegerField()
    failed_requests = serializers.IntegerField()
    average_response_time = serializers.DecimalField(max_digits=10, decimal_places=3)
    requests_by_endpoint = serializers.JSONField()
    requests_by_status = serializers.JSONField()
    top_api_keys = serializers.JSONField()
    