# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard and main pages
    path('dashboard/', views.dashboard_overview, name='dashboard_overview'),
    path('titres/', views.telecommunications_titles_management, name='telecommunications_titles_management'),
    path('titres/nouveau/', views.title_creation_and_edit_form, name='title_creation_and_edit_form'),
    path('suivi/', views.title_tracking_staff, name='title_tracking_staff'),
    path('utilisateurs/', views.user_management_administration, name='user_management_administration'),
    path('statistiques/', views.statistics_and_analytics_dashboard, name='statistics_and_analytics_dashboard'),
    path('impact/', views.impact_dashboard, name='impact_dashboard'),
    
    # API endpoints
    path('reports/generate/', views.generate_report, name='generate_report'),
    path('import-excel/', views.import_excel, name='import_excel'),
]