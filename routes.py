import json
import logging
from flask import render_template, request, jsonify, session
import uuid

from app import app, db
from models import ChatMessage, Project, Action
from ai_model import process_message
from gitlab_api import get_gitlab_projects, create_gitlab_pipeline
from github_api import get_github_repositories, create_github_repository, get_github_workflows

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Render the main page with the chat interface."""
    # Generate a unique session ID if not already present
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Process incoming chat messages and generate responses."""
    try:
        data = request.json
        user_message = data.get('message', '')
        session_id = session.get('session_id', str(uuid.uuid4()))
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Save user message to database
        user_chat = ChatMessage(
            content=user_message,
            is_user=True,
            session_id=session_id
        )
        db.session.add(user_chat)
        db.session.commit()
        
        # Process message with AI model
        ai_response = process_message(user_message)
        
        # Save AI response to database
        ai_chat = ChatMessage(
            content=ai_response,
            is_user=False,
            session_id=session_id
        )
        db.session.add(ai_chat)
        db.session.commit()
        
        return jsonify({
            'response': ai_response,
            'messageId': ai_chat.id
        })
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/history')
def chat_history():
    """Retrieve chat history for the current session."""
    try:
        session_id = session.get('session_id', '')
        if not session_id:
            return jsonify({'messages': []})
        
        messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp).all()
        
        history = [
            {
                'id': msg.id,
                'content': msg.content,
                'isUser': msg.is_user,
                'timestamp': msg.timestamp.isoformat() if msg.timestamp else None
            }
            for msg in messages
        ]
        
        return jsonify({'messages': history})
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        return jsonify({'messages': [], 'error': str(e)})

@app.route('/api/gitlab/projects')
def gitlab_projects():
    """Retrieve projects from GitLab using the stored API token."""
    try:
        projects = get_gitlab_projects()
        return jsonify({'projects': projects})
    except Exception as e:
        logger.error(f"Error fetching GitLab projects: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gitlab/pipeline', methods=['POST'])
def create_pipeline():
    """Create a pipeline in GitLab for a specific project."""
    try:
        data = request.json
        project_id = data.get('project_id')
        branch = data.get('branch', 'main')
        
        if not project_id:
            return jsonify({'error': 'Project ID is required'}), 400
        
        result = create_gitlab_pipeline(project_id, branch)
        
        # Record the action
        action = Action(
            action_type='pipeline_creation',
            description=f'Created pipeline for project {project_id} on branch {branch}',
            status='completed',
            project_id=project_id,
            user_id=1  # Default user ID for now
        )
        db.session.add(action)
        db.session.commit()
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error creating GitLab pipeline: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/github/repositories')
def github_repositories():
    """Retrieve repositories from GitHub using the stored API token."""
    try:
        repositories = get_github_repositories()
        return jsonify({'repositories': repositories})
    except Exception as e:
        logger.error(f"Error fetching GitHub repositories: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/github/repository', methods=['POST'])
def github_create_repository():
    """Create a new GitHub repository."""
    try:
        data = request.json
        name = data.get('name')
        description = data.get('description', '')
        
        if not name:
            return jsonify({'error': 'Repository name is required'}), 400
        
        result = create_github_repository(name, description)
        
        # Record the action
        action = Action(
            action_type='repository_creation',
            description=f'Created GitHub repository "{name}"',
            status='completed',
            project_id=1,  # Default project ID for now
            user_id=1  # Default user ID for now
        )
        db.session.add(action)
        db.session.commit()
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error creating GitHub repository: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/github/workflows')
def github_workflows():
    """Retrieve workflows for a GitHub repository."""
    try:
        owner = request.args.get('owner')
        repo = request.args.get('repo')
        
        if not owner or not repo:
            return jsonify({'error': 'Owner and repository name are required'}), 400
        
        workflows = get_github_workflows(owner, repo)
        return jsonify({'workflows': workflows})
    
    except Exception as e:
        logger.error(f"Error fetching GitHub workflows: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/actions/recent')
def recent_actions():
    """Get recent DevOps actions from the database."""
    actions = Action.query.order_by(Action.created_at.desc()).limit(10).all()
    
    result = [
        {
            'id': action.id,
            'type': action.action_type,
            'description': action.description,
            'status': action.status,
            'created_at': action.created_at.isoformat(),
            'project_id': action.project_id
        }
        for action in actions
    ]
    
    return jsonify({'actions': result})

@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500
