# notifications/serializers.py
from rest_framework import serializers
from .models import Notification, NotificationPreference, EmailTemplate

class NotificationSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    time_since = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_name', 'title', 'message', 
            'type', 'type_display', 'priority', 'priority_display',
            'related_titre_id', 'related_demande_id', 'is_read', 
            'is_sent_email', 'created_at', 'read_at', 'time_since'
        ]
        read_only_fields = [
            'recipient', 'is_sent_email', 'created_at', 'read_at'
        ]
    
    def get_time_since(self, obj):
        """Temps écoulé depuis la création"""
        from django.utils.timesince import timesince
        return timesince(obj.created_at)

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            'user', 'email_expiration', 'email_status_change', 
            'email_assignment', 'email_reminders', 'app_all_notifications',
            'reminder_frequency_days', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'subject_template', 'body_template', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
