"""
DevOps AI Controller

This module provides a centralized AI-powered control system for the DevOps platform.
It uses a local AI model to understand user requests, manage authentication,
and orchestrate operations across GitHub and GitLab platforms.

The controller acts as the top-level intelligence layer that coordinates all platform activities.
"""

import os
import json
import logging
import time
from datetime import datetime
from flask import session, request, jsonify
import random
from ai_model import find_most_similar_query, RESPONSES, process_message

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# No API key required for local AI model
logger.info("Using local AI model for DevOps controller")

# Maximum conversation history to maintain
MAX_CONVERSATION_HISTORY = 20

# Conversation memory storage
conversation_histories = {}


class DevOpsIntelligence:
    """Core intelligence layer for managing DevOps operations with AI."""
    
    def __init__(self, api_key=None):
        """Initialize the DevOps Intelligence system.
        
        Args:
            api_key (str, optional): Not used, kept for backward compatibility.
        """
        self.system_prompt = self._create_system_prompt()
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
        logger.info("Using local AI model for DevOps operations")
    
    def _create_system_prompt(self):
        """Create the system prompt for the DevOps AI assistant."""
        return """
        You are an expert DevOps AI assistant that manages both GitHub and GitLab operations.
        Your primary roles are:
        
        1. Understanding user intent and translating it into specific DevOps operations
        2. Managing authentication with both GitHub and GitLab
        3. Orchestrating cross-platform workflows
        4. Providing clear explanations of complex DevOps processes
        5. Suggesting improvements and optimizations to the user's DevOps workflows
        
        When users mention GitHub operations, focus on repositories, workflows, actions, and deployments.
        When users mention GitLab operations, focus on projects, pipelines, CI/CD, and deployments.
        
        Always prioritize security and follow best practices.
        For each operation requested, output:
        1. A clear explanation of what will be done
        2. The platforms involved (GitHub, GitLab, or both)
        3. The specific API endpoints and operations that will be used
        4. Any potential risks or considerations
        
        Keep your responses focused on DevOps tasks and avoid discussions unrelated to software development,
        deployment, or integration between GitHub and GitLab.
        """
    
    def get_ai_response(self, user_message, session_id, conversation_history=None):
        """Get a response from the AI based on the user message and conversation history.
        
        Args:
            user_message (str): The user's message
            session_id (str): Unique session identifier
            conversation_history (list, optional): Previous conversation
            
        Returns:
            dict: AI response with content and any operation details
        """
        # Get or initialize conversation history
        if not conversation_history:
            conversation_history = self.get_conversation_history(session_id)
        
        # Use the local AI model to process the message
        try:
            # First try our enhanced model
            response_content = process_message(user_message)
            
            # Format the response as if it came from a sophisticated AI
            if "github" in user_message.lower() or "gitlab" in user_message.lower():
                # Add DevOps context to the response
                response_content = self._enhance_response_with_devops_context(user_message, response_content)
        except Exception as e:
            logger.error(f"Error using local AI model: {str(e)}")
            # Provide a fallback response
            response_content = "I understand you're asking about DevOps operations. I can help with GitHub and GitLab integrations, CI/CD pipelines, and cross-platform automation. Could you please be more specific about what you need help with?"
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": response_content})
        
        # Trim history if it's too long
        while len(conversation_history) > MAX_CONVERSATION_HISTORY:
            conversation_history.pop(0)
        
        # Save updated history
        self.save_conversation_history(session_id, conversation_history)
        
        # Process the response for operations
        operations = self.extract_operations(response_content)
        
        return {
            "content": response_content,
            "operations": operations
        }
    
    def _enhance_response_with_devops_context(self, user_message, basic_response):
        """Add DevOps context to a basic response to make it more useful."""
        # Check if message is related to GitHub
        if "github" in user_message.lower():
            if "repository" in user_message.lower() or "repo" in user_message.lower():
                return f"{basic_response}\n\nFor GitHub repositories, I can help you with creation, management, and setting up workflows. GitHub uses REST API endpoints like `/user/repos` for repository operations."
            if "workflow" in user_message.lower() or "action" in user_message.lower():
                return f"{basic_response}\n\nGitHub Actions workflows are defined in YAML files in the `.github/workflows` directory. I can help you create and manage these workflows through the GitHub API."
        
        # Check if message is related to GitLab
        if "gitlab" in user_message.lower():
            if "project" in user_message.lower():
                return f"{basic_response}\n\nFor GitLab projects, I can help with creation and configuration. GitLab uses REST API endpoints like `/projects` for project operations."
            if "pipeline" in user_message.lower() or "ci" in user_message.lower() or "cd" in user_message.lower():
                return f"{basic_response}\n\nGitLab CI/CD pipelines are defined in `.gitlab-ci.yml` files. I can help you create and manage these pipelines through the GitLab API."
        
        # Check if message is related to both platforms
        if "github" in user_message.lower() and "gitlab" in user_message.lower():
            if "sync" in user_message.lower() or "integration" in user_message.lower() or "connect" in user_message.lower():
                return f"{basic_response}\n\nFor synchronizing GitHub and GitLab, we can use API integrations and webhooks to create cross-platform workflows. This helps maintain consistency across platforms and allows for unified DevOps orchestration."
        
        return basic_response
    
    def extract_operations(self, content):
        """Extract any operations mentioned in the AI response.
        
        This function looks for patterns in the AI response that indicate
        specific operations that should be performed.
        
        Args:
            content (str): The AI response content
            
        Returns:
            list: List of operation objects, or empty list if none found
        """
        operations = []
        
        # Look for GitHub operations
        if "github" in content.lower() and any(op in content.lower() for op in ["create", "update", "delete", "repository", "workflow", "action"]):
            if "create repository" in content.lower():
                operations.append({
                    "platform": "github",
                    "operation": "create_repository",
                    "description": "Create a new GitHub repository"
                })
            elif "create workflow" in content.lower():
                operations.append({
                    "platform": "github",
                    "operation": "create_workflow",
                    "description": "Create a new GitHub workflow"
                })
        
        # Look for GitLab operations
        if "gitlab" in content.lower() and any(op in content.lower() for op in ["create", "update", "delete", "project", "pipeline", "ci/cd"]):
            if "create project" in content.lower():
                operations.append({
                    "platform": "gitlab",
                    "operation": "create_project",
                    "description": "Create a new GitLab project"
                })
            elif "trigger pipeline" in content.lower():
                operations.append({
                    "platform": "gitlab",
                    "operation": "trigger_pipeline",
                    "description": "Trigger a GitLab CI/CD pipeline"
                })
        
        # Look for cross-platform operations
        if "github" in content.lower() and "gitlab" in content.lower() and "sync" in content.lower():
            operations.append({
                "platform": "cross-platform",
                "operation": "sync_github_to_gitlab",
                "description": "Synchronize GitHub repository to GitLab"
            })
        
        return operations
    
    def get_conversation_history(self, session_id):
        """Get conversation history for a session.
        
        Args:
            session_id (str): Unique session identifier
            
        Returns:
            list: Conversation history for this session
        """
        if session_id not in conversation_histories:
            conversation_histories[session_id] = []
        
        return conversation_histories[session_id]
    
    def save_conversation_history(self, session_id, history):
        """Save updated conversation history for a session.
        
        Args:
            session_id (str): Unique session identifier
            history (list): Updated conversation history
        """
        conversation_histories[session_id] = history
    
    def clear_conversation_history(self, session_id):
        """Clear conversation history for a session.
        
        Args:
            session_id (str): Unique session identifier
        """
        if session_id in conversation_histories:
            conversation_histories[session_id] = []


