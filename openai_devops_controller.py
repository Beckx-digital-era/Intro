"""
OpenAI DevOps Controller

This module provides a centralized AI-powered control system for the DevOps platform.
It uses OpenAI's capabilities to understand user requests, manage authentication,
and orchestrate operations across GitHub and GitLab platforms.

The controller acts as the top-level intelligence layer that coordinates all platform activities.
"""

import os
import json
import logging
from datetime import datetime
from flask import session, request, jsonify
import random
from ai_model import find_most_similar_query, RESPONSES

# Import for our fallback AI capabilities
from ai_model import process_message as ai_model_process_message

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not found in environment variables")

# Maximum conversation history to maintain
MAX_CONVERSATION_HISTORY = 20

# Conversation memory storage
conversation_histories = {}


class DevOpsIntelligence:
    """Core intelligence layer for managing DevOps operations with AI."""
    
    def __init__(self, api_key=None):
        """Initialize the DevOps Intelligence system.
        
        Args:
            api_key (str, optional): OpenAI API key. If not provided, 
                                     will use environment variable.
        """
        self.api_key = api_key or OPENAI_API_KEY
        self.model = OPENAI_MODEL
        self.system_prompt = self._create_system_prompt()
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
        if not self.api_key:
            logger.error("No OpenAI API key provided. AI features will not function.")
        
        # Create OpenAI client
        self.client = OpenAI(api_key=self.api_key)
    
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
        if not self.api_key:
            return {
                "content": "AI features are not available. Please set the OPENAI_API_KEY environment variable.",
                "error": "No API key provided"
            }
        
        # Get or initialize conversation history
        if not conversation_history:
            conversation_history = self.get_conversation_history(session_id)
        
        # Prepare messages for the API call
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation history
        for msg in conversation_history:
            messages.append(msg)
        
        # Add the current user message
        messages.append({"role": "user", "content": user_message})
        
        # Make the API call with retries
        response_content = None
        error = None
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000,
                )
                
                response_content = response.choices[0].message.content
                break
            
            except Exception as e:
                logger.error(f"Error calling OpenAI API (attempt {attempt+1}): {str(e)}")
                error = str(e)
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
        
        if not response_content:
            # Provide a more detailed fallback response since OpenAI API is unavailable
            fallback_content = (
                f"I'm having trouble connecting to the OpenAI services. Error: {error}\n\n"
                "However, I can still help with basic DevOps operations. Here are some things I can do:\n"
                "1. Create or manage GitHub repositories\n"
                "2. Set up GitLab projects and pipelines\n"
                "3. Synchronize repositories between GitHub and GitLab\n"
                "4. Manage CI/CD workflows\n\n"
                "Just let me know what you need help with, and I'll do my best to assist using the available services."
            )
            return {
                "content": fallback_content,
                "error": error
            }
        
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
intelligence = DevOpsIntelligence(api_key=OPENAI_API_KEY)
orchestrator = DevOpsOrchestrator(intelligence)


def process_chat_message(user_message, session_id=None):
    """Process a user message through the OpenAI DevOps controller.
    
    This function takes a user message, routes it through the AI intelligence
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
    ai_response = intelligence.get_ai_response(user_message, session_id)
    
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


def validate_openai_token():
    """Validate the OpenAI API token.
    
    Returns:
        bool: True if the token is valid, False otherwise
    """
    if not OPENAI_API_KEY:
        return False
    
    try:
        # Make a simple API call to check if the token is valid
        client = OpenAI(api_key=OPENAI_API_KEY)
        models = client.models.list()
        return len(models.data) > 0
    except Exception as e:
        logger.error(f"Error validating OpenAI token: {str(e)}")
        return False


# Flask routes for the OpenAI DevOps controller

def register_openai_routes(app):
    """Register OpenAI DevOps controller routes with Flask app.
    
    Args:
        app: Flask application
    """
    @app.route('/api/openai/chat', methods=['POST'])
    def openai_chat_endpoint():
        """API endpoint for OpenAI chat messages."""
        data = request.json
        user_message = data.get('message', '')
        session_id = data.get('session_id') or session.get('session_id')
        
        response = process_chat_message(user_message, session_id)
        
        # Save session ID
        if 'session_id' in response:
            session['session_id'] = response['session_id']
        
        return jsonify(response)
    
    @app.route('/api/openai/validate', methods=['GET'])
    def validate_openai_token_route():
        """Validate the OpenAI API token."""
        is_valid = validate_openai_token()
        return jsonify({"valid": is_valid})
    
    @app.route('/api/openai/history', methods=['GET'])
    def openai_chat_history():
        """Get OpenAI chat history for the current session."""
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
    
    @app.route('/api/openai/clear', methods=['POST'])
    def clear_openai_chat():
        """Clear OpenAI chat history for the current session."""
        session_id = session.get('session_id')
        if session_id:
            intelligence.clear_conversation_history(session_id)
        
        return jsonify({"success": True})


# Initialization
def initialize():
    """Initialize the OpenAI DevOps controller.
    
    This function should be called during application startup.
    """
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY environment variable not set. AI features will be limited.")
    else:
        valid = validate_openai_token()
        if valid:
            logger.info("OpenAI API token is valid.")
        else:
            logger.warning("OpenAI API token validation failed.")
    
    logger.info("OpenAI DevOps controller initialized.")