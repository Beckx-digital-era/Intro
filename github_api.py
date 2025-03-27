import os
import requests
import logging
import json
from flask import current_app

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Base URL for GitHub API
GITHUB_API_BASE_URL = "https://api.github.com"

def get_github_token():
    """Get the GitHub API token from the environment or the Flask app config."""
    token = os.environ.get("GITHUB_TOKEN")
    
    # Alternative environment variable names
    if not token:
        token = os.environ.get("GH_TOKEN")
    
    # If not found in environment, try to get from Flask app config
    if not token:
        try:
            if current_app:
                token = current_app.config.get("GITHUB_TOKEN")
        except RuntimeError:
            # This happens when outside of Flask context
            pass
    
    if not token:
        logger.error("GitHub API token not found in environment variables or app config")
        raise ValueError("GitHub API token not found in environment variables or app config")
    
    return token

def make_github_request(endpoint, method="GET", data=None, params=None):
    """Make a request to the GitHub API."""
    token = get_github_token()
    url = f"{GITHUB_API_BASE_URL}/{endpoint}"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"GitHub API request failed: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            logger.error(f"Response content: {e.response.text}")
        raise

def get_github_repositories():
    """Get a list of repositories for the authenticated user."""
    return make_github_request("user/repos")

def get_github_repository(owner, repo):
    """Get details for a specific GitHub repository."""
    return make_github_request(f"repos/{owner}/{repo}")

def create_github_repository(name, description="", private=False):
    """Create a new GitHub repository."""
    return make_github_request(
        "user/repos",
        method="POST",
        data={
            "name": name,
            "description": description,
            "private": private,
            "auto_init": True  # Initialize with a README
        }
    )

def get_github_workflows(owner, repo):
    """Get workflows for a specific GitHub repository."""
    return make_github_request(f"repos/{owner}/{repo}/actions/workflows")

def get_github_workflow_runs(owner, repo, workflow_id):
    """Get runs for a specific GitHub workflow."""
    return make_github_request(f"repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs")

def create_github_workflow(owner, repo, workflow_name, workflow_content):
    """Create a new GitHub workflow file in the repository."""
    # Encode content to base64
    import base64
    encoded_content = base64.b64encode(workflow_content.encode()).decode()
    
    return make_github_request(
        f"repos/{owner}/{repo}/contents/.github/workflows/{workflow_name}.yml",
        method="PUT",
        data={
            "message": f"Add {workflow_name} workflow",
            "content": encoded_content
        }
    )

def get_github_pages_status(owner, repo):
    """Get the GitHub Pages status for a repository."""
    try:
        return make_github_request(f"repos/{owner}/{repo}/pages")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # GitHub Pages not enabled
            return {"status": "not_enabled"}
        raise

def enable_github_pages(owner, repo, branch="main"):
    """Enable GitHub Pages for a repository."""
    return make_github_request(
        f"repos/{owner}/{repo}/pages",
        method="POST",
        data={
            "source": {
                "branch": branch,
                "path": "/"
            }
        }
    )

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list_repos":
            repos = get_github_repositories()
            print(json.dumps(repos, indent=2))
        else:
            print(f"Unknown command: {command}")
            print("Available commands: list_repos")
    else:
        print("Please specify a command")
        print("Available commands: list_repos")