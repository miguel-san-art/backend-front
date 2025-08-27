/**
 * Module d'intégration API pour ART Telecom Titles Manager
 * Gère toutes les communications avec le backend Django
 */

// Configuration de l'API
const API_CONFIG = {
    BASE_URL: 'http://localhost:8000/api/',
    TITLES_ENDPOINT: 'titles/',
    IMPORT_ENDPOINT: 'titles/import-excel/',
    STATS_ENDPOINT: 'titles/dashboard-stats/',
    HEADERS: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
    }
};

/**
 * Classe principale pour les appels API
 */
class TitlesAPI {
    constructor() {
        this.baseUrl = API_CONFIG.BASE_URL;
    }

    /**
     * Méthode générique pour les requêtes HTTP
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const defaultOptions = {
            headers: API_CONFIG.HEADERS,
            ...options
        };

        try {
            const response = await fetch(url, defaultOptions);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `HTTP Error: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    }

    /**
     * Récupère tous les titres avec filtres optionnels
     */
    async getTitles(filters = {}) {
        const queryParams = new URLSearchParams(filters).toString();
        const endpoint = queryParams ? `${API_CONFIG.TITLES_ENDPOINT}?${queryParams}` : API_CONFIG.TITLES_ENDPOINT;
        
        return await this.request(endpoint);
    }

    /**
     * Récupère un titre spécifique par ID
     */
    async getTitle(id) {
        return await this.request(`${API_CONFIG.TITLES_ENDPOINT}${id}/`);
    }

    /**
     * Crée un nouveau titre
     */
    async createTitle(titleData) {
        return await this.request(API_CONFIG.TITLES_ENDPOINT, {
            method: 'POST',
            body: JSON.stringify(titleData)
        });
    }

    /**
     * Met à jour un titre existant
     */
    async updateTitle(id, titleData) {
        return await this.request(`${API_CONFIG.TITLES_ENDPOINT}${id}/`, {
            method: 'PUT',
            body: JSON.stringify(titleData)
        });
    }

    /**
     * Supprime un titre
     */
    async deleteTitle(id) {
        return await this.request(`${API_CONFIG.TITLES_ENDPOINT}${id}/`, {
            method: 'DELETE'
        });
    }

    /**
     * Récupère les titres expirés
     */
    async getExpiredTitles() {
        return await this.request(`${API_CONFIG.TITLES_ENDPOINT}expired/`);
    }

    /**
     * Récupère les titres expirant bientôt
     */
    async getExpiringSoonTitles() {
        return await this.request(`${API_CONFIG.TITLES_ENDPOINT}expiring_soon/`);
    }

    /**
     * Récupère les statistiques par région
     */
    async getStatsByRegion() {
        return await this.request(`${API_CONFIG.TITLES_ENDPOINT}by_region/`);
    }

    /**
     * Récupère les statistiques par type
     */
    async getStatsByType() {
        return await this.request(`${API_CONFIG.TITLES_ENDPOINT}by_type/`);
    }

    /**
     * Récupère les statistiques du dashboard
     */
    async getDashboardStats() {
        return await this.request(API_CONFIG.STATS_ENDPOINT);
    }

    /**
     * Importe un fichier Excel
     */
    async importExcel(file, utilisateur = 'Frontend User') {
        const formData = new FormData();
        formData.append('fichier', file);
        formData.append('utilisateur', utilisateur);

        const response = await fetch(`${this.baseUrl}${API_CONFIG.IMPORT_ENDPOINT}`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || 'Erreur lors de l\'import');
        }

        return await response.json();
    }

    /**
     * Renouvelle un titre
     */
    async renewTitle(id) {
        return await this.request(`${API_CONFIG.TITLES_ENDPOINT}${id}/renew/`, {
            method: 'POST'
        });
    }
}

/**
 * Instance globale de l'API
 */
const titlesAPI = new TitlesAPI();

/**
 * Gestionnaire d'erreurs global
 */
function handleAPIError(error, context = '') {
    console.error(`Erreur API ${context}:`, error);
    
    // Afficher une notification à l'utilisateur
    showNotification('error', `Erreur: ${error.message}`);
}

/**
 * Fonction utilitaire pour afficher des notifications
 */
