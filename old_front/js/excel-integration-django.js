/**
 * Module d'intégration Excel avec Django Backend
 * Gère l'importation des fichiers Excel et la synchronisation avec l'API
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Module d\'intégration Excel Django chargé');
    
    // Initialiser les fonctionnalités Excel
    initializeExcelIntegration();
});

function initializeExcelIntegration() {
    console.log('Intégration Excel initialisée pour Django');
    
    // Ajouter les gestionnaires d'événements pour les imports Excel
    const importButtons = document.querySelectorAll('[data-action="import-excel"]');
    importButtons.forEach(button => {
        button.addEventListener('click', handleExcelImportClick);
    });
    
    // Gérer les formulaires d'upload Excel
    const uploadForms = document.querySelectorAll('form[data-excel-upload]');
    uploadForms.forEach(form => {
        form.addEventListener('submit', handleExcelFormSubmit);
    });
    
    // Gérer le drag & drop pour les fichiers Excel
    initializeDragDrop();
    
    // Initialiser les modals d'import si présentes
    initializeImportModal();
}

function handleExcelImportClick(event) {
    event.preventDefault();
    
    // Créer un input file temporaire
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.xlsx,.xls';
    fileInput.style.display = 'none';
    
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            processExcelFileWithAPI(file);
        }
    });
    
    document.body.appendChild(fileInput);
    fileInput.click();
    document.body.removeChild(fileInput);
}

function handleExcelFormSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const fileInput = form.querySelector('input[type="file"]');
    const file = fileInput ? fileInput.files[0] : null;
    
    if (!file) {
        showErrorMessage('Veuillez sélectionner un fichier Excel');
        return;
    }
    
    processExcelFileWithAPI(file);
}

async function processExcelFileWithAPI(file) {
    console.log('Traitement du fichier Excel avec API Django:', file.name);
    
    // Valider le fichier
    if (!validateExcelFile(file)) {
        return;
    }
    
    // Afficher l'indicateur de progression
    showProgressIndicator();
    
    try {
        // Utiliser l'API d'intégration
        const result = await window.handleExcelImport ? 
            window.titlesAPI.importExcel(file) : 
            await importExcelFallback(file);
        
        hideProgressIndicator();
        
        if (result.success) {
            showSuccessMessage(
                `✅ Import réussi!<br>
                📊 ${result.data.nombre_lignes} lignes traitées<br>
                ✅ ${result.data.nombre_succes} succès<br>
                ${result.data.nombre_erreurs > 0 ? `❌ ${result.data.nombre_erreurs} erreurs` : ''}`
            );
            
            // Afficher les erreurs si présentes
            if (result.data.erreurs && result.data.erreurs.length > 0) {
                showImportErrors(result.data.erreurs);
            }
            
            // Mettre à jour l'affichage
            await updateDataDisplay();
            
            // Fermer la modal d'import si ouverte
            closeImportModal();
            
        } else {
            showErrorMessage(`❌ Erreur d'import: ${result.error}`);
        }
        
    } catch (error) {
        hideProgressIndicator();
        console.error('Erreur lors de l\'import Excel:', error);
        showErrorMessage(`❌ Erreur lors de l'import: ${error.message}`);
    }
}

function validateExcelFile(file) {
    // Vérifier l'extension
    const allowedExtensions = ['.xlsx', '.xls'];
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    
    if (!allowedExtensions.includes(fileExtension)) {
        showErrorMessage('Format de fichier non supporté. Utilisez .xlsx ou .xls');
        return false;
    }
    
    // Vérifier la taille (max 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
        showErrorMessage('Le fichier est trop volumineux (max 10MB)');
        return false;
    }
    
    return true;
}

async function importExcelFallback(file) {
    // Fallback si l'API principale n'est pas disponible
    const formData = new FormData();
    formData.append('fichier', file);
    formData.append('utilisateur', 'Frontend User');
    
    const response = await fetch('http://localhost:8000/api/titles/import-excel/', {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Erreur lors de l\'import');
    }
    
    return await response.json();
}

function initializeDragDrop() {
    const dropZones = document.querySelectorAll('[data-drop-zone="excel"]');
    
    dropZones.forEach(zone => {
        zone.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.add('drag-over', 'border-blue-500', 'bg-blue-50');
        });
        
        zone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.remove('drag-over', 'border-blue-500', 'bg-blue-50');
        });
        
        zone.addEventListener('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.remove('drag-over', 'border-blue-500', 'bg-blue-50');
            
            const files = Array.from(e.dataTransfer.files);
            const excelFiles = files.filter(file => 
                file.name.toLowerCase().endsWith('.xlsx') || 
                file.name.toLowerCase().endsWith('.xls')
            );
            
            if (excelFiles.length > 0) {
                processExcelFileWithAPI(excelFiles[0]);
            } else {
                showErrorMessage('Veuillez déposer un fichier Excel (.xlsx ou .xls)');
            }
        });
    });
}

function initializeImportModal() {
    // Gérer l'ouverture de la modal d'import
    const importModalTriggers = document.querySelectorAll('[data-modal="excel-import"]');
    importModalTriggers.forEach(trigger => {
        trigger.addEventListener('click', openImportModal);
    });
    
    // Gérer la fermeture de la modal
    const closeButtons = document.querySelectorAll('[data-close-modal="excel-import"]');
    closeButtons.forEach(button => {
        button.addEventListener('click', closeImportModal);
    });
}

function openImportModal() {
    const modal = document.getElementById('excel-import-modal');
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
}

function closeImportModal() {
    const modal = document.getElementById('excel-import-modal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.add('hidden');
        document.body.style.overflow = 'auto';
        
        // Réinitialiser le formulaire
        const form = modal.querySelector('form');
        if (form) {
            form.reset();
        }
    }
}

function showProgressIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'excel-progress-indicator';
    indicator.innerHTML = `
        <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                <div class="text-center">
                    <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                    <h3 class="text-lg font-semibold mb-2">Import en cours...</h3>
                    <p class="text-gray-600">Traitement des données Excel</p>
                    <div class="mt-4 bg-gray-200 rounded-full h-2">
                        <div class="bg-blue-500 h-2 rounded-full progress-bar" style="width: 0%"></div>
                    </div>
                    <p class="text-xs text-gray-500 mt-2">Veuillez patienter...</p>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(indicator);
    
    // Animer la barre de progression
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        
        const progressBar = indicator.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = progress + '%';
        }
        
        if (progress >= 90) {
            clearInterval(interval);
        }
    }, 300);
    
    // Stocker l'interval pour pouvoir l'arrêter
    indicator.dataset.intervalId = interval;
}

function hideProgressIndicator() {
    const indicator = document.getElementById('excel-progress-indicator');
    if (indicator) {
        // Arrêter l'animation
        const intervalId = indicator.dataset.intervalId;
        if (intervalId) {
            clearInterval(parseInt(intervalId));
        }
        
        // Compléter la barre de progression
        const progressBar = indicator.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = '100%';
        }
        
        // Supprimer après un court délai
        setTimeout(() => {
            indicator.remove();
        }, 500);
    }
}

function showImportErrors(errors) {
    if (!errors || errors.length === 0) return;
    
    const errorModal = document.createElement('div');
    errorModal.id = 'import-errors-modal';
    errorModal.innerHTML = `
        <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-96 overflow-y-auto">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-semibold text-red-600">
                        <i class="fas fa-exclamation-triangle mr-2"></i>
                        Erreurs d'import détectées
                    </h3>
                    <button onclick="closeErrorsModal()" class="text-gray-500 hover:text-gray-700">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="space-y-2">
                    ${errors.map(error => `
                        <div class="p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                            ${error}
                        </div>
                    `).join('')}
                </div>
                <div class="mt-4 text-center">
                    <button onclick="closeErrorsModal()" class="btn-secondary">
                        Fermer
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(errorModal);
    
    // Fonction globale pour fermer la modal
    window.closeErrorsModal = function() {
        errorModal.remove();
        delete window.closeErrorsModal;
    };
}

function showSuccessMessage(message) {
    showNotification(message, 'success');
}

function showErrorMessage(message) {
    showNotification(message, 'error');
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 px-6 py-3 rounded-lg shadow-lg transition-all duration-300 ${
        type === 'success' ? 'bg-green-500 text-white' :
        type === 'error' ? 'bg-red-500 text-white' :
        type === 'warning' ? 'bg-yellow-500 text-black' :
        'bg-blue-500 text-white'
    }`;
    
    notification.innerHTML = `
        <div class="flex items-center">
            <i class="fas ${
                type === 'success' ? 'fa-check-circle' :
                type === 'error' ? 'fa-exclamation-circle' :
                type === 'warning' ? 'fa-exclamation-triangle' :
                'fa-info-circle'
            } mr-2"></i>
            <div>${message}</div>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Animation d'entrée
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
        notification.style.opacity = '1';
    }, 100);
    
    // Suppression automatique après 7 secondes
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        notification.style.opacity = '0';
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, 7000);
}

async function updateDataDisplay() {
    console.log('Mise à jour de l\'affichage des données après import');
    
    try {
        // Recharger les statistiques si on est sur le dashboard
        if (typeof window.loadDashboardStats === 'function') {
            await window.loadDashboardStats();
        }
        
        // Recharger les tableaux de données
        const dataTables = document.querySelectorAll('[data-update-on-import]');
        dataTables.forEach(async (table) => {
            console.log('Rechargement du tableau:', table.id);
            
            if (typeof window.loadTitlesTable === 'function' && table.querySelector('tbody')) {
                const tbody = table.querySelector('tbody');
                await window.loadTitlesTable(tbody.id);
            }
        });
        
        // Mettre à jour les compteurs si présents
        updateCounters();
        
        // Déclencher un événement personnalisé pour notifier d'autres modules
        const event = new CustomEvent('dataUpdated', {
            detail: { source: 'excel-import' }
        });
        document.dispatchEvent(event);
        
    } catch (error) {
        console.error('Erreur lors de la mise à jour de l\'affichage:', error);
    }
}

function updateCounters() {
    // Mettre à jour les compteurs d'éléments sur la page
    const counters = document.querySelectorAll('[data-counter]');
    counters.forEach(counter => {
        const counterId = counter.dataset.counter;
        // Ici on pourrait faire un appel API pour obtenir le nouveau count
        // Pour l'instant on simule une augmentation
        const currentValue = parseInt(counter.textContent) || 0;
        counter.textContent = currentValue + 1;
    });
}

// Exporter les fonctions pour utilisation globale
window.processExcelFileWithAPI = processExcelFileWithAPI;
window.showImportModal = openImportModal;
window.hideImportModal = closeImportModal;