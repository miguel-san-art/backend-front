# gestion_demandes/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Demande, Document, HistoriqueDemande, CommentaireDemande

@admin.register(Demande)
class DemandeAdmin(admin.ModelAdmin):
    """Interface d'administration pour les demandes."""
    
    list_display = [
        'numero_dossier', 'entreprise', 'type_titre_display', 'status_display',
        'demandeur_email', 'assignee_display', 'date_soumission', 'is_overdue_display'
    ]
    list_filter = [
        'status', 'type_titre', 'date_soumission', 'assignee'
    ]
    search_fields = [
        'numero_dossier', 'entreprise', 'email_contact', 'demandeur__email',
        'description'
    ]
    readonly_fields = [
        'numero_dossier', 'date_soumission', 'created_at', 'updated_at',
        'days_since_submission', 'is_overdue'
    ]
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('numero_dossier', 'demandeur', 'entreprise', 'email_contact', 'telephone', 'adresse')
        }),
        ('Demande', {
            'fields': ('type_titre', 'description', 'motivations')
        }),
        ('Traitement', {
            'fields': ('status', 'assignee', 'commentaires_admin', 'date_traitement')
        }),
        ('Métadonnées', {
            'fields': ('date_soumission', 'days_since_submission', 'is_overdue', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def type_titre_display(self, obj):
        return obj.get_type_titre_display()
    type_titre_display.short_description = 'Type de titre'
    
    def status_display(self, obj):
        colors = {
            'soumise': '#fbbf24',      # yellow
            'en_examen': '#3b82f6',    # blue
            'approuvee': '#10b981',    # green
            'rejetee': '#ef4444',      # red
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Statut'
    
    def demandeur_email(self, obj):
        return obj.demandeur.email if obj.demandeur else 'N/A'
    demandeur_email.short_description = 'Email demandeur'
    
    def assignee_display(self, obj):
        if obj.assignee and hasattr(obj.assignee, 'profile'):
            return f"{obj.assignee.profile.nom} {obj.assignee.profile.prenom}"
        elif obj.assignee:
            return obj.assignee.email
        return 'Non assigné'
    assignee_display.short_description = 'Assigné à'
    
    def is_overdue_display(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color: #ef4444; font-weight: bold;">En retard</span>')
        return format_html('<span style="color: #10b981;">À jour</span>')
    is_overdue_display.short_description = 'Statut délai'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('demandeur', 'assignee')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Interface d'administration pour les documents."""
    
    list_display = [
        'nom_fichier', 'type_document', 'demande_numero', 'uploade_par_email',
        'taille_fichier_readable', 'version', 'est_actif', 'created_at'
    ]
    list_filter = [
        'type_document', 'est_actif', 'version', 'created_at'
    ]
    search_fields = [
        'nom_fichier', 'description', 'demande__numero_dossier', 'demande__entreprise'
    ]
    readonly_fields = [
        'taille_fichier', 'hash_fichier', 'taille_fichier_readable', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Informations du document', {
            'fields': ('nom_fichier', 'type_document', 'fichier', 'description')
        }),
        ('Associations', {
            'fields': ('demande', 'titre')
        }),
        ('Métadonnées', {
            'fields': ('uploade_par', 'version', 'est_actif', 'taille_fichier', 
                      'taille_fichier_readable', 'hash_fichier')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def demande_numero(self, obj):
        if obj.demande:
            return obj.demande.numero_dossier or str(obj.demande.id)[:8]
        return 'N/A'
    demande_numero.short_description = 'N° dossier'
    
    def uploade_par_email(self, obj):
        return obj.uploade_par.email if obj.uploade_par else 'N/A'
    uploade_par_email.short_description = 'Uploadé par'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('demande', 'titre', 'uploade_par')

@admin.register(HistoriqueDemande)
class HistoriqueDemandeAdmin(admin.ModelAdmin):
    """Interface d'administration pour l'historique des demandes."""
    
    list_display = [
        'demande_numero', 'action_display', 'utilisateur_display', 'date_action'
    ]
    list_filter = ['action', 'date_action', 'utilisateur']
    search_fields = [
        'demande__numero_dossier', 'demande__entreprise', 'commentaire'
    ]
    readonly_fields = [
        'demande', 'action', 'utilisateur', 'commentaire', 'ancien_status',
        'nouveau_status', 'date_action', 'donnees_modifiees'
    ]
    
    def demande_numero(self, obj):
        return obj.demande.numero_dossier or str(obj.demande.id)[:8]
    demande_numero.short_description = 'N° dossier'
    
    def action_display(self, obj):
        return obj.get_action_display()
    action_display.short_description = 'Action'
    
    def utilisateur_display(self, obj):
        if obj.utilisateur and hasattr(obj.utilisateur, 'profile'):
            return f"{obj.utilisateur.profile.nom} {obj.utilisateur.profile.prenom}"
        elif obj.utilisateur:
            return obj.utilisateur.email
        return 'Système'
    utilisateur_display.short_description = 'Utilisateur'

@admin.register(CommentaireDemande)
class CommentaireDemandeAdmin(admin.ModelAdmin):
    """Interface d'administration pour les commentaires."""
    
    list_display = [
        'demande_numero', 'auteur_display', 'type_commentaire', 'est_resolu', 'created_at'
    ]
    list_filter = ['type_commentaire', 'est_resolu', 'created_at']
    search_fields = [
        'demande__numero_dossier', 'contenu', 'auteur__email'
    ]
    
    def demande_numero(self, obj):
        return obj.demande.numero_dossier or str(obj.demande.id)[:8]
    demande_numero.short_description = 'N° dossier'
    
    def auteur_display(self, obj):
        if obj.auteur and hasattr(obj.auteur, 'profile'):
            return f"{obj.auteur.profile.nom} {obj.auteur.profile.prenom}"
        elif obj.auteur:
            return obj.auteur.email
        return 'Inconnu'
    auteur_display.short_description = 'Auteur'
    