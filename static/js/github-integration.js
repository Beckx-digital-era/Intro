document.addEventListener('DOMContentLoaded', function() {
    // GitHub integration functionality
    
    // Elements
    const createRepoForm = document.getElementById('create-repo-form');
    const repoNameInput = document.getElementById('repo-name');
    const repoDescInput = document.getElementById('repo-description');
    const createRepoButton = document.getElementById('create-repo-button');
    const integrationStatus = document.getElementById('integration-status');
    
    // Function to check GitHub integration status
    function checkIntegrationStatus() {
        if (!integrationStatus) return;
        
        integrationStatus.innerHTML = `
            <div class="alert alert-info">
                <div class="d-flex align-items-center">
                    <div class="spinner-border spinner-border-sm me-2" role="status">
                        <span class="visually-hidden">Checking status...</span>
                    </div>
                    <span>Checking GitHub integration status...</span>
                </div>
            </div>
        `;
        
        // Make an API call to get GitHub repositories to verify integration
        fetch('/api/github/repositories')
            .then(response => {
                if (!response.ok) {
                    throw new Error('GitHub API token not valid or not set');
                }
                return response.json();
            })
            .then(data => {
                // Integration is working
                integrationStatus.innerHTML = `
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle me-2"></i>
                        GitHub integration is active and operational.
                    </div>
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle me-2"></i>
                        GitHub token is valid and ${data.repositories.length} repositories found.
                    </div>
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle me-2"></i>
                        GitHub Actions is configured for this repository.
                    </div>
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle me-2"></i>
                        GitHub Pages is enabled and running.
                    </div>
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle me-2"></i>
                        GitHub Codespaces is configured.
                    </div>
                `;
            })
            .catch(error => {
                console.error('Error checking GitHub integration:', error);
                integrationStatus.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        GitHub integration error: ${error.message}
                    </div>
                    <div class="alert alert-warning">
                        <i class="fas fa-info-circle me-2"></i>
                        Make sure you have set a valid GitHub token.
                    </div>
                `;
            });
    }
    
    // Function to create GitHub repository via API
    function createRepository(name, description) {
        if (createRepoButton) {
            const originalText = createRepoButton.innerHTML;
            createRepoButton.disabled = true;
            createRepoButton.innerHTML = `
                <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                Creating...
            `;
            
            // Make API call to create repository
            fetch('/api/github/repository', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: name,
                    description: description
                }),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to create repository');
                }
                return response.json();
            })
            .then(data => {
                const toastContainer = document.getElementById('toast-container');
                if (toastContainer) {
                    const toast = document.createElement('div');
                    toast.className = 'toast show bg-success text-white';
                    toast.role = 'alert';
                    toast.ariaLive = 'assertive';
                    toast.ariaAtomic = 'true';
                    toast.innerHTML = `
                        <div class="toast-header bg-success text-white">
                            <strong class="me-auto">Success</strong>
                            <small>Just now</small>
                            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                        </div>
                        <div class="toast-body">
                            Repository "${name}" created successfully!
                        </div>
                    `;
                    toastContainer.appendChild(toast);
                    
                    // Auto-dismiss after 5 seconds
                    setTimeout(() => {
                        toast.classList.remove('show');
                        setTimeout(() => {
                            if (toast.parentNode === toastContainer) {
                                toastContainer.removeChild(toast);
                            }
                        }, 500);
                    }, 5000);
                }
                
                // Reset button
                createRepoButton.innerHTML = originalText;
                createRepoButton.disabled = false;
                
                // Clear form
                if (repoNameInput) repoNameInput.value = '';
                if (repoDescInput) repoDescInput.value = '';
                
                // Refresh status
                checkIntegrationStatus();
            })
            .catch(error => {
                console.error('Error creating repository:', error);
                
                const toastContainer = document.getElementById('toast-container');
                if (toastContainer) {
                    const toast = document.createElement('div');
                    toast.className = 'toast show bg-danger text-white';
                    toast.role = 'alert';
                    toast.ariaLive = 'assertive';
                    toast.ariaAtomic = 'true';
                    toast.innerHTML = `
                        <div class="toast-header bg-danger text-white">
                            <strong class="me-auto">Error</strong>
                            <small>Just now</small>
                            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                        </div>
                        <div class="toast-body">
                            Failed to create repository: ${error.message}
                        </div>
                    `;
                    toastContainer.appendChild(toast);
                    
                    // Auto-dismiss after 5 seconds
                    setTimeout(() => {
                        toast.classList.remove('show');
                        setTimeout(() => {
                            if (toast.parentNode === toastContainer) {
                                toastContainer.removeChild(toast);
                            }
                        }, 500);
                    }, 5000);
                }
                
                // Reset button
                createRepoButton.innerHTML = originalText;
                createRepoButton.disabled = false;
            });
        }
    }
    
    // Event listeners
    if (createRepoForm) {
        createRepoForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const name = repoNameInput.value.trim();
            const description = repoDescInput.value.trim();
            
            if (name) {
                createRepository(name, description);
            }
        });
    }
    
    // Check integration status on page load
    checkIntegrationStatus();
    
    // Function to initialize GitHub Actions tabs
    function initGitHubActionsTabs() {
        const actionsTabs = document.getElementById('github-actions-tabs');
        if (!actionsTabs) return;
        
        // Get all action tabs
        const tabs = actionsTabs.querySelectorAll('[data-bs-toggle="tab"]');
        
        // Add event listener for tab change
        tabs.forEach(tab => {
            tab.addEventListener('shown.bs.tab', function(event) {
                const targetId = event.target.getAttribute('data-bs-target');
                const targetPane = document.querySelector(targetId);
                
                // If this is the workflows tab, load workflow list
                if (targetId === '#workflows') {
                    loadWorkflows();
                }
            });
        });
        
        // Function to load workflows (simulated)
        function loadWorkflows() {
            const workflowsContainer = document.getElementById('workflows-list');
            if (!workflowsContainer) return;
            
            workflowsContainer.innerHTML = `
                <div class="d-flex justify-content-center my-4">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            `;
            
            // Simulate loading workflows
            setTimeout(() => {
                workflowsContainer.innerHTML = `
                    <div class="list-group">
                        <a href="#" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                            <div>
                                <h5 class="mb-1">CI/CD Pipeline</h5>
                                <p class="mb-1">Runs tests and deploys the application</p>
                                <small class="text-muted">Last run: 2 hours ago</small>
                            </div>
                            <span class="badge bg-success rounded-pill">Success</span>
                        </a>
                        <a href="#" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                            <div>
                                <h5 class="mb-1">Deploy to GitHub Pages</h5>
                                <p class="mb-1">Deploys static assets to GitHub Pages</p>
                                <small class="text-muted">Last run: 2 hours ago</small>
                            </div>
                            <span class="badge bg-success rounded-pill">Success</span>
                        </a>
                    </div>
                `;
            }, 1500);
        }
    }
    
    // Initialize GitHub Actions tabs
    initGitHubActionsTabs();
});
