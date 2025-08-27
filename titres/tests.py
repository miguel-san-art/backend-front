# titres/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, timedelta
from .models import Titre, RedevanceTitre, HistoriqueTitre
from users.models import Profile

User = get_user_model()

class TitreModelTest(TestCase):
    """Tests pour le modèle Titre."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        Profile.objects.create(
            user=self.user,
            nom='Test',
            prenom='User',
            role='operateur'
        )
        
    def test_titre_creation(self):
        """Test de création d'un titre."""
        titre = Titre.objects.create(
            type='licence_type_1',
            proprietaire=self.user,
            entreprise_nom='Test Company',
            date_emission=date.today(),
            date_expiration=date.today() + timedelta(days=365),
            duree_ans=1
        )
        
        self.assertTrue(titre.numero_titre)  # Numéro généré automatiquement
        self.assertEqual(titre.redevance_annuelle, 500000)  # Redevance calculée
        self.assertEqual(titre.status, 'en_attente')
    
    def test_titre_expiration(self):
        """Test de vérification d'expiration."""
        titre = Titre.objects.create(
            type='licence_type_1',
            proprietaire=self.user,
            entreprise_nom='Test Company',
            date_emission=date.today() - timedelta(days=400),
            date_expiration=date.today() - timedelta(days=1),
            duree_ans=1
        )
        
        self.assertTrue(titre.is_expired)
        self.assertFalse(titre.is_expiring_soon)
    
    def test_titre_renewal(self):
        """Test de renouvellement d'un titre."""
        titre = Titre.objects.create(
            type='licence_type_1',
            proprietaire=self.user,
            entreprise_nom='Test Company',
            date_emission=date.today() - timedelta(days=300),
            date_expiration=date.today() + timedelta(days=65),
            duree_ans=1
        )
        
        titre.renew(2)
        
        self.assertEqual(titre.date_emission, date.today())
        self.assertEqual(titre.duree_ans, 2)
        self.assertEqual(titre.status, 'approuve')


class TitreAPITest(APITestCase):
    """Tests pour l'API des titres."""
    
    def setUp(self):
        # Créer un admin
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123'
        )
        Profile.objects.create(
            user=self.admin_user,
            nom='Admin',
            prenom='User',
            role='admin'
        )
        
        # Créer un opérateur
        self.operateur_user = User.objects.create_user(
            email='operateur@example.com',
            password='operpass123'
        )
        Profile.objects.create(
            user=self.operateur_user,
            nom='Operateur',
            prenom='User',
            role='operateur'
        )
        
        # Créer un titre de test
        self.titre = Titre.objects.create(
            type='licence_type_1',
            proprietaire=self.operateur_user,
            entreprise_nom='Test Company',
            date_emission=date.today(),
            date_expiration=date.today() + timedelta(days=365),
            duree_ans=1
        )
    
    def test_admin_can_create_titre(self):
        """Test qu'un admin peut créer un titre."""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'type': 'licence_type_2',
            'proprietaire_email': 'operateur@example.com',
            'entreprise_nom': 'New Company',
            'date_emission': date.today().isoformat(),
            'date_expiration': (date.today() + timedelta(days=730)).isoformat(),
            'duree_ans': 2,
            'description': 'Test titre'
        }
        
        response = self.client.post('/api/titres/titres/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_operateur_cannot_create_titre(self):
        """Test qu'un opérateur ne peut pas créer un titre."""
        self.client.force_authenticate(user=self.operateur_user)
        
        data = {
            'type': 'licence_type_2',
            'proprietaire_email': 'operateur@example.com',
            'entreprise_nom': 'New Company',
            'date_emission': date.today().isoformat(),
            'date_expiration': (date.today() + timedelta(days=730)).isoformat(),
            'duree_ans': 2
        }
        
        response = self.client.post('/api/titres/titres/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_operateur_can_view_own_titres(self):
        """Test qu'un opérateur peut voir ses propres titres."""
        self.client.force_authenticate(user=self.operateur_user)
        
        response = self.client.get('/api/titres/titres/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_titre_renewal(self):
        """Test de renouvellement d'un titre via l'API."""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'duree_ans': 3,
            'commentaire': 'Renouvellement test'
        }
        
        response = self.client.post(f'/api/titres/titres/{self.titre.id}/renew/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérifier que le titre a été renouvelé
        self.titre.refresh_from_db()
        self.assertEqual(self.titre.duree_ans, 3)
        self.assertEqual(self.titre.status, 'approuve')
    
    def test_titre_statistics(self):
        """Test des statistiques des titres."""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/titres/titres/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        self.assertIn('total_titres', data)
        self.assertIn('titres_actifs', data)
        self.assertIn('par_type', data)
        self.assertIn('par_status', data)


class RedevanceModelTest(TestCase):
    """Tests pour le modèle RedevanceTitre."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        Profile.objects.create(
            user=self.user,
            nom='Test',
            prenom='User',
            role='operateur'
        )
        
        self.titre = Titre.objects.create(
            type='licence_type_1',
            proprietaire=self.user,
            entreprise_nom='Test Company',
            date_emission=date.today(),
            date_expiration=date.today() + timedelta(days=365),
            duree_ans=1
        )
    
    def test_redevance_creation(self):
        """Test de création d'une redevance."""
        redevance = RedevanceTitre.objects.create(
            titre=self.titre,
            annee=2024,
            montant=500000,
            date_echeance=date(2024, 12, 31)
        )
        
        self.assertEqual(redevance.status_paiement, 'en_attente')
        self.assertFalse(redevance.is_overdue)
    
    def test_redevance_overdue(self):
        """Test de détection des redevances en retard."""
        redevance = RedevanceTitre.objects.create(
            titre=self.titre,
            annee=2023,
            montant=500000,
            date_echeance=date.today() - timedelta(days=30)
        )
        
        self.assertTrue(redevance.is_overdue)
        