function showNotification(type, message) {
    // Créer une notification temporaire
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 px-6 py-3 rounded-lg shadow-lg ${
        type === 'success' ? 'bg-green-500 text-white' :
        type === 'error' ? 'bg-red-500 text-white' :
        type === 'warning' ? 'bg-yellow-500 text-black' :
        'bg-blue-500 text-white'
    }`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Supprimer après 5 secondes
    setTimeout(() => {
        if (document.body.contains(notification)) {
            document.body.removeChild(notification);
        }
    }, 5000);
}

/**
 * Fonction pour initialiser la connexion API
 */
async function initializeAPI() {
    try {
        // Tester la connexion à l'API
        await titlesAPI.getDashboardStats();
        console.log('✅ Connexion API établie avec succès');
        return true;
    } catch (error) {
        console.error('❌ Impossible de se connecter à l\'API:', error);
        showNotification('error', 'Impossible de se connecter au serveur. Vérifiez que le backend Django est démarré.');
        return false;
    }
}

/**
 * Fonction pour charger et afficher les titres dans un tableau
 */
async function loadTitlesTable(tableBodyId, filters = {}) {
    try {
        const response = await titlesAPI.getTitles(filters);
        const titles = response.results || response;
        
        const tableBody = document.getElementById(tableBodyId);
        if (!tableBody) {
            console.error(`Table body avec l'ID "${tableBodyId}" non trouvé`);
            return;
        }
        
        // Vider le tableau
        tableBody.innerHTML = '';
        
        // Ajouter chaque titre
        titles.forEach(title => {
            const row = createTitleTableRow(title);
            tableBody.appendChild(row);
        });
        
        console.log(`✅ ${titles.length} titres chargés dans le tableau`);
        
    } catch (error) {
        handleAPIError(error, 'chargement des titres');
    }
}

/**
 * Crée une ligne de tableau pour un titre
 */
function createTitleTableRow(title) {
    const row = document.createElement('tr');
    
    // Classes CSS pour les statuts
    const statusClass = {
        'ACTIF': 'bg-green-100 text-green-800',
        'EXPIRE': 'bg-red-100 text-red-800',
        'SUSPENDU': 'bg-yellow-100 text-yellow-800',
        'RENOUVELE': 'bg-blue-100 text-blue-800',
        'ANNULE': 'bg-gray-100 text-gray-800'
    };
    
    // Déterminer si le titre est en urgence
    const isUrgent = title.is_expiring_soon || title.is_expired;
    const urgentClass = isUrgent ? 'bg-red-50 border-l-4 border-red-500' : '';
    
    row.className = urgentClass;
    row.innerHTML = `
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
            ${title.numero}
        </td>
        <td class="px-6 py-4 whitespace-nowrap">
            <div class="text-sm font-medium text-gray-900">${title.raison_sociale}</div>
            <div class="text-sm text-gray-500">${title.ville}</div>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
            ${title.numero_agrement}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
            ${formatDate(title.date_signature)}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
            ${formatDate(title.validite)}
            ${title.is_expiring_soon ? '<span class="ml-2 text-xs text-red-600">⚠️ Expire bientôt</span>' : ''}
            ${title.is_expired ? '<span class="ml-2 text-xs text-red-600">❌ Expiré</span>' : ''}
        </td>
        <td class="px-6 py-4 whitespace-nowrap">
            <span class="inline-flex px-2 py-1 text-xs font-medium rounded-full ${statusClass[title.statut] || 'bg-gray-100 text-gray-800'}">
                ${title.statut}
            </span>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
            ${title.telephone}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
            <button onclick="viewTitle(${title.numero})" class="text-blue-600 hover:text-blue-900 mr-2">
                <i class="fas fa-eye"></i>
            </button>
            <button onclick="editTitle(${title.numero})" class="text-green-600 hover:text-green-900 mr-2">
                <i class="fas fa-edit"></i>
            </button>
            ${title.statut === 'ACTIF' && title.is_expiring_soon ? 
                `<button onclick="renewTitle(${title.numero})" class="text-yellow-600 hover:text-yellow-900 mr-2" title="Renouveler">
                    <i class="fas fa-sync-alt"></i>
                </button>` : ''
            }
        </td>
    `;
    
    return row;
}

/**
 * Fonction utilitaire pour formater les dates
 */
