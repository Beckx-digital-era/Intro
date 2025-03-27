"""
GitLab Controller - Centralized control of GitLab operations via GitHub Actions

This module provides a centralized way to control all GitLab operations from GitHub Actions.
It handles all GitLab API interactions and ensures all GitLab capabilities are controlled by GitHub.
"""

import os
import sys
import json
import logging
import requests
import argparse
import base64
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('gitlab-controller')

class GitLabController:
    """GitLab Controller for managing all GitLab operations from GitHub Actions."""
    
    def __init__(self, token=None):
        """Initialize the GitLab controller with API token."""
        self.token = token or os.environ.get('GITLAB_TOKEN')
        if not self.token:
            raise ValueError("GitLab token is required. Set environment variable GITLAB_TOKEN or pass token parameter.")
        
        self.api_url = "https://gitlab.com/api/v4"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, endpoint, method="GET", data=None, params=None, raw_response=False):
        """Make a request to the GitLab API with proper error handling."""
        url = f"{self.api_url}/{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data if data and method != "GET" else None,
                params=params,
                timeout=30
            )
            
            # Log request details for debugging (without sensitive info)
            logger.debug(f"GitLab API Request: {method} {url}")
            if params:
                logger.debug(f"Params: {json.dumps(params)}")
            
            # Raise exception for error status codes
            response.raise_for_status()
            
            # Return raw response if requested
            if raw_response:
                return response
            
            # Return JSON response for successful requests
            if response.status_code != 204:  # No content
                return response.json()
            return {"status": "success"}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GitLab API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise
    
    def get_projects(self, membership=True, search=None):
        """Get a list of GitLab projects accessible to the current user."""
        params = {"membership": membership}
        if search:
            params["search"] = search
        
        return self._make_request("projects", params=params)
    
    def get_project(self, project_id):
        """Get details for a specific GitLab project."""
        return self._make_request(f"projects/{project_id}")
    
    def create_project(self, name, description="", visibility="private"):
        """Create a new GitLab project."""
        data = {
            "name": name,
            "description": description,
            "visibility": visibility
        }
        
        return self._make_request("projects", method="POST", data=data)
    
    def update_project(self, project_id, data):
        """Update a GitLab project with the provided data."""
        return self._make_request(f"projects/{project_id}", method="PUT", data=data)
    
    def trigger_pipeline(self, project_id, ref="main", variables=None):
        """Trigger a pipeline for a specific GitLab project with optional variables."""
        data = {"ref": ref}
        
        if variables:
            try:
                data["variables"] = variables
                return self._make_request(f"projects/{project_id}/pipeline", method="POST", data=data)
            except requests.exceptions.RequestException as e:
                # If we got a permission error about variables, try without them
                if (hasattr(e, 'response') and e.response is not None and 
                    e.response.status_code == 400 and 
                    "Insufficient permissions to set pipeline variables" in e.response.text):
                    logger.warning("No permission to set pipeline variables, trying without variables...")
                    data.pop("variables", None)
                    return self._make_request(f"projects/{project_id}/pipeline", method="POST", data=data)
                else:
                    # Re-raise if it's not the specific permission error we're handling
                    raise
        else:
            return self._make_request(f"projects/{project_id}/pipeline", method="POST", data=data)
    
    def get_pipelines(self, project_id, status=None, ref=None, order_by="id", sort="desc"):
        """Get a list of pipelines for a specific GitLab project with filtering options."""
        params = {"order_by": order_by, "sort": sort}
        if status:
            params["status"] = status
        if ref:
            params["ref"] = ref
        
        return self._make_request(f"projects/{project_id}/pipelines", params=params)
    
    def get_pipeline(self, project_id, pipeline_id):
        """Get details for a specific pipeline in a GitLab project."""
        return self._make_request(f"projects/{project_id}/pipelines/{pipeline_id}")
    
    def get_pipeline_jobs(self, project_id, pipeline_id):
        """Get jobs for a specific pipeline in a GitLab project."""
        return self._make_request(f"projects/{project_id}/pipelines/{pipeline_id}/jobs")
    
    def cancel_pipeline(self, project_id, pipeline_id):
        """Cancel a specific pipeline in a GitLab project."""
        return self._make_request(f"projects/{project_id}/pipelines/{pipeline_id}/cancel", method="POST")
    
    def retry_pipeline(self, project_id, pipeline_id):
        """Retry a specific pipeline in a GitLab project."""
        return self._make_request(f"projects/{project_id}/pipelines/{pipeline_id}/retry", method="POST")
    
    def get_file_content(self, project_id, file_path, ref="main"):
        """Get the content of a file from a GitLab repository."""
        try:
            response = self._make_request(
                f"projects/{project_id}/repository/files/{file_path}",
                params={"ref": ref}
            )
            
            # GitLab returns the content as base64 encoded
            return base64.b64decode(response.get("content", "")).decode("utf-8")
            
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
                return None
            raise
    
    def create_or_update_file(self, project_id, file_path, content, commit_message, branch="main"):
        """Create or update a file in a GitLab repository."""
        # First check if file exists
        file_exists = False
        try:
            self._make_request(
                f"projects/{project_id}/repository/files/{file_path}",
                params={"ref": branch}
            )
            file_exists = True
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response.status_code == 404:
                pass  # File doesn't exist, that's fine
            else:
                raise
        
        # Encode content as base64
        content_encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        
        # Create or update the file
        method = "PUT" if file_exists else "POST"
        return self._make_request(
            f"projects/{project_id}/repository/files/{file_path}",
            method=method,
            data={
                "branch": branch,
                "content": content,
                "commit_message": commit_message,
                "encoding": "text"
            }
        )
    
    def delete_file(self, project_id, file_path, commit_message, branch="main"):
        """Delete a file from a GitLab repository."""
        return self._make_request(
            f"projects/{project_id}/repository/files/{file_path}",
            method="DELETE",
            data={
                "branch": branch,
                "commit_message": commit_message
            }
        )
    
    def get_repository_tree(self, project_id, path="", ref="main", recursive=False):
        """Get a list of files and directories in a repository tree."""
        params = {
            "path": path,
            "ref": ref,
            "recursive": recursive
        }
        
        return self._make_request(f"projects/{project_id}/repository/tree", params=params)
    
    def get_environments(self, project_id):
        """Get a list of environments for a GitLab project."""
        return self._make_request(f"projects/{project_id}/environments")
    
    def create_environment(self, project_id, name, external_url=None):
        """Create a new environment for a GitLab project."""
        data = {"name": name}
        if external_url:
            data["external_url"] = external_url
        
        return self._make_request(f"projects/{project_id}/environments", method="POST", data=data)
    
    def get_deployments(self, project_id, environment=None):
        """Get a list of deployments for a GitLab project."""
        params = {}
        if environment:
            params["environment"] = environment
        
        return self._make_request(f"projects/{project_id}/deployments", params=params)
    
    def create_deployment(self, project_id, environment, ref="main", status="success"):
        """Create a new deployment for a GitLab project."""
        data = {
            "environment": environment,
            "ref": ref,
            "status": status
        }
        
        return self._make_request(f"projects/{project_id}/deployments", method="POST", data=data)
    
    def update_deployment(self, project_id, deployment_id, status):
        """Update the status of a deployment in a GitLab project."""
        return self._make_request(
            f"projects/{project_id}/deployments/{deployment_id}",
            method="PUT",
            data={"status": status}
        )
    
    def sync_github_repo_to_gitlab(self, project_id, github_repo, github_branch="main"):
        """Sync a GitHub repository to GitLab."""
        logger.info(f"Syncing GitHub repository {github_repo} to GitLab project {project_id}...")
        
        # Update GitLab project description to include GitHub info
        try:
            # Get GitHub repository information via environment variables or passed info
            github_repo_name = github_repo.split("/")[-1] if github_repo else "unknown"
            
            # Update GitLab project description
            project_data = {
                "description": f"Synced from GitHub: {github_repo} | Managed by GitHub Actions"
            }
            
            # Update GitLab project
            self.update_project(project_id, project_data)
            
            logger.info(f"Successfully synced GitHub repository info to GitLab project {project_id}")
            
            # Create or update a file in GitLab to store GitHub sync status
            try:
                # Create JSON content with sync info
                sync_info = {
                    "github_repository": github_repo,
                    "github_default_branch": github_branch,
                    "last_synced": datetime.utcnow().isoformat(),
                    "sync_status": "success",
                    "github_actions_managed": True
                }
                
                # Create or update the file in GitLab
                self.create_or_update_file(
                    project_id,
                    "github-sync-info.json",
                    json.dumps(sync_info, indent=2),
                    "Update GitHub sync information via GitHub Actions controller"
                )
                
                logger.info("Successfully saved GitHub sync information to GitLab repository")
            except Exception as e:
                logger.error(f"Failed to save GitHub sync information to GitLab repository: {str(e)}")
            
            return {
                "status": "success",
                "message": "GitHub repository synced to GitLab",
                "project_id": project_id,
                "github_repo": github_repo
            }
            
        except Exception as e:
            logger.error(f"Failed to sync GitHub repository to GitLab: {str(e)}")
            raise
    
    def setup_gitlab_ci_cd(self, project_id, ci_config_content):
        """Set up GitLab CI/CD for a project with a provided configuration."""
        logger.info(f"Setting up GitLab CI/CD for project {project_id}...")
        
        try:
            # Create or update .gitlab-ci.yml
            self.create_or_update_file(
                project_id,
                ".gitlab-ci.yml",
                ci_config_content,
                "Update GitLab CI configuration via GitHub Actions controller"
            )
            
            logger.info(f"Successfully set up GitLab CI/CD for project {project_id}")
            
            return {"status": "success", "message": "GitLab CI/CD configured successfully"}
            
        except Exception as e:
            logger.error(f"Failed to set up GitLab CI/CD: {str(e)}")
            raise
    
    def setup_gitlab_pages(self, project_id, index_html_content):
        """Set up GitLab Pages for a project with a provided index.html."""
        logger.info(f"Setting up GitLab Pages for project {project_id}...")
        
        try:
            # Create public directory structure if it doesn't exist
            # We'll create an empty .gitkeep file in the public directory
            try:
                self.create_or_update_file(
                    project_id,
                    "public/.gitkeep",
                    "",
                    "Create public directory for GitLab Pages"
                )
            except Exception as e:
                logger.warning(f"Failed to create public directory: {str(e)}")
            
            # Create or update index.html in the public directory
            self.create_or_update_file(
                project_id,
                "public/index.html",
                index_html_content,
                "Update GitLab Pages via GitHub Actions controller"
            )
            
            logger.info(f"Successfully set up GitLab Pages for project {project_id}")
            
            return {"status": "success", "message": "GitLab Pages configured successfully"}
            
        except Exception as e:
            logger.error(f"Failed to set up GitLab Pages: {str(e)}")
            raise


