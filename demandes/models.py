# demandes/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
import uuid
from datetime import date

User = get_user_model()

class Demande(models.Model):
    """Modèle pour les demandes de titres de télécommunications."""
    
    TYPE_TITRE_CHOICES = [
        ('licence_type_1', 'Licence de type 1'),
        ('licence_type_2', 'Licence de type 2'),
        ('agrement_vendeurs', 'Agrément vendeurs'),
        ('agrement_installateurs', 'Agrément installateurs'),
        ('concessions', 'Concessions'),
        ('recepisse', 'Récépissé'),
    ]
    
    STATUS_CHOICES = [
        ('soumise', 'Soumise'),
        ('en_examen', 'En examen'),
        ('approuvee', 'Approuvée'),
        ('rejetee', 'Rejetée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    demandeur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demandes')
    entreprise = models.CharField(max_length=255, help_text="Nom de l'entreprise demandeuse")
    email_contact = models.EmailField(help_text="Email de contact pour la demande")
    telephone = models.CharField(max_length=20, blank=True, null=True, help_text="Numéro de téléphone")
    adresse = models.TextField(blank=True, null=True, help_text="Adresse complète")
    
    # Informations sur le titre demandé
    type_titre = models.CharField(max_length=50, choices=TYPE_TITRE_CHOICES)
    description = models.TextField(blank=True, null=True, help_text="Description de la demande")
    motivations = models.TextField(blank=True, null=True, help_text="Motivations de la demande")
    
    # Workflow et suivi
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='soumise')
    numero_dossier = models.CharField(max_length=100, unique=True, blank=True, null=True, 
                                     help_text="Numéro unique du dossier")
    date_soumission = models.DateField(auto_now_add=True)
    date_traitement = models.DateField(blank=True, null=True, help_text="Date de traitement final")
    
    # Commentaires administratifs
    commentaires_admin = models.TextField(blank=True, null=True, 
                                        help_text="Commentaires du personnel administratif")
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='demandes_assignees', 
                               help_text="Personnel assigné au traitement")
    
    # Documents associés (URLs stockées en JSON)
    documents_urls = models.JSONField(default=list, help_text="URLs des documents associés")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Demande"
        verbose_name_plural = "Demandes"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['numero_dossier']),
            models.Index(fields=['status']),
            models.Index(fields=['type_titre']),
            models.Index(fields=['demandeur']),
            models.Index(fields=['date_soumission']),
        ]
    
    def __str__(self):
        return f"{self.numero_dossier or self.id} - {self.entreprise} - {self.get_type_titre_display()}"
    
    def save(self, *args, **kwargs):
        # Générer automatiquement le numéro de dossier si pas fourni
        if not self.numero_dossier:
            self.numero_dossier = self.generate_numero_dossier()
        
        super().save(*args, **kwargs)
    
    def generate_numero_dossier(self):
        """Génère automatiquement un numéro de dossier unique."""
        year = date.today().year
        type_code = self.get_type_code()
        
        # Trouver le dernier numéro pour ce type et cette année
        last_demande = Demande.objects.filter(
            type_titre=self.type_titre,
            numero_dossier__startswith=f"DEM-{type_code}-{year}"
        ).order_by('-numero_dossier').first()
        
        if last_demande and last_demande.numero_dossier:
            # Extraire le numéro séquentiel
            try:
                last_num = int(last_demande.numero_dossier.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
        
        return f"DEM-{type_code}-{year}-{next_num:04d}"
    
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
        return type_codes.get(self.type_titre, 'UNK')
    
    @property
    def days_since_submission(self):
        """Nombre de jours depuis la soumission."""
        if self.date_soumission is None:
            return None
        return (date.today() - self.date_soumission).days
    
    @property
    def is_overdue(self):
        """Vérifie si la demande est en retard (plus de 30 jours sans traitement)."""
        days = self.days_since_submission
        if days is None:
            return False  # Sécurité pour les objets non encore enregistrés
        return days > 30 and self.status in ['soumise', 'en_examen']


class HistoriqueDemande(models.Model):
    """Historique des modifications des demandes."""
    
    ACTION_CHOICES = [
        ('soumission', 'Soumission'),
        ('assignation', 'Assignation'),
        ('mise_en_examen', 'Mise en examen'),
        ('commentaire', 'Commentaire ajouté'),
        ('document_ajoute', 'Document ajouté'),
        ('document_supprime', 'Document supprimé'),
        ('approbation', 'Approbation'),
        ('rejet', 'Rejet'),
        ('modification', 'Modification'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    demande = models.ForeignKey(Demande, on_delete=models.CASCADE, related_name='historique')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    commentaire = models.TextField(blank=True, null=True)
    ancien_status = models.CharField(max_length=20, blank=True, null=True)
    nouveau_status = models.CharField(max_length=20, blank=True, null=True)
    date_action = models.DateTimeField(auto_now_add=True)
    donnees_modifiees = models.JSONField(default=dict, help_text="Données qui ont été modifiées")
    
    class Meta:
        verbose_name = "Historique Demande"
        verbose_name_plural = "Historiques Demandes"
        ordering = ['-date_action']
    
    def __str__(self):
        demande_ref = self.demande.numero_dossier or str(self.demande.id)[:8]
        return f"{demande_ref} - {self.get_action_display()} - {self.date_action}"


class Document(models.Model):
    """Modèle pour les documents associés aux demandes et titres."""
    
    TYPE_DOCUMENT_CHOICES = [
        ('justificatif_entreprise', 'Justificatif d\'entreprise'),
        ('plan_affaires', 'Plan d\'affaires'),
        ('etude_technique', 'Étude technique'),
        ('garantie_financiere', 'Garantie financière'),
        ('autorisation_prealable', 'Autorisation préalable'),
        ('certificat_conformite', 'Certificat de conformité'),
        ('autre', 'Autre document'),
    ]
    
    ALLOWED_EXTENSIONS = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'zip', 'rar']
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom_fichier = models.CharField(max_length=255, help_text="Nom original du fichier")
    type_document = models.CharField(max_length=50, choices=TYPE_DOCUMENT_CHOICES)
    fichier = models.FileField(
        upload_to='documents/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_EXTENSIONS)],
        help_text="Fichier à télécharger"
    )
    taille_fichier = models.PositiveIntegerField(help_text="Taille du fichier en bytes")
    hash_fichier = models.CharField(max_length=64, help_text="Hash SHA-256 du fichier")
    
    # Relations
    demande = models.ForeignKey(Demande, on_delete=models.CASCADE, null=True, blank=True,
                              related_name='documents')
    titre = models.ForeignKey('titres.Titre', on_delete=models.CASCADE, null=True, blank=True,
                             related_name='documents')
    
    # Métadonnées
    uploade_par = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True, help_text="Description du document")
    version = models.PositiveIntegerField(default=1, help_text="Version du document")
    est_actif = models.BooleanField(default=True, help_text="Document actif ou archivé")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['demande', 'type_document']),
            models.Index(fields=['titre', 'type_document']),
            models.Index(fields=['hash_fichier']),
        ]
    
    def __str__(self):
        return f"{self.nom_fichier} - {self.get_type_document_display()}"
    
    @property
    def taille_fichier_readable(self):
        """Retourne la taille du fichier en format lisible."""
        if self.taille_fichier is None:
            return "0 B"  # ou "" selon ce que tu préfères
        taille = float(self.taille_fichier)  # éviter de modifier self.taille_fichier
        for unit in ['B', 'KB', 'MB', 'GB']:
            if taille < 1024.0:
                return f"{taille:.1f} {unit}"
            taille /= 1024.0
        return f"{taille:.1f} TB"
    
    def save(self, *args, **kwargs):
        # Calculer la taille du fichier
        if self.fichier and hasattr(self.fichier, 'size'):
            self.taille_fichier = self.fichier.size
        
        # Calculer le hash du fichier
        if self.fichier:
            import hashlib
            self.fichier.seek(0)
            file_hash = hashlib.sha256()
            for chunk in iter(lambda: self.fichier.read(4096), b""):
                file_hash.update(chunk)
            self.hash_fichier = file_hash.hexdigest()
            self.fichier.seek(0)
        
        super().save(*args, **kwargs)


class CommentaireDemande(models.Model):
    """Modèle pour les commentaires sur les demandes."""
    
    TYPE_COMMENTAIRE_CHOICES = [
        ('public', 'Public'),
        ('interne', 'Interne'),
        ('systeme', 'Système'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    demande = models.ForeignKey(Demande, on_delete=models.CASCADE, related_name='commentaires')
    auteur = models.ForeignKey(User, on_delete=models.CASCADE)
    type_commentaire = models.CharField(max_length=20, choices=TYPE_COMMENTAIRE_CHOICES, default='public')
    contenu = models.TextField(help_text="Contenu du commentaire")
    est_resolu = models.BooleanField(default=False, help_text="Commentaire résolu ou non")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Commentaire Demande"
        verbose_name_plural = "Commentaires Demandes"
        ordering = ['-created_at']
    
    def __str__(self):
        demande_ref = self.demande.numero_dossier or str(self.demande.id)[:8]
        return f"Commentaire sur {demande_ref} par {self.auteur.email}"
    