function formatDate(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

/**
 * Gestionnaire pour l'importation Excel
 */
async function handleExcelImport(fileInputId, progressBarId = null) {
    const fileInput = document.getElementById(fileInputId);
    const file = fileInput.files[0];
    
    if (!file) {
        showNotification('warning', 'Veuillez sélectionner un fichier Excel');
        return;
    }
    
    // Validation du fichier
    const allowedTypes = [
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ];
    
    if (!allowedTypes.includes(file.type) && !file.name.match(/\.(xlsx|xls)$/i)) {
        showNotification('error', 'Veuillez sélectionner un fichier Excel (.xlsx ou .xls)');
        return;
    }
    
    try {
        // Afficher la barre de progression si fournie
        if (progressBarId) {
            const progressBar = document.getElementById(progressBarId);
            if (progressBar) {
                progressBar.style.display = 'block';
            }
        }
        
        showNotification('info', 'Import en cours...');
        
        const result = await titlesAPI.importExcel(file);
        
        // Masquer la barre de progression
        if (progressBarId) {
            const progressBar = document.getElementById(progressBarId);
            if (progressBar) {
                progressBar.style.display = 'none';
            }
        }
        
        if (result.success) {
            showNotification('success', 
                `Import réussi: ${result.data.nombre_succes} enregistrements traités. 
                ${result.data.nombre_erreurs > 0 ? `${result.data.nombre_erreurs} erreurs.` : ''}`
            );
            
            // Recharger les données si on est sur une page avec un tableau
            const tableBody = document.querySelector('tbody');
            if (tableBody && tableBody.id) {
                await loadTitlesTable(tableBody.id);
            }
            
            // Réinitialiser le formulaire
            fileInput.value = '';
        } else {
            showNotification('error', `Erreur d'import: ${result.error}`);
        }
        
    } catch (error) {
        handleAPIError(error, 'import Excel');
        
        // Masquer la barre de progression en cas d'erreur
        if (progressBarId) {
            const progressBar = document.getElementById(progressBarId);
            if (progressBar) {
                progressBar.style.display = 'none';
            }
        }
    }
}

/**
 * Fonctions pour les actions sur les titres
 */
async function viewTitle(id) {
    try {
        const title = await titlesAPI.getTitle(id);
        // Ici vous pouvez afficher une modal avec les détails
        console.log('Détails du titre:', title);
        showNotification('info', `Affichage des détails du titre ${title.numero_agrement}`);
    } catch (error) {
        handleAPIError(error, 'consultation du titre');
    }
}

async function editTitle(id) {
    try {
        const title = await titlesAPI.getTitle(id);
        // Ici vous pouvez afficher un formulaire d'édition
        console.log('Édition du titre:', title);
        showNotification('info', `Édition du titre ${title.numero_agrement}`);
    } catch (error) {
        handleAPIError(error, 'édition du titre');
    }
}

async function renewTitle(id) {
    if (!confirm('Êtes-vous sûr de vouloir renouveler ce titre ?')) {
        return;
    }
    
    try {
        const result = await titlesAPI.renewTitle(id);
        showNotification('success', `Titre renouvelé avec succès jusqu'au ${formatDate(result.validite)}`);
        
        // Recharger le tableau
        const tableBody = document.querySelector('tbody');
        if (tableBody && tableBody.id) {
            await loadTitlesTable(tableBody.id);
        }
    } catch (error) {
        handleAPIError(error, 'renouvellement du titre');
    }
}

/**
 * Fonction pour charger les statistiques du dashboard
 */
async function loadDashboardStats() {
    try {
        const stats = await titlesAPI.getDashboardStats();
        
        // Mettre à jour les éléments du DOM avec les statistiques
        updateStatElement('total-requests', stats.total_titres);
        updateStatElement('pending-requests', stats.titres_expirant_bientot);
        updateStatElement('approved-requests', stats.titres_actifs);
        updateStatElement('urgent-requests', stats.titres_expires);
        
        console.log('✅ Statistiques du dashboard chargées');
        return stats;
        
    } catch (error) {
        handleAPIError(error, 'chargement des statistiques');
        return null;
    }
}

/**
 * Met à jour un élément statistique
 */
function updateStatElement(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = typeof value === 'number' ? value.toLocaleString('fr-FR') : value;
    }
}

/**
 * Initialisation automatique quand le DOM est prêt
 */
document.addEventListener('DOMContentLoaded', async function() {
    console.log('🚀 Initialisation de l\'intégration API...');
    
    const isConnected = await initializeAPI();
    
    if (isConnected) {
        // Charger les statistiques si on est sur le dashboard
        if (document.getElementById('total-requests')) {
            await loadDashboardStats();
        }
        
        // Charger les titres si on est sur une page avec un tableau
        const tableBody = document.querySelector('tbody[id]');
        if (tableBody) {
            await loadTitlesTable(tableBody.id);
        }
    }
});

// Exporter les fonctions pour utilisation globale
window.titlesAPI = titlesAPI;
window.handleExcelImport = handleExcelImport;
window.loadTitlesTable = loadTitlesTable;
window.viewTitle = viewTitle;
window.editTitle = editTitle;
window.renewTitle = renewTitle;
window.loadDashboardStats = loadDashboardStats;
