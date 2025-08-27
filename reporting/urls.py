# reporting/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'reports', views.ReportViewSet, basename='report')
router.register(r'dashboards', views.DashboardViewSet, basename='dashboard')
router.register(r'audit-logs', views.AuditLogViewSet, basename='auditlog')


urlpatterns = [
    # API Routes
    path('api/', include(router.urls)),
    
    # Dashboard Views
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('api/statistics/', views.get_statistics, name='statistics'),
    
    # Report Generation
    path('api/reports/generate-titles/', 
         views.ReportViewSet.as_view({'post': 'generate_titles_report'}), 
         name='generate-titles-report'),
    path('api/reports/generate-requests/', 
         views.ReportViewSet.as_view({'post': 'generate_requests_report'}), 
         name='generate-requests-report'),
]
