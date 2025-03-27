#!/usr/bin/env python3
"""
GitHub-GitLab Integration Bridge

This script serves as a bridge between GitHub and GitLab, allowing bidirectional
communication between the two platforms. It can be called from GitHub Actions or
GitLab CI/CD pipelines to trigger events on the other platform.

Usage:
    python github_gitlab_bridge.py [options]

Options:
    --direction=<direction>       Direction of the bridge: github-to-gitlab or gitlab-to-github
    --action=<action>             Action to perform: trigger-pipeline, update-status, sync-repo
    --github-token=<token>        GitHub API token (or set GITHUB_TOKEN env var)
    --gitlab-token=<token>        GitLab API token (or set GITLAB_TOKEN env var)
    --github-repo=<repo>          GitHub repository in the format "owner/repo"
    --gitlab-project=<project>    GitLab project ID or path

Example:
    python github_gitlab_bridge.py --direction=github-to-gitlab --action=trigger-pipeline \\
        --github-token=xyz --gitlab-token=abc --gitlab-project=12345
"""

import os
import sys
import json
import logging
import argparse
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("github-gitlab-bridge")

# Base URLs for APIs
GITHUB_API_BASE_URL = "https://api.github.com"
GITLAB_API_BASE_URL = "https://gitlab.com/api/v4"

def get_github_token(args):
    """Get GitHub API token from args or environment variables."""
    token = args.github_token or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GitHub API token not provided in args or environment")
    return token

def get_gitlab_token(args):
    """Get GitLab API token from args or environment variables."""
    token = args.gitlab_token or os.environ.get("GITLAB_TOKEN")
    if not token:
        raise ValueError("GitLab API token not provided in args or environment")
    return token