class DevOpsOrchestrator:
    """Orchestrates DevOps operations across platforms based on AI directives."""
    
    def __init__(self, intelligence):
        """Initialize the DevOps Orchestrator.
        
        Args:
            intelligence (DevOpsIntelligence): The AI intelligence component
        """
        self.intelligence = intelligence
        self.operation_handlers = {
            # GitHub operations
            "github:create_repository": self.github_create_repository,
            "github:create_workflow": self.github_create_workflow,
            
            # GitLab operations
            "gitlab:create_project": self.gitlab_create_project,
            "gitlab:trigger_pipeline": self.gitlab_trigger_pipeline,
            
            # Cross-platform operations
            "cross-platform:sync_github_to_gitlab": self.sync_github_to_gitlab
        }
    
    def execute_operation(self, operation, parameters=None):
        """Execute a specific DevOps operation.
        
        Args:
            operation (str): Operation identifier (platform:operation)
            parameters (dict): Parameters for the operation
            
        Returns:
            dict: Result of the operation
        """
        if not parameters:
            parameters = {}
        
        if operation not in self.operation_handlers:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}"
            }
        
        try:
            handler = self.operation_handlers[operation]
            result = handler(**parameters)
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            logger.error(f"Error executing operation {operation}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def github_create_repository(self, name, description="", private=False):
        """Create a new GitHub repository.
        
        Args:
            name (str): Repository name
            description (str): Repository description
            private (bool): Whether the repository should be private
            
        Returns:
            dict: Created repository information
        """
        logger.info(f"Creating GitHub repository: {name}")
        result = make_secure_github_request(
            "user/repos",
            method="POST",
            data={
                "name": name,
                "description": description,
                "private": private
            }
        )
        logger.info(f"GitHub repository created: {result.get('html_url', '')}")
        return result
    
    def github_create_workflow(self, owner, repo, workflow_name, workflow_content):
        """Create a new GitHub workflow.
        
        Args:
            owner (str): Repository owner
            repo (str): Repository name
            workflow_name (str): Name for the workflow file
            workflow_content (str): YAML content for the workflow
            
        Returns:
            dict: Result of creating the workflow file
        """
        logger.info(f"Creating GitHub workflow: {workflow_name} in {owner}/{repo}")
        
        # Ensure the workflows directory exists
        try:
            workflows_dir = make_secure_github_request(
                f"repos/{owner}/{repo}/contents/.github/workflows",
                method="GET"
            )
        except Exception:
            # Create .github/workflows directory structure
            try:
                # First check if .github exists
                github_dir = make_secure_github_request(
                    f"repos/{owner}/{repo}/contents/.github",
                    method="GET"
                )
            except Exception:
                # Create .github directory
                make_secure_github_request(
                    f"repos/{owner}/{repo}/contents/.github",
                    method="PUT",
                    data={
                        "message": "Create .github directory",
                        "content": "",
                        "branch": "main"
                    }
                )
            
            # Create workflows directory
            make_secure_github_request(
                f"repos/{owner}/{repo}/contents/.github/workflows",
                method="PUT",
                data={
                    "message": "Create workflows directory",
                    "content": "",
                    "branch": "main"
                }
            )
        
        # Create workflow file
        import base64
        encoded_content = base64.b64encode(workflow_content.encode()).decode()
        
        result = make_secure_github_request(
            f"repos/{owner}/{repo}/contents/.github/workflows/{workflow_name}.yml",
            method="PUT",
            data={
                "message": f"Create workflow: {workflow_name}",
                "content": encoded_content,
                "branch": "main"
            }
        )
        
        logger.info(f"GitHub workflow created: {workflow_name}")
        return result
    
    def gitlab_create_project(self, name, description=""):
        """Create a new GitLab project.
        
        Args:
            name (str): Project name
            description (str): Project description
            
        Returns:
            dict: Created project information
        """
        logger.info(f"Creating GitLab project: {name}")
        result = make_secure_gitlab_request(
            "projects",
            method="POST",
            data={
                "name": name,
                "description": description,
                "visibility": "private"
            }
        )
        logger.info(f"GitLab project created: {result.get('web_url', '')}")
        return result
    
    def gitlab_trigger_pipeline(self, project_id, ref="main"):
        """Trigger a pipeline in a GitLab project.
        
        Args:
            project_id (int): GitLab project ID
            ref (str): Git reference (branch/tag)
            
        Returns:
            dict: Pipeline information
        """
        logger.info(f"Triggering GitLab pipeline in project {project_id}, ref {ref}")
        result = make_secure_gitlab_request(
            f"projects/{project_id}/pipeline",
            method="POST",
            data={"ref": ref}
        )
        logger.info(f"GitLab pipeline triggered: {result.get('id', '')}")
        return result
    
    def sync_github_to_gitlab(self, github_repo, gitlab_project):
        """Synchronize a GitHub repository to GitLab.
        
        Args:
            github_repo (str): GitHub repository in the format "owner/repo"
            gitlab_project (int): GitLab project ID
            
        Returns:
            dict: Result of the synchronization
        """
        logger.info(f"Syncing GitHub repo {github_repo} to GitLab project {gitlab_project}")
        
        # Get GitHub repository information
        repo_info = make_secure_github_request(
            f"repos/{github_repo}"
        )
        
        # Update GitLab project description
        make_secure_gitlab_request(
            f"projects/{gitlab_project}",
            method="PUT",
            data={
                "description": f"Synced from GitHub: {github_repo} | {repo_info.get('description', 'No description')}"
            }
        )
        
        # Get repository contents
        contents = make_secure_github_request(
            f"repos/{github_repo}/contents"
        )
        
        # Sync files (simplified version - in reality, this would be more complex)
        for item in contents:
            if item['type'] == 'file':
                # Download file content from GitHub
                # Directly access the download URL without API prefix
                import requests
                file_response = requests.get(item['download_url'])
                file_content = file_response.text
                
                # Upload to GitLab
                import base64
                encoded_content = base64.b64encode(file_content.encode()).decode()
                
                make_secure_gitlab_request(
                    f"projects/{gitlab_project}/repository/files/{item['path']}",
                    method="POST",
                    data={
                        "branch": "main",
                        "content": encoded_content,
                        "commit_message": f"Sync {item['path']} from GitHub"
                    }
                )
        
        return {
            "status": "success",
            "message": f"Synchronized {github_repo} to GitLab project {gitlab_project}",
            "files_synced": len([item for item in contents if item['type'] == 'file'])
        }


# Create instances for global use
intelligence = DevOpsIntelligence()
orchestrator = DevOpsOrchestrator(intelligence)


def process_chat_message(user_message, session_id=None):
    """Process a user message through the DevOps AI controller.
    
    This function takes a user message, routes it through the local AI intelligence
    system, and determines what operations (if any) to perform.
    
    Args:
        user_message (str): The user's message
        session_id (str, optional): Session identifier. If None, will generate one.
        
    Returns:
        dict: Response with AI content and any operations performed
    """
    # Generate a session ID if not provided
    if not session_id:
        session_id = str(datetime.now().timestamp())
    
    # Get AI response
    try:
        ai_response = intelligence.get_ai_response(user_message, session_id)
    except Exception as e:
        # Fallback to basic AI model if any issues
        logger.error(f"Error from main AI model: {str(e)}")
        # Simple fallback response
        response_text = process_message(user_message)
        ai_response = {
            "content": response_text,
            "operations": []
        }
    
    # Check if there are operations to perform
    operations_results = []
    if "operations" in ai_response and ai_response["operations"]:
        for operation in ai_response["operations"]:
            # Access dictionary keys safely
            if isinstance(operation, dict):
                platform = operation.get("platform", "unknown")
                operation_type = operation.get("operation", "unknown")
            else:
                # Handle case where operation might be a string or other type
                platform = "unknown"
                operation_type = str(operation)
            op_id = f"{platform}:{operation_type}"
            
            # Extract parameters from operation (this would be more sophisticated in a real system)
            parameters = {}  # In reality, we would extract parameters from the user message
            
            # Execute the operation
            result = orchestrator.execute_operation(op_id, parameters)
            operations_results.append({
                "operation": operation,
                "result": result
            })
    
    # Compile the response
    response = {
        "content": ai_response["content"],
        "session_id": session_id
    }
    
    if operations_results:
        response["operations"] = operations_results
    
    return response


def validate_ai_model():
    """Validate the AI model availability.
    
    Returns:
        bool: True if the local AI model is available, False otherwise
    """
    try:
        # Check if our local AI model is functioning
        test_response = process_message("Hello, are you working?")
        return len(test_response) > 0
    except Exception as e:
        logger.error(f"Error validating local AI model: {str(e)}")
        return False


# Flask routes for the DevOps AI controller

def register_devops_routes(app):
    """Register DevOps AI controller routes with Flask app.
    
    Args:
        app: Flask application
    """
    @app.route('/api/devops/chat', methods=['POST'])
    def devops_chat_endpoint():
        """API endpoint for DevOps AI chat messages."""
        data = request.json
        user_message = data.get('message', '')
        session_id = data.get('session_id') or session.get('session_id')
        
        response = process_chat_message(user_message, session_id)
        
        # Save session ID
        if 'session_id' in response:
            session['session_id'] = response['session_id']
        
        return jsonify(response)
    
    @app.route('/api/devops/validate', methods=['GET'])
    def validate_ai_token_route():
        """Validate the AI model availability."""
        is_valid = validate_ai_model()
        return jsonify({"valid": is_valid})
    
    @app.route('/api/devops/history', methods=['GET'])
    def devops_chat_history():
        """Get DevOps AI chat history for the current session."""
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({"history": []})
        
        history = intelligence.get_conversation_history(session_id)
        
        # Format history for the frontend
        formatted_history = []
        for message in history:
            formatted_history.append({
                "content": message["content"],
                "is_user": message["role"] == "user"
            })
        
        return jsonify({"history": formatted_history})
    
    @app.route('/api/devops/clear', methods=['POST'])
    def clear_devops_chat():
        """Clear DevOps AI chat history for the current session."""
        session_id = session.get('session_id')
        if session_id:
            intelligence.clear_conversation_history(session_id)
        
        return jsonify({"success": True})


# Initialization
def initialize():
    """Initialize the DevOps AI controller.
    
    This function should be called during application startup.
    """
    valid = validate_ai_model()
    if valid:
        logger.info("Local AI model initialized successfully.")
    else:
        logger.warning("Local AI model validation failed. Check the AI model implementation.")
    
    logger.info("DevOps AI controller initialized.")