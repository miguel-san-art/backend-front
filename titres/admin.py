# titres/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Titre, HistoriqueTitre, RedevanceTitre

@admin.register(Titre)
class TitreAdmin(admin.ModelAdmin):
    list_display = [
        'numero_titre', 'type', 'get_proprietaire_nom', 'entreprise_nom',
        'status', 'date_emission', 'date_expiration', 'get_status_badge',
        'redevance_annuelle', 'is_expired'
    ]
    list_filter = ['type', 'status', 'date_emission', 'date_expiration']
    search_fields = [
        'numero_titre', 'entreprise_nom', 'proprietaire__email',
        'proprietaire__profile__nom', 'proprietaire__profile__prenom'
    ]
    readonly_fields = ['numero_titre', 'redevance_annuelle', 'created_at', 'updated_at']
    date_hierarchy = 'date_emission'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('numero_titre', 'type', 'proprietaire', 'entreprise_nom')
        }),
        ('Dates et durée', {
            'fields': ('date_emission', 'date_expiration', 'duree_ans')
        }),
        ('Statut et conditions', {
            'fields': ('status', 'description', 'conditions_specifiques')
        }),
        ('Redevance', {
            'fields': ('redevance_annuelle',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_proprietaire_nom(self, obj):
        if hasattr(obj.proprietaire, 'profile'):
            return f"{obj.proprietaire.profile.nom} {obj.proprietaire.profile.prenom}"
        return obj.proprietaire.email
    get_proprietaire_nom.short_description = 'Propriétaire'
    
    def get_status_badge(self, obj):
        colors = {
            'en_attente': 'orange',
            'en_cours': 'blue',
            'approuve': 'green',
            'rejete': 'red',
            'expire': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_badge.short_description = 'Statut'
    
    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = 'Expiré'


class RedevanceTitreInline(admin.TabularInline):
    model = RedevanceTitre
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['annee', 'montant', 'date_echeance', 'date_paiement', 'status_paiement', 'reference_paiement']


@admin.register(RedevanceTitre)
class RedevanceTitreAdmin(admin.ModelAdmin):
    list_display = [
        'get_titre_numero', 'annee', 'montant', 'date_echeance',
        'date_paiement', 'get_status_badge', 'reference_paiement', 'is_overdue'
    ]
    list_filter = ['status_paiement', 'annee', 'date_echeance']
    search_fields = [
        'titre__numero_titre', 'titre__entreprise_nom',
        'reference_paiement', 'titre__proprietaire__email'
    ]
    date_hierarchy = 'date_echeance'
    ordering = ['-annee', '-date_echeance']
    
    def get_titre_numero(self, obj):
        return obj.titre.numero_titre
    get_titre_numero.short_description = 'Numéro de titre'
    
    def get_status_badge(self, obj):
        colors = {
            'en_attente': 'orange',
            'paye': 'green',
            'en_retard': 'red',
            'annule': 'gray'
        }
        color = colors.get(obj.status_paiement, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_paiement_display()
        )
    get_status_badge.short_description = 'Statut paiement'
    
    def is_overdue(self, obj):
        return obj.is_overdue
    is_overdue.boolean = True
    is_overdue.short_description = 'En retard'


@admin.register(HistoriqueTitre)
class HistoriqueTitreAdmin(admin.ModelAdmin):
    list_display = [
        'get_titre_numero', 'action', 'get_utilisateur_nom',
        'ancien_status', 'nouveau_status', 'date_action'
    ]
    list_filter = ['action', 'ancien_status', 'nouveau_status', 'date_action']
    search_fields = [
        'titre__numero_titre', 'utilisateur__email',
        'utilisateur__profile__nom', 'commentaire'
    ]
    readonly_fields = ['date_action']
    date_hierarchy = 'date_action'
    ordering = ['-date_action']
    
    def get_titre_numero(self, obj):
        return obj.titre.numero_titre
    get_titre_numero.short_description = 'Numéro de titre'
    
    def get_utilisateur_nom(self, obj):
        if obj.utilisateur:
            if hasattr(obj.utilisateur, 'profile'):
                return f"{obj.utilisateur.profile.nom} {obj.utilisateur.profile.prenom}"
            return obj.utilisateur.email
        return "Système"
    get_utilisateur_nom.short_description = 'Utilisateur'
    
    def has_add_permission(self, request):
        # Empêcher l'ajout manuel d'historique
        return False
    
    def has_change_permission(self, request, obj=None):
        # Empêcher la modification de l'historique
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Empêcher la suppression de l'historique
        return False


# Personnalisation de l'interface d'administration
admin.site.site_header = "Administration - Gestion des Titres de Télécommunications"
admin.site.site_title = "Titres Télécom Admin"
admin.site.index_title = "Gestion des Titres de Télécommunications"
