# requests_management/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DemandeViewSet, DocumentViewSet, CommentaireDemandeViewSet

router = DefaultRouter()
router.register(r'demandes', DemandeViewSet, basename='demande')
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'commentaires', CommentaireDemandeViewSet, basename='commentaire')

urlpatterns = [
    path('', include(router.urls)),
]
