# notifications/urls.py
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Notifications utilisateur
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),
    path('<int:pk>/read/', views.mark_notification_read, name='mark-read'),
    path('mark-all-read/', views.mark_all_notifications_read, name='mark-all-read'),
    path('counts/', views.notification_counts, name='notification-counts'),
    
    # Préférences utilisateur
    path('preferences/', views.NotificationPreferenceView.as_view(), name='notification-preferences'),
    
    # Templates d'email (admin)
    path('email-templates/', views.EmailTemplateListView.as_view(), name='email-template-list'),
    path('email-templates/<int:pk>/', views.EmailTemplateDetailView.as_view(), name='email-template-detail'),
    path('email-templates/<int:pk>/test/', views.test_email_template, name='test-email-template'),
    
    # Actions admin
    path('bulk-send/', views.send_bulk_notification, name='bulk-notification'),
]
