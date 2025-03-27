"""
GitLab Routes - Endpoints for controlling GitLab operations via Flask

This module provides Flask endpoints for interacting with GitLab through the
centralized GitLab controller, which ensures all operations are managed via GitHub Actions.
"""

import os
import json
import logging
from flask import Blueprint, request, jsonify, current_app, abort
from gitlab_controller import GitLabController

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a blueprint for GitLab routes
gitlab_bp = Blueprint('gitlab', __name__, url_prefix='/api/gitlab')

def get_gitlab_token():
    """Get the GitLab API token from environment or app config."""
    # First check environment
    token = os.environ.get('GITLAB_TOKEN')
    
    # If not in environment, check Flask app config
    if not token and current_app:
        token = current_app.config.get('GITLAB_TOKEN')
    
    return token


@gitlab_bp.route('/projects', methods=['GET'])
def get_projects():
    """Get a list of GitLab projects accessible to the current user."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    try:
        controller = GitLabController(token=token)
        projects = controller.get_projects()
        return jsonify(projects)
    except Exception as e:
        logger.error(f"Error getting GitLab projects: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    """Get details for a specific GitLab project."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    try:
        controller = GitLabController(token=token)
        project = controller.get_project(project_id)
        return jsonify(project)
    except Exception as e:
        logger.error(f"Error getting GitLab project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects', methods=['POST'])
def create_project():
    """Create a new GitLab project."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    data = request.json
    if not data or 'name' not in data:
        return jsonify({"error": "Project name is required"}), 400
    
    try:
        controller = GitLabController(token=token)
        project = controller.create_project(
            name=data['name'],
            description=data.get('description', ''),
            visibility=data.get('visibility', 'private')
        )
        return jsonify(project), 201
    except Exception as e:
        logger.error(f"Error creating GitLab project: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/pipelines', methods=['GET'])
def get_pipelines(project_id):
    """Get a list of pipelines for a specific GitLab project."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    try:
        controller = GitLabController(token=token)
        status = request.args.get('status')
        ref = request.args.get('ref')
        pipelines = controller.get_pipelines(
            project_id, 
            status=status,
            ref=ref
        )
        return jsonify(pipelines)
    except Exception as e:
        logger.error(f"Error getting GitLab pipelines for project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/pipelines', methods=['POST'])
def trigger_pipeline(project_id):
    """Trigger a pipeline for a specific GitLab project."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    data = request.json or {}
    ref = data.get('ref', 'main')
    variables = data.get('variables')
    
    try:
        controller = GitLabController(token=token)
        pipeline = controller.trigger_pipeline(
            project_id,
            ref=ref,
            variables=variables
        )
        return jsonify(pipeline), 201
    except Exception as e:
        logger.error(f"Error triggering GitLab pipeline for project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/pipelines/<pipeline_id>', methods=['GET'])
def get_pipeline(project_id, pipeline_id):
    """Get details for a specific pipeline in a GitLab project."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    try:
        controller = GitLabController(token=token)
        pipeline = controller.get_pipeline(project_id, pipeline_id)
        return jsonify(pipeline)
    except Exception as e:
        logger.error(f"Error getting GitLab pipeline {pipeline_id} for project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/pipelines/<pipeline_id>/jobs', methods=['GET'])
def get_pipeline_jobs(project_id, pipeline_id):
    """Get jobs for a specific pipeline in a GitLab project."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    try:
        controller = GitLabController(token=token)
        jobs = controller.get_pipeline_jobs(project_id, pipeline_id)
        return jsonify(jobs)
    except Exception as e:
        logger.error(f"Error getting jobs for GitLab pipeline {pipeline_id} in project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/pipelines/<pipeline_id>/cancel', methods=['POST'])
def cancel_pipeline(project_id, pipeline_id):
    """Cancel a specific pipeline in a GitLab project."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    try:
        controller = GitLabController(token=token)
        result = controller.cancel_pipeline(project_id, pipeline_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error canceling GitLab pipeline {pipeline_id} in project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/pipelines/<pipeline_id>/retry', methods=['POST'])
def retry_pipeline(project_id, pipeline_id):
    """Retry a specific pipeline in a GitLab project."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    try:
        controller = GitLabController(token=token)
        result = controller.retry_pipeline(project_id, pipeline_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error retrying GitLab pipeline {pipeline_id} in project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/files/<path:file_path>', methods=['GET'])
def get_file_content(project_id, file_path):
    """Get the content of a file from a GitLab repository."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    ref = request.args.get('ref', 'main')
    
    try:
        controller = GitLabController(token=token)
        content = controller.get_file_content(project_id, file_path, ref=ref)
        
        if content is None:
            return jsonify({"error": "File not found"}), 404
        
        return jsonify({"content": content})
    except Exception as e:
        logger.error(f"Error getting file {file_path} from GitLab project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/files/<path:file_path>', methods=['PUT'])
def update_file(project_id, file_path):
    """Update a file in a GitLab repository."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    data = request.json
    if not data or 'content' not in data:
        return jsonify({"error": "File content is required"}), 400
    
    content = data['content']
    commit_message = data.get('commit_message', f"Update {file_path} via API")
    branch = data.get('branch', 'main')
    
    try:
        controller = GitLabController(token=token)
        result = controller.create_or_update_file(
            project_id,
            file_path,
            content,
            commit_message,
            branch=branch
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error updating file {file_path} in GitLab project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/files/<path:file_path>', methods=['DELETE'])
def delete_file(project_id, file_path):
    """Delete a file from a GitLab repository."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    data = request.json or {}
    commit_message = data.get('commit_message', f"Delete {file_path} via API")
    branch = data.get('branch', 'main')
    
    try:
        controller = GitLabController(token=token)
        result = controller.delete_file(
            project_id,
            file_path,
            commit_message,
            branch=branch
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error deleting file {file_path} from GitLab project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/tree', methods=['GET'])
def get_repository_tree(project_id):
    """Get a list of files and directories in a repository tree."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    path = request.args.get('path', '')
    ref = request.args.get('ref', 'main')
    recursive = request.args.get('recursive', 'false').lower() == 'true'
    
    try:
        controller = GitLabController(token=token)
        tree = controller.get_repository_tree(
            project_id,
            path=path,
            ref=ref,
            recursive=recursive
        )
        return jsonify(tree)
    except Exception as e:
        logger.error(f"Error getting repository tree for GitLab project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/ci/setup', methods=['POST'])
def setup_ci_cd(project_id):
    """Set up GitLab CI/CD for a project with a provided configuration."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    data = request.json
    if not data or 'content' not in data:
        return jsonify({"error": "CI/CD configuration content is required"}), 400
    
    ci_config_content = data['content']
    
    try:
        controller = GitLabController(token=token)
        result = controller.setup_gitlab_ci_cd(project_id, ci_config_content)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error setting up CI/CD for GitLab project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/pages/setup', methods=['POST'])
def setup_pages(project_id):
    """Set up GitLab Pages for a project with a provided index.html."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    data = request.json
    if not data or 'content' not in data:
        return jsonify({"error": "HTML content is required"}), 400
    
    index_html_content = data['content']
    
    try:
        controller = GitLabController(token=token)
        result = controller.setup_gitlab_pages(project_id, index_html_content)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error setting up GitLab Pages for project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/sync-github', methods=['POST'])
def sync_github_repo(project_id):
    """Sync a GitHub repository to GitLab."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    data = request.json
    if not data or 'github_repo' not in data:
        return jsonify({"error": "GitHub repository is required"}), 400
    
    github_repo = data['github_repo']
    github_branch = data.get('github_branch', 'main')
    
    try:
        controller = GitLabController(token=token)
        result = controller.sync_github_repo_to_gitlab(
            project_id,
            github_repo,
            github_branch=github_branch
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error syncing GitHub repository to GitLab project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/environments', methods=['GET'])
def get_environments(project_id):
    """Get a list of environments for a GitLab project."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    try:
        controller = GitLabController(token=token)
        environments = controller.get_environments(project_id)
        return jsonify(environments)
    except Exception as e:
        logger.error(f"Error getting environments for GitLab project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/environments', methods=['POST'])
def create_environment(project_id):
    """Create a new environment for a GitLab project."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    data = request.json
    if not data or 'name' not in data:
        return jsonify({"error": "Environment name is required"}), 400
    
    name = data['name']
    external_url = data.get('external_url')
    
    try:
        controller = GitLabController(token=token)
        environment = controller.create_environment(
            project_id,
            name,
            external_url=external_url
        )
        return jsonify(environment), 201
    except Exception as e:
        logger.error(f"Error creating environment for GitLab project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@gitlab_bp.route('/projects/<project_id>/deployments', methods=['GET'])
def get_deployments(project_id):
    """Get a list of deployments for a GitLab project."""
    token = get_gitlab_token()
    if not token:
        return jsonify({
            "error": "GitLab token not found",
            "message": "GitLab authentication token is missing. Please configure it in the application."
        }), 401
    
    environment = request.args.get('environment')
    
    try:
        controller = GitLabController(token=token)
        deployments = controller.get_deployments(
            project_id,
            environment=environment
        )
        return jsonify(deployments)
    except Exception as e:
        logger.error(f"Error getting deployments for GitLab project {project_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Function to register the blueprint to the main Flask app
def register_gitlab_routes(app):
    """Register the GitLab routes blueprint to the main Flask app."""
    app.register_blueprint(gitlab_bp)
    
    # Make the GitLab token available in app config if it's in the environment
    if 'GITLAB_TOKEN' in os.environ and not app.config.get('GITLAB_TOKEN'):
        app.config['GITLAB_TOKEN'] = os.environ.get('GITLAB_TOKEN')
    
    return app