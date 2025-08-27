// Script pour l'intégration des fichiers Excel avec le backend ART Telecom

class ExcelIntegration {
    constructor() {
        this.apiBaseUrl = 'http://localhost:3000/api';
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Écouteur pour le bouton d'upload Excel
        const uploadBtn = document.getElementById('uploadExcelBtn');
        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => this.showUploadModal());
        }

        // Écouteur pour le formulaire d'upload
        const uploadForm = document.getElementById('excelUploadForm');
        if (uploadForm) {
            uploadForm.addEventListener('submit', (e) => this.handleFileUpload(e));
        }

        // Écouteur pour le bouton de fermeture du modal
        const closeModalBtn = document.getElementById('closeUploadModal');
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', () => this.hideUploadModal());
        }
    }

    showUploadModal() {
        const modal = document.getElementById('uploadModal');
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
        }
    }

    hideUploadModal() {
        const modal = document.getElementById('uploadModal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }
    }

    async handleFileUpload(event) {
        event.preventDefault();
        
        const fileInput = document.getElementById('excelFile');
        const file = fileInput.files[0];
        
        if (!file) {
            this.showNotification('Veuillez sélectionner un fichier Excel', 'error');
            return;
        }

        // Validation du type de fichier
        const allowedTypes = [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel',
            'text/csv'
        ];

        if (!allowedTypes.includes(file.type)) {
            this.showNotification('Type de fichier non supporté. Veuillez uploader un fichier Excel (.xlsx, .xls) ou CSV.', 'error');
            return;
        }

        // Validation de la taille du fichier (10MB max)
        if (file.size > 10 * 1024 * 1024) {
            this.showNotification('Le fichier est trop volumineux. Taille maximale : 10MB', 'error');
            return;
        }

        this.showLoading();
        
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${this.apiBaseUrl}/upload-excel`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                this.showNotification(`Fichier traité avec succès ! ${result.recordsProcessed} enregistrements importés.`, 'success');
                this.hideUploadModal();
                
                // Actualiser les données affichées
                this.refreshData();
                
                // Réinitialiser le formulaire
                document.getElementById('excelUploadForm').reset();
            } else {
                throw new Error(result.error || 'Erreur lors du traitement du fichier');
            }

        } catch (error) {
            console.error('Erreur lors de l\'upload:', error);
            this.showNotification(`Erreur lors de l'upload : ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async refreshData() {
        try {
            // Actualiser les statistiques
            await this.loadStatistics();
            
            // Actualiser les graphiques
            this.updateCharts();
            
            // Actualiser le tableau de données
            await this.loadTableData();
            
        } catch (error) {
            console.error('Erreur lors de l\'actualisation des données:', error);
        }
    }

    async loadStatistics() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/statistics`);
            const stats = await response.json();

            if (response.ok) {
                // Mettre à jour les KPIs
                this.updateKPIs(stats);
            }
        } catch (error) {
            console.error('Erreur lors du chargement des statistiques:', error);
        }
    }

    updateKPIs(stats) {
        // Mise à jour des cartes KPI
        const kpiElements = {
            totalTitles: stats.totalTitles?.count || 0,
            activeTitles: stats.activeTitles?.count || 0,
            expiringSoon: stats.expiringSoon?.count || 0,
            totalRevenue: stats.totalRevenue?.total || 0
        };

        Object.keys(kpiElements).forEach(key => {
            const element = document.getElementById(key);
            if (element) {
                if (key === 'totalRevenue') {
                    element.textContent = this.formatCurrency(kpiElements[key]);
                } else {
                    element.textContent = kpiElements[key].toLocaleString('fr-FR');
                }
            }
        });
    }

    async loadTableData() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/titles`);
            const titles = await response.json();

            if (response.ok) {
                this.populateDataTable(titles);
            }
        } catch (error) {
            console.error('Erreur lors du chargement des données du tableau:', error);
        }
    }

    populateDataTable(titles) {
        const tableBody = document.getElementById('dataTableBody');
        if (!tableBody) return;

        tableBody.innerHTML = '';

        titles.forEach(title => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-secondary-50 transition-colors';
            
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                        <div class="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center mr-3">
                            <i class="fas fa-building text-primary text-sm"></i>
                        </div>
                        <div class="text-sm font-medium text-text-primary">${title.operator_name}</div>
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="status-badge bg-primary-100 text-primary-800">
                        ${title.service_type}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-text-primary font-data">
                    ${title.title_number}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-text-primary font-data">
                    ${title.status === 'actif' ? 'Actif' : 'Expiré'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-text-primary font-data">
                    ${this.formatCurrency(title.revenue)} XAF
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                    ${title.region || 'N/A'}
                </td>
            `;
            
            tableBody.appendChild(row);
        });
    }

    updateCharts() {
        // Actualiser les graphiques avec les nouvelles données
        if (window.charts) {
            Object.values(window.charts).forEach(chart => {
                if (chart && typeof chart.update === 'function') {
                    chart.update();
                }
            });
        }
    }

    showLoading() {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.classList.remove('hidden');
            loadingOverlay.classList.add('flex');
        }
    }

    hideLoading() {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.classList.add('hidden');
            loadingOverlay.classList.remove('flex');
        }
    }

    showNotification(message, type = 'info') {
        // Créer l'élément de notification
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 p-4 rounded-md shadow-elevated max-w-sm transition-all duration-300 transform translate-x-full`;
        
        const colors = {
            success: 'bg-success-50 border border-success-200 text-success-800',
            error: 'bg-error-50 border border-error-200 text-error-800',
            warning: 'bg-warning-50 border border-warning-200 text-warning-800',
            info: 'bg-accent-50 border border-accent-200 text-accent-800'
        };
        
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        
        notification.className += ` ${colors[type]}`;
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="${icons[type]} mr-2"></i>
                <span class="text-sm font-medium">${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-current opacity-70 hover:opacity-100">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animer l'entrée
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);
        
        // Auto-suppression après 5 secondes
        setTimeout(() => {
            notification.classList.add('translate-x-full');
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 300);
        }, 5000);
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('fr-FR', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount || 0);
    }

    // Méthode pour exporter les données en Excel
    async exportToExcel() {
        try {
            this.showLoading();
            
            const response = await fetch(`${this.apiBaseUrl}/titles`);
            const titles = await response.json();

            if (response.ok) {
                // Créer un workbook Excel
                const workbook = XLSX.utils.book_new();
                const worksheet = XLSX.utils.json_to_sheet(titles);
                
                // Ajouter le worksheet au workbook
                XLSX.utils.book_append_sheet(workbook, worksheet, 'Titres Telecom');
                
                // Générer le fichier Excel
                const excelBuffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
                const blob = new Blob([excelBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
                
                // Télécharger le fichier
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = `titres_telecom_${new Date().toISOString().split('T')[0]}.xlsx`;
                link.click();
                
                window.URL.revokeObjectURL(url);
                
                this.showNotification('Export Excel réussi !', 'success');
            }
        } catch (error) {
            console.error('Erreur lors de l\'export Excel:', error);
            this.showNotification('Erreur lors de l\'export Excel', 'error');
        } finally {
            this.hideLoading();
        }
    }
}

// Initialisation de l'intégration Excel
document.addEventListener('DOMContentLoaded', function() {
    window.excelIntegration = new ExcelIntegration();
}); 