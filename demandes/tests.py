# gestion_demandes/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, timedelta
import tempfile
import json

from .models import Demande, Document, HistoriqueDemande, CommentaireDemande
from users.models import Profile

User = get_user_model()

class DemandeModelTest(TestCase):
    """Tests pour le modèle Demande."""
    
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
    
    def test_create_demande(self):
        """Test de création d'une demande."""
        demande = Demande.objects.create(
            demandeur=self.user,
            entreprise='Test Company',
            email_contact='contact@test.com',
            type_titre='licence_type_1',
            description='Test demande'
        )
        
        self.assertIsNotNone(demande.numero_dossier)
        self.assertTrue(demande.numero_dossier.startswith('DEM-LT1-'))
        self.assertEqual(demande.status, 'soumise')
        self.assertEqual(demande.days_since_submission, 0)
    
    def test_numero_dossier_generation(self):
        """Test de génération automatique du numéro de dossier."""
        # Première demande
        demande1 = Demande.objects.create(
            demandeur=self.user,
            entreprise='Test Company 1',
            email_contact='contact1@test.com',
            type_titre='licence_type_1'
        )
        
        # Deuxième demande du même type
        demande2 = Demande.objects.create(
            demandeur=self.user,
            entreprise='Test Company 2',
            email_contact='contact2@test.com',
            type_titre='licence_type_1'
        )
        
        # Vérifier que les numéros sont différents et séquentiels
        self.assertNotEqual(demande1.numero_dossier, demande2.numero_dossier)
        
        # Extraire les numéros séquentiels
        num1 = int(demande1.numero_dossier.split('-')[-1])
        num2 = int(demande2.numero_dossier.split('-')[-1])
        self.assertEqual(num2, num1 + 1)
    
    def test_is_overdue_property(self):
        """Test de la propriété is_overdue."""
        # Demande récente
        demande_recente = Demande.objects.create(
            demandeur=self.user,
            entreprise='Recent Company',
            email_contact='recent@test.com',
            type_titre='licence_type_1'
        )
        self.assertFalse(demande_recente.is_overdue)
        
        # Demande ancienne
        demande_ancienne = Demande.objects.create(
            demandeur=self.user,
            entreprise='Old Company',
            email_contact='old@test.com',
            type_titre='licence_type_1'
        )
        # Modifier manuellement la date de soumission
        demande_ancienne.date_soumission = date.today() - timedelta(days=35)
        demande_ancienne.save()
        
        self.assertTrue(demande_ancienne.is_overdue)

class DocumentModelTest(TestCase):
    """Tests pour le modèle Document."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.demande = Demande.objects.create(
            demandeur=self.user,
            entreprise='Test Company',
            email_contact='contact@test.com',
            type_titre='licence_type_1'
        )
    
    def test_create_document(self):
        """Test de création d'un document."""
        # Créer un fichier temporaire
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        document = Document.objects.create(
            nom_fichier='test.pdf',
            type_document='justificatif_entreprise',
            fichier=test_file,
            demande=self.demande,
            uploade_par=self.user,
            description='Document de test'
        )
        
        self.assertEqual(document.nom_fichier, 'test.pdf')
        self.assertEqual(document.version, 1)
        self.assertTrue(document.est_actif)
        self.assertIsNotNone(document.hash_fichier)