def parse_arguments():
    """Parse command-line arguments for the GitLab controller."""
    parser = argparse.ArgumentParser(
        description="GitLab Controller for GitHub Actions"
    )
    
    parser.add_argument(
        "--action",
        choices=[
            "get-projects", "get-project", "create-project", "update-project",
            "trigger-pipeline", "get-pipelines", "get-pipeline", "cancel-pipeline", "retry-pipeline",
            "get-file", "update-file", "delete-file", "get-tree",
            "setup-ci-cd", "setup-pages", "sync-github-repo",
            "get-environments", "create-environment", "get-deployments"
        ],
        required=True,
        help="Action to perform on GitLab"
    )
    
    parser.add_argument(
        "--gitlab-token",
        help="GitLab API token (or set GITLAB_TOKEN env var)"
    )
    
    parser.add_argument(
        "--project-id",
        help="GitLab project ID or path"
    )
    
    parser.add_argument(
        "--github-repo",
        help="GitHub repository in the format 'owner/repo'"
    )
    
    parser.add_argument(
        "--file-path",
        help="Path to a file in the GitLab repository"
    )
    
    parser.add_argument(
        "--content",
        help="Content for file creation or update"
    )
    
    parser.add_argument(
        "--ref",
        default="main",
        help="Git reference (branch, tag, or commit)"
    )
    
    parser.add_argument(
        "--input-file",
        help="Path to a local file containing input data (like CI config)"
    )
    
    parser.add_argument(
        "--name",
        help="Name for a project, environment, etc."
    )
    
    parser.add_argument(
        "--description",
        help="Description for a project, environment, etc."
    )
    
    parser.add_argument(
        "--environment",
        help="GitLab environment name"
    )
    
    parser.add_argument(
        "--status",
        help="Status for deployments, pipelines, etc."
    )
    
    parser.add_argument(
        "--variables",
        help="JSON string of variables for pipeline triggers"
    )
    
    return parser.parse_args()


