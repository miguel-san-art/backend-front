# titres/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
import uuid
from datetime import date, timedelta

User = get_user_model()

class Titre(models.Model):
    """Modèle pour les titres de télécommunications."""
    
    TYPE_CHOICES = [
        ('licence_type_1', 'Licence de type 1'),
        ('licence_type_2', 'Licence de type 2'),
        ('agrement_vendeurs', 'Agrément vendeurs'),
        ('agrement_installateurs', 'Agrément installateurs'),
        ('concessions', 'Concessions'),
        ('recepisse', 'Récépissé'),
    ]
    
    STATUS_CHOICES = [
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('approuve', 'Approuvé'),
        ('rejete', 'Rejeté'),
        ('expire', 'Expiré'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_titre = models.CharField(max_length=100, unique=True, help_text="Numéro unique du titre")
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    proprietaire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='titres')
    entreprise_nom = models.CharField(max_length=255, help_text="Nom de l'entreprise propriétaire")
    date_emission = models.DateField(help_text="Date d'émission du titre")
    date_expiration = models.DateField(help_text="Date d'expiration du titre")
    duree_ans = models.PositiveIntegerField(validators=[MinValueValidator(1)], help_text="Durée en années")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='en_attente')
    description = models.TextField(blank=True, null=True, help_text="Description du titre")
    conditions_specifiques = models.JSONField(default=list, help_text="Conditions spécifiques du titre")
    redevance_annuelle = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Redevance annuelle en FCFA")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Titre"
        verbose_name_plural = "Titres"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['numero_titre']),
            models.Index(fields=['type']),
            models.Index(fields=['status']),
            models.Index(fields=['date_expiration']),
            models.Index(fields=['proprietaire']),
        ]
    
    def __str__(self):
        return f"{self.numero_titre} - {self.get_type_display()}"
    
    @property
    def is_expired(self):
        """Vérifie si le titre est expiré."""
        return date.today() > self.date_expiration
    
    @property
    def days_until_expiration(self):
        """Nombre de jours avant expiration."""
        return (self.date_expiration - date.today()).days
    
    @property
    def is_expiring_soon(self):
        """Vérifie si le titre expire dans les 30 jours."""
        return 0 <= self.days_until_expiration <= 30
    
    def save(self, *args, **kwargs):
        # Générer automatiquement le numéro de titre si pas fourni
        if not self.numero_titre:
            self.numero_titre = self.generate_numero_titre()
        
        # Calculer automatiquement la redevance
        self.redevance_annuelle = self.calculate_redevance()
        
        # Mettre à jour le statut si expiré
        if self.is_expired and self.status != 'expire':
            self.status = 'expire'
        
        super().save(*args, **kwargs)
    
    def generate_numero_titre(self):
        """Génère automatiquement un numéro de titre unique."""
        year = date.today().year
        type_code = self.get_type_code()
        
        # Trouver le dernier numéro pour ce type et cette année
        last_titre = Titre.objects.filter(
            type=self.type,
            numero_titre__startswith=f"{type_code}-{year}"
        ).order_by('-numero_titre').first()
        
        if last_titre:
            # Extraire le numéro séquentiel du dernier titre
            last_num = int(last_titre.numero_titre.split('-')[-1])
            next_num = last_num + 1
        else:
            next_num = 1
        
        return f"{type_code}-{year}-{next_num:04d}"
    
    def get_type_code(self):
        """Retourne le code du type de titre."""
        type_codes = {
            'licence_type_1': 'LT1',
            'licence_type_2': 'LT2',
            'agrement_vendeurs': 'AGV',
            'agrement_installateurs': 'AGI',
            'concessions': 'CON',
            'recepisse': 'REC',
        }
        return type_codes.get(self.type, 'UNK')
    
    def calculate_redevance(self):
        """Calcule automatiquement la redevance selon le type de titre."""
        redevances = {
            'licence_type_1': 500000,      # 500,000 FCFA
            'licence_type_2': 300000,      # 300,000 FCFA
            'agrement_vendeurs': 100000,   # 100,000 FCFA
            'agrement_installateurs': 150000, # 150,000 FCFA
            'concessions': 1000000,        # 1,000,000 FCFA
            'recepisse': 50000,           # 50,000 FCFA
        }
        return redevances.get(self.type, 0)
    
    def renew(self, duree_ans=None):
        """Renouvelle le titre pour une durée donnée."""
        if duree_ans is None:
            duree_ans = self.duree_ans
        
        self.date_emission = date.today()
        self.date_expiration = date.today() + timedelta(days=duree_ans * 365)
        self.duree_ans = duree_ans
        self.status = 'approuve'
        self.save()


class HistoriqueTitre(models.Model):
    """Historique des modifications des titres."""
    
    ACTION_CHOICES = [
        ('creation', 'Création'),
        ('modification', 'Modification'),
        ('renouvellement', 'Renouvellement'),
        ('suspension', 'Suspension'),
        ('reactivation', 'Réactivation'),
        ('expiration', 'Expiration'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titre = models.ForeignKey(Titre, on_delete=models.CASCADE, related_name='historique')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    commentaire = models.TextField(blank=True, null=True)
    ancien_status = models.CharField(max_length=20, blank=True, null=True)
    nouveau_status = models.CharField(max_length=20, blank=True, null=True)
    date_action = models.DateTimeField(auto_now_add=True)
    donnees_modifiees = models.JSONField(default=dict, help_text="Données qui ont été modifiées")
    
    class Meta:
        verbose_name = "Historique Titre"
        verbose_name_plural = "Historiques Titres"
        ordering = ['-date_action']
    
    def __str__(self):
        return f"{self.titre.numero_titre} - {self.get_action_display()} - {self.date_action}"


class RedevanceTitre(models.Model):
    """Modèle pour le suivi des paiements de redevances."""
    
    STATUS_PAIEMENT_CHOICES = [
        ('en_attente', 'En attente'),
        ('paye', 'Payé'),
        ('en_retard', 'En retard'),
        ('annule', 'Annulé'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titre = models.ForeignKey(Titre, on_delete=models.CASCADE, related_name='redevances')
    annee = models.PositiveIntegerField(help_text="Année de la redevance")
    montant = models.DecimalField(max_digits=12, decimal_places=2, help_text="Montant de la redevance")
    date_echeance = models.DateField(help_text="Date d'échéance du paiement")
    date_paiement = models.DateField(null=True, blank=True, help_text="Date effective du paiement")
    status_paiement = models.CharField(max_length=20, choices=STATUS_PAIEMENT_CHOICES, default='en_attente')
    reference_paiement = models.CharField(max_length=100, blank=True, null=True, help_text="Référence du paiement")
    commentaires = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['titre', 'annee']
        verbose_name = "Redevance Titre"
        verbose_name_plural = "Redevances Titres"
        ordering = ['-annee', '-date_echeance']
    
    def __str__(self):
        return f"{self.titre.numero_titre} - {self.annee} - {self.montant} FCFA"
    
    @property
    def is_overdue(self):
        """Vérifie si la redevance est en retard."""
        return date.today() > self.date_echeance and self.status_paiement != 'paye'
    
    def save(self, *args, **kwargs):
        # Mettre à jour le statut automatiquement
        if self.is_overdue and self.status_paiement == 'en_attente':
            self.status_paiement = 'en_retard'
        super().save(*args, **kwargs)
        