def make_github_request(endpoint, token, method="GET", data=None, params=None):
    """Make a request to the GitHub API."""
    url = f"{GITHUB_API_BASE_URL}/{endpoint}"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    try:
        response = None
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
        return response.json() if response.content else {}
    
    except requests.exceptions.RequestException as e:
        logger.error(f"GitHub API request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
            logger.error(f"Response content: {e.response.text}")
        raise

def make_gitlab_request(endpoint, token, method="GET", data=None, params=None):
    """Make a request to the GitLab API."""
    url = f"{GITLAB_API_BASE_URL}/{endpoint}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = None
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
        return response.json() if response.content else {}
    
    except requests.exceptions.RequestException as e:
        logger.error(f"GitLab API request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
            logger.error(f"Response content: {e.response.text}")
        raise

def github_to_gitlab_trigger_pipeline(args):
    """Trigger a GitLab CI/CD pipeline from GitHub."""
    logger.info("Triggering GitLab pipeline from GitHub...")
    
    github_token = get_github_token(args)
    gitlab_token = get_gitlab_token(args)
    gitlab_project = args.gitlab_project
    
    if not gitlab_project:
        # Try to find a GitLab project with a similar name to the GitHub repo
        github_repo = args.github_repo or os.environ.get("GITHUB_REPOSITORY", "")
        if github_repo:
            # Extract the repo name without owner
            repo_name = github_repo.split("/")[-1] if "/" in github_repo else github_repo
            
            # Search for GitLab projects
            try:
                projects = make_gitlab_request(
                    "projects", 
                    gitlab_token, 
                    params={"search": repo_name, "membership": True}
                )
                
                if projects:
                    gitlab_project = projects[0]["id"]
                    logger.info(f"Found GitLab project with ID {gitlab_project} matching GitHub repo {repo_name}")
                else:
                    logger.warning(f"No matching GitLab project found for GitHub repo {repo_name}")
            except Exception as e:
                logger.error(f"Failed to search for GitLab projects: {str(e)}")
    
    if not gitlab_project:
        raise ValueError("GitLab project ID not provided")
    
    # Get GitHub run information if available
    github_workflow = os.environ.get("GITHUB_WORKFLOW", "unknown")
    github_run_id = os.environ.get("GITHUB_RUN_ID", "unknown")
    github_run_number = os.environ.get("GITHUB_RUN_NUMBER", "unknown")
    
    # Trigger the GitLab pipeline
    try:
        # First try with variables
        try:
            result = make_gitlab_request(
                f"projects/{gitlab_project}/pipeline",
                gitlab_token,
                method="POST",
                data={
                    "ref": "main",
                    "variables": [
                        {"key": "GITHUB_INTEGRATION", "value": "true"},
                        {"key": "GITHUB_WORKFLOW", "value": github_workflow},
                        {"key": "GITHUB_RUN_ID", "value": github_run_id},
                        {"key": "GITHUB_RUN_NUMBER", "value": github_run_number},
                        {"key": "GITHUB_REPOSITORY", "value": args.github_repo or os.environ.get("GITHUB_REPOSITORY", "")}
                    ]
                }
            )
        except requests.exceptions.RequestException as e:
            # If we got a permission error about variables, try without them
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 400 and "Insufficient permissions to set pipeline variables" in e.response.text:
                logger.warning("No permission to set pipeline variables, trying without variables...")
                result = make_gitlab_request(
                    f"projects/{gitlab_project}/pipeline",
                    gitlab_token, 
                    method="POST",
                    data={"ref": "main"}
                )
            else:
                # Re-raise if it's not the specific permission error we're handling
                raise
        
        logger.info(f"Successfully triggered GitLab pipeline: {result.get('id', 'N/A')}")
        logger.info(f"Pipeline URL: {result.get('web_url', 'N/A')}")
        
        # Update GitHub status
        if args.github_repo:
            try:
                # Get the latest commit SHA
                repo_info = make_github_request(
                    f"repos/{args.github_repo}/commits",
                    github_token,
                    params={"per_page": 1}
                )
                
                if repo_info and isinstance(repo_info, list) and len(repo_info) > 0:
                    commit_sha = repo_info[0]["sha"]
                    
                    # Create a commit status
                    status_result = make_github_request(
                        f"repos/{args.github_repo}/statuses/{commit_sha}",
                        github_token,
                        method="POST",
                        data={
                            "state": "success",
                            "target_url": result.get("web_url", ""),
                            "description": f"GitLab pipeline #{result.get('id', 'N/A')} triggered",
                            "context": "gitlab-ci/pipeline"
                        }
                    )
                    
                    logger.info(f"Updated GitHub commit status for {commit_sha}")
            except Exception as e:
                logger.error(f"Failed to update GitHub commit status: {str(e)}")
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to trigger GitLab pipeline: {str(e)}")
        raise

def gitlab_to_github_dispatch(args):
    """Trigger a GitHub repository dispatch event from GitLab."""
    logger.info("Triggering GitHub repository dispatch from GitLab...")
    
    github_token = get_github_token(args)
    github_repo = args.github_repo
    
    if not github_repo:
        raise ValueError("GitHub repository not provided")
    
    # Get GitLab pipeline information if available
    gitlab_pipeline_id = os.environ.get("CI_PIPELINE_ID", "unknown")
    gitlab_project_id = os.environ.get("CI_PROJECT_ID", args.gitlab_project or "unknown")
    gitlab_job_id = os.environ.get("CI_JOB_ID", "unknown")
    
    # Trigger the GitHub repository dispatch event
    try:
        result = make_github_request(
            f"repos/{github_repo}/dispatches",
            github_token,
            method="POST",
            data={
                "event_type": "gitlab_ci_completed",
                "client_payload": {
                    "gitlab_pipeline_id": gitlab_pipeline_id,
                    "gitlab_project_id": gitlab_project_id,
                    "gitlab_job_id": gitlab_job_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
        
        logger.info(f"Successfully triggered GitHub repository dispatch for {github_repo}")
        
        return {"status": "success", "message": "GitHub repository dispatch triggered"}
    
    except Exception as e:
        logger.error(f"Failed to trigger GitHub repository dispatch: {str(e)}")
        raise

def sync_github_repo_to_gitlab(args):
    """Sync a GitHub repository to GitLab."""
    logger.info("Syncing GitHub repository to GitLab...")
    
    github_token = get_github_token(args)
    gitlab_token = get_gitlab_token(args)
    github_repo = args.github_repo
    gitlab_project = args.gitlab_project
    
    if not github_repo:
        raise ValueError("GitHub repository not provided")
    
    if not gitlab_project:
        raise ValueError("GitLab project ID not provided")
    
    # Get GitHub repository information
    try:
        github_repo_info = make_github_request(
            f"repos/{github_repo}",
            github_token
        )
        
        # Update GitLab project description to include GitHub info
        project_data = {
            "description": f"Synced from GitHub: {github_repo} | {github_repo_info.get('description', 'No description')}",
        }
        
        # Update GitLab project
        result = make_gitlab_request(
            f"projects/{gitlab_project}",
            gitlab_token,
            method="PUT",
            data=project_data
        )
        
        logger.info(f"Successfully synced GitHub repository info to GitLab project {gitlab_project}")
        
        # Create or update a file in GitLab to store GitHub sync status
        try:
            # Create JSON content with sync info
            sync_info = {
                "github_repository": github_repo,
                "github_default_branch": github_repo_info.get("default_branch", "main"),
                "last_synced": datetime.utcnow().isoformat(),
                "sync_status": "success"
            }
            
            # Base64 encode the content
            import base64
            content = base64.b64encode(json.dumps(sync_info, indent=2).encode()).decode()
            
            # Try to update the file if it exists, otherwise create it
            try:
                # Check if file exists
                make_gitlab_request(
                    f"projects/{gitlab_project}/repository/files/github-sync-info.json",
                    gitlab_token,
                    params={"ref": "main"}
                )
                
                # Update file
                make_gitlab_request(
                    f"projects/{gitlab_project}/repository/files/github-sync-info.json",
                    gitlab_token,
                    method="PUT",
                    data={
                        "branch": "main",
                        "content": json.dumps(sync_info, indent=2),
                        "commit_message": "Update GitHub sync information"
                    }
                )
            except:
                # Create file
                make_gitlab_request(
                    f"projects/{gitlab_project}/repository/files/github-sync-info.json",
                    gitlab_token,
                    method="POST",
                    data={
                        "branch": "main",
                        "content": json.dumps(sync_info, indent=2),
                        "commit_message": "Add GitHub sync information"
                    }
                )
            
            logger.info("Successfully saved GitHub sync information to GitLab repository")
        except Exception as e:
            logger.error(f"Failed to save GitHub sync information to GitLab repository: {str(e)}")
        
        return {"status": "success", "message": "GitHub repository synced to GitLab"}
    
    except Exception as e:
        logger.error(f"Failed to sync GitHub repository to GitLab: {str(e)}")
        raise

def update_github_status_from_gitlab(args):
    """Update GitHub commit status based on GitLab CI/CD pipeline status."""
    logger.info("Updating GitHub commit status from GitLab...")
    
    github_token = get_github_token(args)
    gitlab_token = get_gitlab_token(args)
    github_repo = args.github_repo
    gitlab_project = args.gitlab_project
    
    if not github_repo:
        raise ValueError("GitHub repository not provided")
    
    if not gitlab_project:
        raise ValueError("GitLab project ID not provided")
    
    # Get GitLab pipeline information
    pipeline_id = os.environ.get("CI_PIPELINE_ID")
    if not pipeline_id:
        raise ValueError("GitLab pipeline ID not found in environment variables")
    
    try:
        # Get pipeline details
        pipeline = make_gitlab_request(
            f"projects/{gitlab_project}/pipelines/{pipeline_id}",
            gitlab_token
        )
        
        # Get latest commit SHA from GitHub
        commits = make_github_request(
            f"repos/{github_repo}/commits",
            github_token,
            params={"per_page": 1}
        )
        
        if not commits or not isinstance(commits, list) or len(commits) == 0:
            raise ValueError("No commits found in GitHub repository")
        
        commit_sha = commits[0]["sha"]
        
        # Map GitLab pipeline status to GitHub commit status
        status_map = {
            "running": "pending",
            "pending": "pending",
            "success": "success",
            "failed": "failure",
            "canceled": "error"
        }
        
        github_status = status_map.get(pipeline.get("status", ""), "error")
        
        # Update GitHub commit status
        make_github_request(
            f"repos/{github_repo}/statuses/{commit_sha}",
            github_token,
            method="POST",
            data={
                "state": github_status,
                "target_url": pipeline.get("web_url", ""),
                "description": f"GitLab CI pipeline #{pipeline_id} {pipeline.get('status', 'unknown')}",
                "context": "gitlab-ci/pipeline"
            }
        )
        
        logger.info(f"Successfully updated GitHub commit status to {github_status} for {commit_sha}")
        
        return {
            "status": "success", 
            "message": f"GitHub commit status updated to {github_status}",
            "github_repo": github_repo,
            "github_commit": commit_sha,
            "gitlab_pipeline": pipeline_id,
            "gitlab_status": pipeline.get("status")
        }
    
    except Exception as e:
        logger.error(f"Failed to update GitHub commit status: {str(e)}")
        raise

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="GitHub-GitLab Integration Bridge"
    )
    
    parser.add_argument(
        "--direction",
        choices=["github-to-gitlab", "gitlab-to-github"],
        required=True,
        help="Direction of the bridge operation"
    )
    
    parser.add_argument(
        "--action",
        choices=["trigger-pipeline", "update-status", "sync-repo"],
        required=True,
        help="Action to perform"
    )
    
    parser.add_argument(
        "--github-token",
        help="GitHub API token (or set GITHUB_TOKEN env var)"
    )
    
    parser.add_argument(
        "--gitlab-token",
        help="GitLab API token (or set GITLAB_TOKEN env var)"
    )
    
    parser.add_argument(
        "--github-repo",
        help="GitHub repository in the format 'owner/repo'"
    )
    
    parser.add_argument(
        "--gitlab-project",
        help="GitLab project ID or path"
    )
    
    return parser.parse_args()

def main():
    """Main function for the GitHub-GitLab integration bridge."""
    args = parse_arguments()
    
    try:
        if args.direction == "github-to-gitlab" and args.action == "trigger-pipeline":
            result = github_to_gitlab_trigger_pipeline(args)
        elif args.direction == "gitlab-to-github" and args.action == "trigger-pipeline":
            result = gitlab_to_github_dispatch(args)
        elif args.direction == "github-to-gitlab" and args.action == "sync-repo":
            result = sync_github_repo_to_gitlab(args)
        elif args.direction == "gitlab-to-github" and args.action == "update-status":
            result = update_github_status_from_gitlab(args)
        else:
            logger.error(f"Unsupported combination: direction={args.direction}, action={args.action}")
            return 1
        
        # Print the result as JSON
        print(json.dumps(result, indent=2))
        return 0
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())