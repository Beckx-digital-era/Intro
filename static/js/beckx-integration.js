/**
 * Beckx Digital Era Integration - JavaScript for integrating with Beckx-digital-era/Intro repository
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    initBeckxIntegration();
});

/**
 * Initialize the Beckx Integration section
 */
function initBeckxIntegration() {
    // Add event listeners to buttons once they exist
    const checkInterval = setInterval(() => {
        const syncButton = document.getElementById('beckx-sync-button');
        const setupCicdButton = document.getElementById('beckx-setup-cicd-button');
        const deployButton = document.getElementById('beckx-deploy-button');
        
        if (syncButton && setupCicdButton && deployButton) {
            clearInterval(checkInterval);
            
            syncButton.addEventListener('click', syncRepository);
            setupCicdButton.addEventListener('click', setupCICD);
            deployButton.addEventListener('click', deployToProduction);
            
            // Load initial data
            fetchRepositoryDetails();
            fetchRecentCommits();
            
            // Check if loadRecentActions exists before calling it
            if (typeof loadRecentActions === 'function') {
                loadRecentActions(); // Reuse from gitlab-integration.js
            }
        }
    }, 500);
}

/**
 * Fetch repository details from the GitHub API via our backend
 */
function fetchRepositoryDetails() {
    const repoDetailsElement = document.getElementById('beckx-repo-details');
    if (!repoDetailsElement) return;
    
    // Show loading indicator
    repoDetailsElement.innerHTML = '<div class="d-flex justify-content-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    
    fetch('/api/github/repository/beckx-intro')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                repoDetailsElement.innerHTML = `<div class="alert alert-danger">Error: ${data.error}</div>`;
                return;
            }
            
            const repo = data.repository;
            
            // Update repository details section
            repoDetailsElement.innerHTML = `
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5 class="mb-0"><i class="fab fa-github me-2"></i>${repo.full_name}</h5>
                        <span class="badge bg-${repo.private ? 'danger' : 'success'}">${repo.private ? 'Private' : 'Public'}</span>
                    </div>
                    <div class="card-body">
                        <p class="card-text">${repo.description || 'No description provided'}</p>
                        <div class="row mb-2">
                            <div class="col-md-6">
                                <small class="text-muted"><i class="fas fa-code-branch me-1"></i> Default branch: ${repo.default_branch}</small>
                            </div>
                            <div class="col-md-6">
                                <small class="text-muted"><i class="fas fa-star me-1"></i> Stars: ${repo.stargazers_count}</small>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6">
                                <small class="text-muted"><i class="fas fa-code me-1"></i> Language: ${repo.language || 'Not specified'}</small>
                            </div>
                            <div class="col-md-6">
                                <small class="text-muted"><i class="fas fa-clock me-1"></i> Updated: ${new Date(repo.updated_at).toLocaleDateString()}</small>
                            </div>
                        </div>
                    </div>
                    <div class="card-footer">
                        <a href="${repo.html_url}" target="_blank" class="btn btn-sm btn-primary">
                            <i class="fab fa-github me-1"></i> View on GitHub
                        </a>
                        <a href="${repo.html_url}/issues" target="_blank" class="btn btn-sm btn-outline-secondary">
                            <i class="fas fa-exclamation-circle me-1"></i> Issues
                        </a>
                    </div>
                </div>
            `;
        })
        .catch(error => {
            console.error('Error fetching repository details:', error);
            repoDetailsElement.innerHTML = `<div class="alert alert-danger">Failed to load repository details. Please try again later.</div>`;
        });
}

/**
 * Fetch recent commits for the repository
 */
function fetchRecentCommits() {
    const commitsElement = document.getElementById('beckx-commits');
    if (!commitsElement) return;
    
    // Show loading indicator
    commitsElement.innerHTML = '<div class="d-flex justify-content-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    
    fetch('/api/github/repository/beckx-intro/commits')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                commitsElement.innerHTML = `<div class="alert alert-danger">Error: ${data.error}</div>`;
                return;
            }
            
            const commits = data.commits.slice(0, 5); // Get last 5 commits
            
            if (commits.length === 0) {
                commitsElement.innerHTML = '<div class="alert alert-info">No commits found.</div>';
                return;
            }
            
            // Create a list of commits
            let commitsHtml = '<div class="list-group">';
            
            commits.forEach(commit => {
                const date = new Date(commit.commit.author.date).toLocaleString();
                commitsHtml += `
                    <a href="${commit.html_url}" target="_blank" class="list-group-item list-group-item-action">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1 text-truncate" style="max-width: 70%;">${commit.commit.message}</h6>
                            <small class="text-muted">${date}</small>
                        </div>
                        <div class="d-flex align-items-center">
                            <img src="${commit.author ? commit.author.avatar_url : 'https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png'}" alt="Author" class="rounded-circle me-2" width="20" height="20">
                            <small>${commit.commit.author.name}</small>
                        </div>
                    </a>
                `;
            });
            
            commitsHtml += '</div>';
            commitsElement.innerHTML = commitsHtml;
        })
        .catch(error => {
            console.error('Error fetching commits:', error);
            commitsElement.innerHTML = `<div class="alert alert-danger">Failed to load commits. Please try again later.</div>`;
        });
}

/**
 * Sync the GitHub repository with GitLab
 */
