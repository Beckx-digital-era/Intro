import os
import requests
import logging
import json
from flask import current_app

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Base URL for GitLab API
GITLAB_API_BASE_URL = "https://gitlab.com/api/v4"

def get_gitlab_token():
    """Get the GitLab API token from the environment or the Flask app config."""
    token = os.environ.get("GITLAB_TOKEN")
    
    # Alternative environment variable names
    if not token:
        token = os.environ.get("GL_TOKEN")
    
    # If not found in environment, try to get from Flask app config
    if not token:
        try:
            if current_app:
                token = current_app.config.get("GITLAB_TOKEN")
        except RuntimeError:
            # This happens when outside of Flask context
            pass
    
    if not token:
        logger.error("GitLab API token not found in environment variables or app config")
        raise ValueError("GitLab API token not found in environment variables or app config")
    
    return token

def make_gitlab_request(endpoint, method="GET", data=None, params=None, max_retries=3):
    """Make a request to the GitLab API with retry logic."""
    token = get_gitlab_token()
    url = f"{GITLAB_API_BASE_URL}/{endpoint}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    logger.debug(f"Making GitLab API request to: {url}")
    
    # Initialize retry counter
    retries = 0
    last_exception = None
    
    while retries < max_retries:
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Log the response status
            logger.debug(f"GitLab API response status: {response.status_code}")
            
            # Check if the token is invalid
            if response.status_code == 401:
                logger.error("GitLab API token is invalid or expired")
                return {
                    "status": "error", 
                    "message": "GitLab API token is invalid or expired. Please update your token."
                }
            
            response.raise_for_status()
            
            # Handle responses without JSON content
            if response.status_code == 204 or not response.text.strip():
                return {"status": "success", "status_code": response.status_code}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            last_exception = e
            retries += 1
            logger.warning(f"GitLab API request failed (attempt {retries}/{max_retries}): {str(e)}")
            
            if hasattr(e, 'response') and e.response is not None:
                if hasattr(e.response, 'text'):
                    logger.warning(f"Response content: {e.response.text}")
                
                # If we get a 401 Unauthorized, no point in retrying
                if e.response.status_code == 401:
                    logger.error("GitLab API token is invalid or expired")
                    return {
                        "status": "error", 
                        "message": "GitLab API token is invalid or expired. Please update your token."
                    }
            
            # Only sleep if we're going to retry
            if retries < max_retries:
                import time
                time.sleep(1)  # Wait 1 second before retrying
    
    # If we've exhausted all retries, log the error and raise the exception
    logger.error(f"GitLab API request failed after {max_retries} attempts")
    if last_exception:
        # Return error information instead of raising an exception
        error_message = str(last_exception)
        logger.error(f"Final error: {error_message}")
        return {"status": "error", "message": error_message}

def get_gitlab_projects():
    """Get a list of GitLab projects for the authenticated user."""
    return make_gitlab_request("projects", params={"membership": True})

def get_gitlab_project(project_id):
    """Get details for a specific GitLab project."""
    return make_gitlab_request(f"projects/{project_id}")

def create_gitlab_pipeline(project_id, ref="main"):
    """Create a pipeline for a specific GitLab project."""
    return make_gitlab_request(
        f"projects/{project_id}/pipeline",
        method="POST",
        data={"ref": ref}
    )

def get_gitlab_pipelines(project_id):
    """Get a list of pipelines for a specific GitLab project."""
    return make_gitlab_request(f"projects/{project_id}/pipelines")

def get_gitlab_pipeline_jobs(project_id, pipeline_id):
    """Get jobs for a specific pipeline in a GitLab project."""
    return make_gitlab_request(f"projects/{project_id}/pipelines/{pipeline_id}/jobs")

def create_gitlab_project(name, description=""):
    """Create a new GitLab project."""
    return make_gitlab_request(
        "projects",
        method="POST",
        data={
            "name": name,
            "description": description,
            "visibility": "private"
        }
    )

def update_ci_config():
    """Update GitLab CI configuration for all accessible projects."""
    try:
        projects = get_gitlab_projects()
        updated_count = 0
        
        for project in projects:
            project_id = project["id"]
            
            # Basic CI/CD configuration for integration with GitHub
            ci_config = {
                "stages": ["build", "test", "deploy"],
                "variables": {
                    "GITHUB_INTEGRATION": "enabled"
                },
                "build": {
                    "stage": "build",
                    "script": [
                        "echo 'Building project...'",
                        "# Build commands go here"
                    ]
                },
                "test": {
                    "stage": "test",
                    "script": [
                        "echo 'Running tests...'",
                        "# Test commands go here"
                    ]
                },
                "deploy": {
                    "stage": "deploy",
                    "script": [
                        "echo 'Deploying application...'",
                        "# Deployment commands go here"
                    ],
                    "only": ["main"]
                }
            }
            
            try:
                # Create or update .gitlab-ci.yml file in the repository
                make_gitlab_request(
                    f"projects/{project_id}/repository/files/.gitlab-ci.yml",
                    method="POST",
                    data={
                        "branch": "main",
                        "content": json.dumps(ci_config, indent=2),
                        "commit_message": "Update CI configuration via DevOps AI System"
                    }
                )
                updated_count += 1
                logger.info(f"Updated CI configuration for project {project['name']}")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 400:
                    # File already exists, update it
                    try:
                        make_gitlab_request(
                            f"projects/{project_id}/repository/files/.gitlab-ci.yml",
                            method="PUT",
                            data={
                                "branch": "main",
                                "content": json.dumps(ci_config, indent=2),
                                "commit_message": "Update CI configuration via DevOps AI System"
                            }
                        )
                        updated_count += 1
                        logger.info(f"Updated existing CI configuration for project {project['name']}")
                    except Exception as update_error:
                        logger.error(f"Failed to update CI configuration for project {project['name']}: {str(update_error)}")
                else:
                    logger.error(f"Failed to create CI configuration for project {project['name']}: {str(e)}")
        
        return {"status": "success", "updated_projects": updated_count}
    
    except Exception as e:
        logger.error(f"Failed to update CI configurations: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "update_ci_config":
            result = update_ci_config()
            print(json.dumps(result, indent=2))
        else:
            print(f"Unknown command: {command}")
            print("Available commands: update_ci_config")
    else:
        print("Please specify a command")
        print("Available commands: update_ci_config")