def main():
    """Main function for the GitLab controller."""
    args = parse_arguments()
    
    try:
        # Initialize the GitLab controller
        controller = GitLabController(token=args.gitlab_token)
        
        # Execute the requested action
        if args.action == "get-projects":
            result = controller.get_projects()
        
        elif args.action == "get-project":
            if not args.project_id:
                raise ValueError("project-id is required for get-project action")
            result = controller.get_project(args.project_id)
        
        elif args.action == "create-project":
            if not args.name:
                raise ValueError("name is required for create-project action")
            result = controller.create_project(args.name, description=args.description or "")
        
        elif args.action == "update-project":
            if not args.project_id:
                raise ValueError("project-id is required for update-project action")
            
            # Parse data for project update from input file or command line
            if args.input_file:
                with open(args.input_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {}
                if args.name:
                    data["name"] = args.name
                if args.description:
                    data["description"] = args.description
            
            result = controller.update_project(args.project_id, data)
        
        elif args.action == "trigger-pipeline":
            if not args.project_id:
                raise ValueError("project-id is required for trigger-pipeline action")
            
            variables = None
            if args.variables:
                try:
                    variables = json.loads(args.variables)
                except json.JSONDecodeError:
                    raise ValueError("variables must be a valid JSON string")
            
            result = controller.trigger_pipeline(
                args.project_id,
                ref=args.ref,
                variables=variables
            )
        
        elif args.action == "get-pipelines":
            if not args.project_id:
                raise ValueError("project-id is required for get-pipelines action")
            result = controller.get_pipelines(args.project_id, status=args.status, ref=args.ref)
        
        elif args.action == "get-file":
            if not args.project_id or not args.file_path:
                raise ValueError("project-id and file-path are required for get-file action")
            result = {"content": controller.get_file_content(args.project_id, args.file_path, ref=args.ref)}
        
        elif args.action == "update-file":
            if not args.project_id or not args.file_path:
                raise ValueError("project-id and file-path are required for update-file action")
            
            content = args.content
            if args.input_file:
                with open(args.input_file, 'r') as f:
                    content = f.read()
            
            if not content:
                raise ValueError("content or input-file is required for update-file action")
            
            result = controller.create_or_update_file(
                args.project_id,
                args.file_path,
                content,
                f"Update {args.file_path} via GitHub Actions controller"
            )
        
        elif args.action == "setup-ci-cd":
            if not args.project_id:
                raise ValueError("project-id is required for setup-ci-cd action")
            
            ci_config = args.content
            if args.input_file:
                with open(args.input_file, 'r') as f:
                    ci_config = f.read()
            
            if not ci_config:
                raise ValueError("content or input-file is required for setup-ci-cd action")
            
            result = controller.setup_gitlab_ci_cd(args.project_id, ci_config)
        
        elif args.action == "setup-pages":
            if not args.project_id:
                raise ValueError("project-id is required for setup-pages action")
            
            html_content = args.content
            if args.input_file:
                with open(args.input_file, 'r') as f:
                    html_content = f.read()
            
            if not html_content:
                raise ValueError("content or input-file is required for setup-pages action")
            
            result = controller.setup_gitlab_pages(args.project_id, html_content)
        
        elif args.action == "sync-github-repo":
            if not args.project_id or not args.github_repo:
                raise ValueError("project-id and github-repo are required for sync-github-repo action")
            
            result = controller.sync_github_repo_to_gitlab(args.project_id, args.github_repo, args.ref)
        
        elif args.action == "get-environments":
            if not args.project_id:
                raise ValueError("project-id is required for get-environments action")
            
            result = controller.get_environments(args.project_id)
        
        elif args.action == "create-environment":
            if not args.project_id or not args.name:
                raise ValueError("project-id and name are required for create-environment action")
            
            result = controller.create_environment(args.project_id, args.name)
        
        elif args.action == "get-deployments":
            if not args.project_id:
                raise ValueError("project-id is required for get-deployments action")
            
            result = controller.get_deployments(args.project_id, environment=args.environment)
        
        else:
            raise ValueError(f"Unsupported action: {args.action}")
        
        # Print the result as JSON
        print(json.dumps(result, indent=2))
        return 0
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())