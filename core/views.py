# core/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q
from django.utils import timezone
from datetime import date, timedelta
import json

from users.models import User, Profile
from titres.models import Titre, HistoriqueTitre, RedevanceTitre
from demandes.models import Demande
from notifications.models import Notification


def login_view(request):
    """Vue pour la connexion des utilisateurs."""
    if request.user.is_authenticated:
        return redirect('dashboard_overview')
    
    if request.method == 'POST':
        email = request.POST.get('username')  # Le champ s'appelle username dans le form mais contient l'email
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Bienvenue {user.profile.nom} {user.profile.prenom}!')
            
            # Redirection selon le rôle
            if user.profile.role == 'operateur':
                return redirect('title_creation_and_edit_form')
            elif user.profile.role == 'personnel':
                return redirect('title_tracking_staff')
            else:  # admin
                return redirect('dashboard_overview')
        else:
            messages.error(request, 'Email ou mot de passe incorrect.')
    
    return render(request, 'login.html')


@login_required
def logout_view(request):
    """Vue pour la déconnexion."""
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('login')


@login_required
def dashboard_overview(request):
    """Vue pour le tableau de bord principal."""
    user = request.user
    
    # Statistiques de base
    stats = {}
    
    # Filtrer les titres selon le rôle
    if user.profile.role == 'operateur':
        titres_queryset = Titre.objects.filter(proprietaire=user)
    else:
        titres_queryset = Titre.objects.all()
    
    # Calcul des statistiques
    stats['titres_actifs'] = titres_queryset.filter(status='approuve').count()
    stats['titres_expires'] = titres_queryset.filter(date_expiration__lt=date.today()).count()
    
    # Titres expirant dans les 30 jours
    date_limite = date.today() + timedelta(days=30)
    stats['titres_expirant_bientot'] = titres_queryset.filter(
        date_expiration__lte=date_limite,
        date_expiration__gte=date.today(),
        status='approuve'
    ).count()
    
    # Ajouts récents (cette semaine)
    date_semaine = date.today() - timedelta(days=7)
    stats['ajouts_recents'] = titres_queryset.filter(created_at__gte=date_semaine).count()
    
    # Dates importantes
    dernier_titre = titres_queryset.order_by('-created_at').first()
    stats['dernier_ajout'] = dernier_titre.created_at if dernier_titre else None
    
    titre_expire = titres_queryset.filter(date_expiration__lt=date.today()).order_by('-date_expiration').first()
    stats['derniere_expiration'] = titre_expire.date_expiration if titre_expire else None
    
    prochain_renouvellement = titres_queryset.filter(
        date_expiration__gte=date.today()
    ).order_by('date_expiration').first()
    stats['prochain_renouvellement'] = prochain_renouvellement.date_expiration if prochain_renouvellement else None
    
    # Calcul de la valeur totale des titres actifs
    titres_actifs = titres_queryset.filter(status='approuve')
    stats['valeur_totale'] = sum(titre.redevance_annuelle for titre in titres_actifs)
    
    # Statistiques supplémentaires
    stats['taux_conformite'] = 94.2  # Exemple
    stats['revenus_mois'] = 847  # En millions XAF
    stats['nouveaux_clients'] = 127
    stats['en_attente'] = titres_queryset.filter(status='en_attente').count()
    
    # Activités récentes
    recent_activities = []
    historique = HistoriqueTitre.objects.select_related('titre', 'utilisateur__profile')
    
    if user.profile.role == 'operateur':
        historique = historique.filter(titre__proprietaire=user)
    
    for hist in historique.order_by('-date_action')[:10]:
        activity = {
            'action': hist.get_action_display(),
            'titre_numero': hist.titre.numero_titre,
            'utilisateur': f"{hist.utilisateur.profile.nom} {hist.utilisateur.profile.prenom}" if hist.utilisateur else "Système",
            'date': hist.date_action,
            'status': hist.titre.get_status_display(),
            'status_class': get_status_class(hist.titre.status),
            'icon': get_action_icon(hist.action),
            'icon_color': get_action_icon_color(hist.action)
        }
        recent_activities.append(activity)
    
    # Notifications
    notifications = []
    urgent_count = 0
    
    # Notification pour titres expirés
    if stats['titres_expires'] > 0:
        notifications.append({
            'type': 'error',
            'icon': 'exclamation-circle',
            'title': 'Titres expirés',
            'message': f"{stats['titres_expires']} titres ont expiré et nécessitent une action immédiate",
            'action_url': '/titres/?filter=expired',
            'action_text': 'Voir les titres'
        })
        urgent_count += 1
    
    # Notification pour renouvellements
    if stats['titres_expirant_bientot'] > 0:
        notifications.append({
            'type': 'warning',
            'icon': 'clock',
            'title': 'Renouvellements à venir',
            'message': f"{stats['titres_expirant_bientot']} titres expirent dans les 30 prochains jours",
            'action_url': '/titres/?filter=expiring_soon',
            'action_text': 'Planifier'
        })
        if stats['titres_expirant_bientot'] > 20:
            urgent_count += 1
    
    # Notification pour rapport mensuel
    notifications.append({
        'type': 'accent',
        'icon': 'info-circle',
        'title': 'Rapport mensuel',
        'message': 'Le rapport de juillet est prêt à être généré',
        'action_url': '/reports/generate/',
        'action_text': 'Générer'
    })
    
    context = {
        'stats': stats,
        'recent_activities': recent_activities,
        'notifications': notifications,
        'urgent_notifications_count': urgent_count,
        'now': timezone.now(),
    }
    
    return render(request, 'dashboard_overview.html', context)


