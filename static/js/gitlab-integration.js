document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const projectsList = document.getElementById('gitlab-projects');
    const refreshButton = document.getElementById('refresh-gitlab-projects');
    const createPipelineButton = document.getElementById('create-pipeline-button');
    const projectSelect = document.getElementById('project-select');
    const branchInput = document.getElementById('branch-input');
    
    // Function to load GitLab projects
    function loadGitLabProjects() {
        if (!projectsList) return;
        
        // Show loading indicator
        projectsList.innerHTML = '<div class="d-flex justify-content-center"><div class="loader"></div></div>';
        
        fetch('/api/gitlab/projects')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch GitLab projects');
                }
                return response.json();
            })
            .then(data => {
                // Clear loading indicator
                projectsList.innerHTML = '';
                
                if (data.projects && data.projects.length > 0) {
                    // Display projects
                    data.projects.forEach(project => {
                        const projectCard = document.createElement('div');
                        projectCard.className = 'card project-card mb-2';
                        projectCard.innerHTML = `
                            <div class="card-body">
                                <h5 class="card-title">${project.name}</h5>
                                <p class="card-text">${project.description || 'No description'}</p>
                                <div class="d-flex justify-content-between align-items-center">
                                    <small class="text-muted">ID: ${project.id}</small>
                                    <div>
                                        <button class="btn btn-sm btn-outline-primary create-pipeline-btn" 
                                                data-project-id="${project.id}" 
                                                data-project-name="${project.name}">
                                            Create Pipeline
                                        </button>
                                        <a href="${project.web_url}" target="_blank" class="btn btn-sm btn-outline-secondary">
                                            View
                                        </a>
                                    </div>
                                </div>
                            </div>
                        `;
                        projectsList.appendChild(projectCard);
                        
                        // Add to project select dropdown if it exists
                        if (projectSelect) {
                            const option = document.createElement('option');
                            option.value = project.id;
                            option.textContent = project.name;
                            projectSelect.appendChild(option);
                        }
                    });
                    
                    // Add event listeners to create pipeline buttons
                    document.querySelectorAll('.create-pipeline-btn').forEach(button => {
                        button.addEventListener('click', function() {
                            const projectId = this.getAttribute('data-project-id');
                            const projectName = this.getAttribute('data-project-name');
                            createPipeline(projectId, 'main', projectName);
                        });
                    });
                } else {
                    projectsList.innerHTML = '<div class="alert alert-info">No GitLab projects found or API token is not configured.</div>';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                projectsList.innerHTML = `<div class="alert alert-danger">Error loading GitLab projects: ${error.message}</div>`;
            });
    }
    
    // Function to create a GitLab pipeline
    function createPipeline(projectId, branch, projectName) {
        // Show loading indicator or toast
        const toastContainer = document.getElementById('toast-container');
        if (toastContainer) {
            const toast = document.createElement('div');
            toast.className = 'toast show';
            toast.role = 'alert';
            toast.ariaLive = 'assertive';
            toast.ariaAtomic = 'true';
            toast.innerHTML = `
                <div class="toast-header">
                    <strong class="me-auto">Creating Pipeline</strong>
                    <small>Just now</small>
                    <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    Creating pipeline for ${projectName || 'project'} on branch ${branch}...
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
        
        // Make API request
        fetch('/api/gitlab/pipeline', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                project_id: projectId,
                branch: branch
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to create pipeline');
            }
            return response.json();
        })
        .then(data => {
            console.log('Pipeline created:', data);
            
            // Show success toast
            if (toastContainer) {
                const successToast = document.createElement('div');
                successToast.className = 'toast show bg-success text-white';
                successToast.role = 'alert';
                successToast.ariaLive = 'assertive';
                successToast.ariaAtomic = 'true';
                successToast.innerHTML = `
                    <div class="toast-header bg-success text-white">
                        <strong class="me-auto">Success</strong>
                        <small>Just now</small>
                        <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                    </div>
                    <div class="toast-body">
                        Pipeline created successfully! Pipeline ID: ${data.id}
                    </div>
                `;
                toastContainer.appendChild(successToast);
                
                // Auto-dismiss after 5 seconds
                setTimeout(() => {
                    successToast.classList.remove('show');
                    setTimeout(() => {
                        if (successToast.parentNode === toastContainer) {
                            toastContainer.removeChild(successToast);
                        }
                    }, 500);
                }, 5000);
            }
            
            // Load recent actions to show the new pipeline
            loadRecentActions();
        })
        .catch(error => {
            console.error('Error:', error);
            
            // Show error toast
            if (toastContainer) {
                const errorToast = document.createElement('div');
                errorToast.className = 'toast show bg-danger text-white';
                errorToast.role = 'alert';
                errorToast.ariaLive = 'assertive';
                errorToast.ariaAtomic = 'true';
                errorToast.innerHTML = `
                    <div class="toast-header bg-danger text-white">
                        <strong class="me-auto">Error</strong>
                        <small>Just now</small>
                        <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                    </div>
                    <div class="toast-body">
                        Failed to create pipeline: ${error.message}
                    </div>
                `;
                toastContainer.appendChild(errorToast);
                
                // Auto-dismiss after 5 seconds
                setTimeout(() => {
                    errorToast.classList.remove('show');
                    setTimeout(() => {
                        if (errorToast.parentNode === toastContainer) {
                            toastContainer.removeChild(errorToast);
                        }
                    }, 500);
                }, 5000);
            }
        });
    }
    
    // Function to load recent actions
    function loadRecentActions() {
        const actionsContainer = document.getElementById('recent-actions');
        if (!actionsContainer) return;
        
        fetch('/api/actions/recent')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch recent actions');
                }
                return response.json();
            })
            .then(data => {
                // Clear existing actions
                actionsContainer.innerHTML = '';
                
                if (data.actions && data.actions.length > 0) {
                    const actionsList = document.createElement('ul');
                    actionsList.className = 'list-group';
                    
                    data.actions.forEach(action => {
                        const actionItem = document.createElement('li');
                        actionItem.className = 'list-group-item d-flex justify-content-between align-items-center';
                        
                        // Format created_at date
                        const date = new Date(action.created_at);
                        const formattedDate = date.toLocaleString();
                        
                        // Status badge
                        let badgeClass = 'badge-pending';
                        if (action.status === 'completed') {
                            badgeClass = 'badge-completed';
                        } else if (action.status === 'failed') {
                            badgeClass = 'badge-failed';
                        }
                        
                        actionItem.innerHTML = `
                            <div>
                                <h6 class="mb-0">${action.type}</h6>
                                <small class="text-muted">${action.description}</small>
                                <small class="text-muted d-block">${formattedDate}</small>
                            </div>
                            <span class="badge rounded-pill action-badge ${badgeClass}">${action.status}</span>
                        `;
                        
                        actionsList.appendChild(actionItem);
                    });
                    
                    actionsContainer.appendChild(actionsList);
                } else {
                    actionsContainer.innerHTML = '<div class="alert alert-info">No recent actions found.</div>';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                actionsContainer.innerHTML = `<div class="alert alert-danger">Error loading recent actions: ${error.message}</div>`;
            });
    }
    
    // Event listeners
    if (refreshButton) {
        refreshButton.addEventListener('click', loadGitLabProjects);
    }
    
    if (createPipelineButton) {
        createPipelineButton.addEventListener('click', function() {
            const projectId = projectSelect.value;
            const branch = branchInput.value.trim() || 'main';
            const projectName = projectSelect.options[projectSelect.selectedIndex].textContent;
            
            if (projectId) {
                createPipeline(projectId, branch, projectName);
            } else {
                alert('Please select a project first.');
            }
        });
    }
    
    // Load GitLab projects on page load
    if (projectsList) {
        loadGitLabProjects();
    }
    
    // Load recent actions on page load
    loadRecentActions();
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
