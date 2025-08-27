# system_admin/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import SystemConfiguration, AuditLog, SystemBackup, SystemMetrics, SystemMaintenance


class SystemConfigurationSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)
    parsed_value = serializers.SerializerMethodField()
    
    class Meta:
        model = SystemConfiguration
        fields = [
            'id', 'key', 'value', 'parsed_value', 'description', 'category',
            'is_active', 'created_at', 'updated_at', 'updated_by', 'updated_by_name'
        ]
        read_only_fields = ['created_at', 'updated_at', 'updated_by']
    
    def get_parsed_value(self, obj):
        return obj.get_value()
    
    def update(self, instance, validated_data):
        # Enregistrer qui a fait la modification
        instance.updated_by = self.context['request'].user
        return super().update(instance, validated_data)


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_name', 'action', 'action_display', 
            'level', 'level_display', 'resource_type', 'resource_id',
            'description', 'ip_address', 'user_agent', 'extra_data', 'timestamp'
        ]
        read_only_fields = ['timestamp']


class SystemBackupSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_backup_type_display', read_only=True)
    duration = serializers.SerializerMethodField()
    formatted_file_size = serializers.CharField(read_only=True)
    
    class Meta:
        model = SystemBackup
        fields = [
            'id', 'name', 'backup_type', 'type_display', 'status', 'status_display',
            'file_path', 'file_size', 'formatted_file_size', 'description',
            'created_by', 'created_by_name', 'created_at', 'started_at', 
            'completed_at', 'duration', 'error_message'
        ]
        read_only_fields = [
            'file_path', 'file_size', 'created_at', 'started_at', 
            'completed_at', 'error_message'
        ]
    
    def get_duration(self, obj):
        duration = obj.duration
        if duration:
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return None


class SystemMetricsSerializer(serializers.ModelSerializer):
    metric_type_display = serializers.CharField(source='get_metric_type_display', read_only=True)
    
    class Meta:
        model = SystemMetrics
        fields = [
            'id', 'metric_type', 'metric_type_display', 'value', 'unit', 
            'timestamp', 'metadata'
        ]
        read_only_fields = ['timestamp']


class SystemMaintenanceSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = SystemMaintenance
        fields = [
            'id', 'title', 'description', 'status', 'status_display',
            'priority', 'priority_display', 'scheduled_start', 'scheduled_end',
            'actual_start', 'actual_end', 'impact_description', 'notification_sent',
            'created_by', 'created_by_name', 'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['created_at', 'updated_at', 'notification_sent']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
    