class DemandeAPITest(APITestCase):
    """Tests pour l'API des demandes."""
    
    def setUp(self):
        # Créer des utilisateurs avec différents rôles
        self.operateur = User.objects.create_user(
            email='operateur@test.com',
            password='testpass123'
        )
        Profile.objects.create(
            user=self.operateur,
            nom='Opérateur',
            prenom='Test',
            role='operateur'
        )
        
        self.personnel = User.objects.create_user(
            email='personnel@test.com',
            password='testpass123'
        )
        Profile.objects.create(
            user=self.personnel,
            nom='Personnel',
            prenom='Test',
            role='personnel'
        )
        
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
        Profile.objects.create(
            user=self.admin,
            nom='Admin',
            prenom='Test',
            role='admin'
        )
    
    def test_create_demande_operateur(self):
        """Test de création de demande par un opérateur."""
        self.client.force_authenticate(user=self.operateur)
        
        data = {
            'entreprise': 'Ma Société',
            'email_contact': 'contact@masociete.com',
            'telephone': '123456789',
            'type_titre': 'licence_type_1',
            'description': 'Demande de licence',
            'motivations': 'Expansion des activités'
        }
        
        response = self.client.post('/api/demandes/demandes/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        demande = Demande.objects.get(id=response.data['id'])
        self.assertEqual(demande.demandeur, self.operateur)
        self.assertEqual(demande.status, 'soumise')
        self.assertIsNotNone(demande.numero_dossier)
    
    def test_list_demandes_permissions(self):
        """Test des permissions pour lister les demandes."""
        # Créer une demande
        demande = Demande.objects.create(
            demandeur=self.operateur,
            entreprise='Test Company',
            email_contact='test@test.com',
            type_titre='licence_type_1'
        )
        
        # Test opérateur - voit seulement ses demandes
        self.client.force_authenticate(user=self.operateur)
        response = self.client.get('/api/demandes/demandes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Test personnel - voit toutes les demandes
        self.client.force_authenticate(user=self.personnel)
        response = self.client.get('/api/demandes/demandes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_update_status_permissions(self):
        """Test des permissions pour changer le statut."""
        demande = Demande.objects.create(
            demandeur=self.operateur,
            entreprise='Test Company',
            email_contact='test@test.com',
            type_titre='licence_type_1'
        )
        
        # Opérateur ne peut pas changer le statut
        self.client.force_authenticate(user=self.operateur)
        response = self.client.post(f'/api/demandes/demandes/{demande.id}/update_status/', {
            'status': 'en_examen'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Personnel peut changer le statut
        self.client.force_authenticate(user=self.personnel)
        response = self.client.post(f'/api/demandes/demandes/{demande.id}/update_status/', {
            'status': 'en_examen',
            'commentaires_admin': 'Mise en examen de la demande'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        demande.refresh_from_db()
        self.assertEqual(demande.status, 'en_examen')
    
    def test_dashboard_operateur(self):
        """Test du tableau de bord pour un opérateur."""
        # Créer quelques demandes pour l'opérateur
        for i in range(3):
            Demande.objects.create(
                demandeur=self.operateur,
                entreprise=f'Company {i}',
                email_contact=f'test{i}@test.com',
                type_titre='licence_type_1'
            )
        
        self.client.force_authenticate(user=self.operateur)
        response = self.client.get('/api/demandes/demandes/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        self.assertEqual(data['mes_demandes_total'], 3)
        self.assertEqual(data['mes_demandes_soumises'], 3)
        self.assertEqual(len(data['dernières_demandes']), 3)
    
    def test_statistics_admin(self):
        """Test des statistiques pour un admin."""
        # Créer des demandes avec différents statuts
        Demande.objects.create(
            demandeur=self.operateur,
            entreprise='Company 1',
            email_contact='test1@test.com',
            type_titre='licence_type_1',
            status='soumise'
        )
        
        demande2 = Demande.objects.create(
            demandeur=self.operateur,
            entreprise='Company 2',
            email_contact='test2@test.com',
            type_titre='licence_type_2',
            status='approuvee'
        )
        demande2.date_traitement = date.today()
        demande2.save()
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/demandes/demandes/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        self.assertEqual(data['total_demandes'], 2)
        self.assertEqual(data['demandes_soumises'], 1)
        self.assertEqual(data['demandes_approuvees'], 1)

class DocumentAPITest(APITestCase):
    """Tests pour l'API des documents."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@test.com',
            password='testpass123'
        )
        Profile.objects.create(
            user=self.user,
            nom='Test',
            prenom='User',
            role='operateur'
        )
        
        self.demande = Demande.objects.create(
            demandeur=self.user,
            entreprise='Test Company',
            email_contact='test@test.com',
            type_titre='licence_type_1'
        )
    
    def test_upload_document(self):
        """Test d'upload de document."""
        self.client.force_authenticate(user=self.user)
        
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        data = {
            'demande_id': str(self.demande.id),
            'nom_fichier': 'test.pdf',
            'type_document': 'justificatif_entreprise',
            'fichier': test_file,
            'description': 'Document de test'
        }
        
        response = self.client.post('/api/demandes/documents/upload/', data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        document = Document.objects.get(id=response.data['id'])
        self.assertEqual(document.demande, self.demande)
        self.assertEqual(document.nom_fichier, 'test.pdf')
        