@login_required
def telecommunications_titles_management(request):
    """Vue pour la gestion des titres."""
    user = request.user
    
    # Filtres de base selon le rôle
    if user.profile.role == 'operateur':
        titres = Titre.objects.filter(proprietaire=user)
    else:
        titres = Titre.objects.all()
    
    titres = titres.select_related('proprietaire__profile').order_by('-created_at')
    
    # Filtres de recherche
    search_query = request.GET.get('search', '')
    if search_query:
        titres = titres.filter(
            Q(numero_titre__icontains=search_query) |
            Q(entreprise_nom__icontains=search_query) |
            Q(proprietaire__profile__nom__icontains=search_query) |
            Q(proprietaire__profile__prenom__icontains=search_query)
        )
    
    # Filtre par type
    selected_type = request.GET.get('type', '')
    if selected_type:
        titres = titres.filter(type=selected_type)
    
    # Filtre par statut
    selected_status = request.GET.get('status', '')
    if selected_status:
        titres = titres.filter(status=selected_status)
    
    # Filtre par urgence
    filter_type = request.GET.get('filter', '')
    if filter_type == 'expired':
        titres = titres.filter(date_expiration__lt=date.today())
    elif filter_type == 'expiring_soon':
        date_limite = date.today() + timedelta(days=30)
        titres = titres.filter(
            date_expiration__lte=date_limite,
            date_expiration__gte=date.today(),
            status='approuve'
        )
    elif filter_type == 'active':
        titres = titres.filter(status='approuve')
    
    # Statistiques pour les cartes
    stats = {
        'total_actifs': titres.filter(status='approuve').count(),
        'total_expires': titres.filter(date_expiration__lt=date.today()).count(),
        'total_expirant_bientot': titres.filter(
            date_expiration__lte=date.today() + timedelta(days=30),
            date_expiration__gte=date.today(),
            status='approuve'
        ).count(),
        'total_demandes': titres.count(),
    }
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(titres, 25)  # 25 titres par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'titres': page_obj,
        'stats': stats,
        'search_query': search_query,
        'selected_type': selected_type,
        'selected_status': selected_status,
        'filter_type': filter_type,
        'type_choices': Titre.TYPE_CHOICES,
        'status_choices': Titre.STATUS_CHOICES,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
        'paginator': paginator,
    }
    
    return render(request, 'telecommunications_titles_management.html', context)


@login_required
def title_creation_and_edit_form(request):
    """Vue pour la création et modification des titres."""
    # Cette vue sera implémentée plus tard
    return render(request, 'title_creation_and_edit_form.html')


@login_required
def title_tracking_staff(request):
    """Vue pour le suivi des demandes (personnel)."""
    # Cette vue sera implémentée plus tard
    return render(request, 'title_tracking_staff.html')


@login_required
def user_management_administration(request):
    """Vue pour la gestion des utilisateurs (admin seulement)."""
    if request.user.profile.role != 'admin':
        messages.error(request, 'Accès non autorisé.')
        return redirect('dashboard_overview')
    
    # Cette vue sera implémentée plus tard
    return render(request, 'user_management_administration.html')


@login_required
def statistics_and_analytics_dashboard(request):
    """Vue pour les statistiques et analyses."""
    # Cette vue sera implémentée plus tard
    return render(request, 'statistics_and_analytics_dashboard.html')


@login_required
def impact_dashboard(request):
    """Vue pour le tableau de bord d'impact."""
    # Cette vue sera implémentée plus tard
    return render(request, 'impact_dashboard.html')


@login_required
def generate_report(request):
    """API endpoint pour générer des rapports."""
    if request.method == 'POST':
        try:
            # Logique de génération de rapport ici
            # Pour l'instant, on simule une génération réussie
            
            return JsonResponse({
                'success': True,
                'message': 'Rapport généré avec succès',
                'download_url': '/media/reports/rapport_titres.xlsx'  # URL fictive
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


@login_required
def import_excel(request):
    """API endpoint pour l'import Excel."""
    if request.method == 'POST':
        try:
            # Logique d'import Excel ici
            # Pour l'instant, on simule un import réussi
            
            return JsonResponse({
                'success': True,
                'data': {
                    'nombre_succes': 15,
                    'nombre_erreurs': 0
                }
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


# Fonctions utilitaires
def get_status_class(status):
    """Retourne la classe CSS pour un statut."""
    status_classes = {
        'approuve': 'success',
        'expire': 'error',
        'en_attente': 'warning',
        'en_cours': 'accent',
        'rejete': 'error'
    }
    return status_classes.get(status, 'secondary')


def get_action_icon(action):
    """Retourne l'icône pour une action."""
    action_icons = {
        'creation': 'plus',
        'modification': 'edit',
        'renouvellement': 'sync-alt',
        'suspension': 'pause',
        'reactivation': 'play',
        'expiration': 'exclamation-triangle'
    }
    return action_icons.get(action, 'info-circle')


def get_action_icon_color(action):
    """Retourne la couleur de l'icône pour une action."""
    action_colors = {
        'creation': 'success',
        'modification': 'warning',
        'renouvellement': 'accent',
        'suspension': 'error',
        'reactivation': 'success',
        'expiration': 'error'
    }
    return action_colors.get(action, 'secondary')