function syncRepository() {
    const syncButton = document.getElementById('beckx-sync-button');
    if (!syncButton) return;
    
    // Disable button and show loading
    syncButton.disabled = true;
    syncButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Syncing...';
    
    fetch('/api/github/repository/beckx-intro/sync-gitlab', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            // Show error toast
            showToast('Sync Failed', data.error, 'error');
            console.error('Error syncing repository:', data.error);
        } else {
            // Show success toast
            showToast('Sync Successful', 'Repository successfully synchronized with GitLab.', 'success');
            
            // Enable GitLab setup button
            const setupCicdButton = document.getElementById('beckx-setup-cicd-button');
            if (setupCicdButton) {
                setupCicdButton.disabled = false;
            }
        }
        
        // Re-enable button
        syncButton.disabled = false;
        syncButton.innerHTML = '<i class="fas fa-sync-alt me-1"></i> Sync with GitLab';
        
        // Refresh actions list if function exists
        if (typeof loadRecentActions === 'function') {
            loadRecentActions();
        }
    })
    .catch(error => {
        console.error('Error syncing repository:', error);
        showToast('Sync Failed', 'An unexpected error occurred. Please try again.', 'error');
        
        // Re-enable button
        syncButton.disabled = false;
        syncButton.innerHTML = '<i class="fas fa-sync-alt me-1"></i> Sync with GitLab';
    });
}

/**
 * Set up CI/CD pipeline for the repository
 */
function setupCICD() {
    const setupButton = document.getElementById('beckx-setup-cicd-button');
    if (!setupButton) return;
    
    // Disable button and show loading
    setupButton.disabled = true;
    setupButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Setting up...';
    
    fetch('/api/github/repository/beckx-intro/setup-cicd', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            // Show error toast
            showToast('CI/CD Setup Failed', data.error, 'error');
            console.error('Error setting up CI/CD:', data.error);
        } else {
            // Show success toast
            showToast('CI/CD Setup Successful', 'CI/CD pipeline configured successfully.', 'success');
            
            // Enable deploy button
            const deployButton = document.getElementById('beckx-deploy-button');
            if (deployButton) {
                deployButton.disabled = false;
            }
        }
        
        // Re-enable button
        setupButton.disabled = false;
        setupButton.innerHTML = '<i class="fas fa-cogs me-1"></i> Setup CI/CD';
        
        // Refresh actions list if function exists
        if (typeof loadRecentActions === 'function') {
            loadRecentActions();
        }
    })
    .catch(error => {
        console.error('Error setting up CI/CD:', error);
        showToast('CI/CD Setup Failed', 'An unexpected error occurred. Please try again.', 'error');
        
        // Re-enable button
        setupButton.disabled = false;
        setupButton.innerHTML = '<i class="fas fa-cogs me-1"></i> Setup CI/CD';
    });
}

/**
 * Deploy the repository to production
 */
function deployToProduction() {
    const deployButton = document.getElementById('beckx-deploy-button');
    if (!deployButton) return;
    
    // Disable button and show loading
    deployButton.disabled = true;
    deployButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Deploying...';
    
    fetch('/api/github/repository/beckx-intro/deploy', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            // Show error toast
            showToast('Deployment Failed', data.error, 'error');
            console.error('Error deploying repository:', data.error);
        } else {
            // Show success toast
            showToast('Deployment Triggered', 'Deployment pipeline started successfully.', 'success');
        }
        
        // Re-enable button
        deployButton.disabled = false;
        deployButton.innerHTML = '<i class="fas fa-rocket me-1"></i> Deploy to Production';
        
        // Refresh actions list if function exists
        if (typeof loadRecentActions === 'function') {
            loadRecentActions();
        }
    })
    .catch(error => {
        console.error('Error deploying repository:', error);
        showToast('Deployment Failed', 'An unexpected error occurred. Please try again.', 'error');
        
        // Re-enable button
        deployButton.disabled = false;
        deployButton.innerHTML = '<i class="fas fa-rocket me-1"></i> Deploy to Production';
    });
}

/**
 * Load recent actions from the server
 * This is similar to the function in gitlab-integration.js but implemented here 
 * to avoid dependency on other files
 */
function loadRecentActions() {
    const actionsElement = document.getElementById('recent-actions');
    if (!actionsElement) return;
    
    fetch('/api/actions/recent')
        .then(response => response.json())
        .then(data => {
            if (!data.actions || data.actions.length === 0) {
                actionsElement.innerHTML = '<div class="alert alert-info">No recent actions found.</div>';
                return;
            }
            
            let actionsHtml = '<div class="list-group">';
            
            data.actions.forEach(action => {
                const date = new Date(action.created_at).toLocaleString();
                const statusBadge = action.status === 'completed' 
                    ? '<span class="badge bg-success">Completed</span>' 
                    : action.status === 'pending'
                    ? '<span class="badge bg-warning">Pending</span>'
                    : '<span class="badge bg-danger">Failed</span>';
                
                actionsHtml += `
                    <div class="list-group-item">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">${action.type}</h6>
                            ${statusBadge}
                        </div>
                        <p class="mb-1">${action.description}</p>
                        <small class="text-muted">${date}</small>
                    </div>
                `;
            });
            
            actionsHtml += '</div>';
            actionsElement.innerHTML = actionsHtml;
        })
        .catch(error => {
            console.error('Error loading recent actions:', error);
            actionsElement.innerHTML = '<div class="alert alert-danger">Failed to load recent actions.</div>';
        });
}

/**
 * Helper function to show toast notifications
 */
function showToast(title, message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    
    const toastId = 'toast-' + Date.now();
    const bgColor = type === 'success' ? 'bg-success' : 
                    type === 'error' ? 'bg-danger' :
                    type === 'warning' ? 'bg-warning' : 'bg-info';
    
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header ${bgColor} text-white">
                <strong class="me-auto">${title}</strong>
                <small>${new Date().toLocaleTimeString()}</small>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 5000
    });
    
    toast.show();
    
    // Remove the toast from DOM after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}