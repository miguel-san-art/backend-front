# reporting/serializers.py
from rest_framework import serializers
from users.models import User
from .models import Report, Dashboard, AuditLog

class ReportSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    format_display = serializers.CharField(source='get_format_display', read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id', 'name', 'report_type', 'report_type_display',
            'format', 'format_display', 'created_by', 'created_by_name',
            'created_at', 'filters', 'file_path'
        ]
        read_only_fields = ['created_by', 'file_path', 'created_at']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class DashboardSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Dashboard
        fields = [
            'id', 'user', 'user_name', 'name', 'config', 'is_default', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_name', 'user_email', 'action', 'action_display',
            'model_name', 'object_id', 'description', 'ip_address', 
            'user_agent', 'timestamp'
        ]
        read_only_fields = ['user', 'timestamp']

class StatisticsSerializer(serializers.Serializer):
    """Serializer pour les statistiques du dashboard"""
    total_titres = serializers.IntegerField()
    total_demandes = serializers.IntegerField()
    total_users = serializers.IntegerField()
    titres_actifs = serializers.IntegerField()
    demandes_en_cours = serializers.IntegerField()
    titres_expirant_30j = serializers.IntegerField()
    titres_par_type = serializers.DictField()
    demandes_par_statut = serializers.DictField()
    evolution_mensuelle = serializers.ListField()
