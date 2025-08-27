# titres/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TitreViewSet, RedevanceTitreViewSet, HistoriqueTitreViewSet

router = DefaultRouter()
router.register(r'titres', TitreViewSet)
router.register(r'redevances', RedevanceTitreViewSet, basename='redevance')
router.register(r'historique', HistoriqueTitreViewSet, basename='historique')

urlpatterns = [
    path('', include(router.urls)),
]