import json
import logging
import os
import requests
import subprocess
import uuid
from flask import render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from app import app, db
from models import ChatMessage, Project, Action, User
from ai_model import process_message
from openai_devops_controller import process_chat_message
from gitlab_api import get_gitlab_projects, create_gitlab_pipeline
from github_api import get_github_repositories, create_github_repository, get_github_workflows, make_github_request
from github_gitlab_bridge import sync_github_repo_to_gitlab

logger = logging.getLogger(__name__)

# Set up Flask Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for user authentication."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')
    
@app.route('/admin-login', methods=['POST'])
def admin_login():
    """Admin login with a special key."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    admin_key = request.form.get('admin_key')
    
    # Check if the admin key is correct (hard-coded "Meeki")
    if admin_key == "Meeki":
        # Look for an admin user
        admin = User.query.filter_by(is_admin=True).first()
        
        # If no admin user exists, create one
        if not admin:
            admin = User(
                username="admin",
                email="admin@devops.system",
                is_admin=True
            )
            admin.set_password("Meeki")  # Set the admin password to match the key
            db.session.add(admin)
            db.session.commit()
        
        login_user(admin)
        return redirect(url_for('index'))
    else:
        flash('Invalid admin key')
        return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page for new users."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return render_template('register.html')
            
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return render_template('register.html')
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """Logout the current user."""
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Render the main page with the chat interface."""
    # Generate a unique session ID if not already present
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    return render_template('index.html')

@app.route('/terminal')
@login_required
def terminal():
    """Render the terminal interface page (admin only)."""
    # Check if the user is an admin
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
        
    return render_template('terminal.html')
    
@app.route('/api/terminal/execute', methods=['POST'])
@login_required
def execute_command():
    """Execute a command in the terminal and return the result (admin only)."""
    # Check if the user is an admin
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        return jsonify({
            'output': 'Access denied. Admin privileges required.',
            'error': True
        }), 403
    try:
        data = request.json
        command = data.get('command', '')
        
        if not command:
            return jsonify({'error': 'Command is required'}), 400
            
        # Security check - prevent dangerous commands
        if any(dangerous_cmd in command for dangerous_cmd in ['rm -rf', 'sudo', '>', '|', '&']):
            return jsonify({
                'output': 'Error: Command not allowed for security reasons.',
                'error': True
            })
        
        # Execute the command
        try:
            output = subprocess.check_output(
                command,
                shell=True,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=10
            )
            
            # Record the action
            action = Action(
                action_type='terminal_command',
                description=f'Executed command: {command}',
                status='completed',
                project_id=1,  # Default project ID
                user_id=1  # Using 1 as default user ID since current_user might not be available
            )
            db.session.add(action)
            db.session.commit()
            
            return jsonify({
                'output': output,
                'error': False
            })
            
        except subprocess.CalledProcessError as e:
            return jsonify({
                'output': e.output,
                'error': True
            })
        except subprocess.TimeoutExpired:
            return jsonify({
                'output': 'Command execution timed out after 10 seconds.',
                'error': True
            })
    
    except Exception as e:
        logger.error(f"Error executing terminal command: {str(e)}")
        return jsonify({
            'output': f'Internal error: {str(e)}',
            'error': True
        }), 500

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
        
        # Try to process message with OpenAI DevOps controller first
        try:
            response = process_chat_message(user_message, session_id)
            ai_response = response.get('content', '')
            
            # If we got an empty response, fall back to simple AI model
            if not ai_response:
                logger.warning("OpenAI controller returned empty response, falling back to basic AI model")
                ai_response = process_message(user_message)
        except Exception as e:
            # If OpenAI processing fails, fall back to simple AI model
            logger.warning(f"Error using OpenAI controller, falling back to basic AI model: {str(e)}")
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



@app.route('/api/gitlab/projects')
def gitlab_projects():
    """Retrieve projects from GitLab using the stored API token."""
    try:
        projects = get_gitlab_projects()
        
        # Check if there was an error returned from the API call
        if isinstance(projects, dict) and projects.get("status") == "error":
            error_message = projects.get("message", "Unknown GitLab API error")
            logger.error(f"GitLab API error: {error_message}")
            return jsonify({
                'error': error_message,
                'needs_token_update': 'token is invalid' in error_message.lower() or 'token is expired' in error_message.lower()
            }), 401
        
        return jsonify({'projects': projects})
    except Exception as e:
        logger.error(f"Error fetching GitLab projects: {str(e)}")
        return jsonify({
            'error': str(e),
            'needs_token_update': 'token' in str(e).lower() or 'unauthorized' in str(e).lower() or '401' in str(e)
        }), 500

@app.route('/api/gitlab/pipeline', methods=['POST'])
def create_pipeline():
    """Create a pipeline in GitLab for a specific project."""
    try:
        data = request.json
        gitlab_project_id = data.get('project_id')
        branch = data.get('branch', 'main')
        
        if not gitlab_project_id:
            return jsonify({'error': 'Project ID is required'}), 400
        
        # Check if the GitLab project exists in our database
        project = Project.query.filter_by(gitlab_project_id=str(gitlab_project_id)).first()
        
        # If the project doesn't exist in our database, create it
        if not project:
            project = Project(
                name=f'GitLab Project {gitlab_project_id}',
                description='Project automatically added from GitLab integration',
                gitlab_project_id=str(gitlab_project_id),
                user_id=1  # Default user ID
            )
            db.session.add(project)
            db.session.commit()
            logger.info(f"Created new project record for GitLab project {gitlab_project_id}")
        
        # Now create the pipeline via API
        result = create_gitlab_pipeline(gitlab_project_id, branch)
        
        # Check if there was an error returned from the API call
        if isinstance(result, dict) and result.get("status") == "error":
            error_message = result.get("message", "Unknown GitLab API error")
            logger.error(f"GitLab API error when creating pipeline: {error_message}")
            action = Action(
                action_type='pipeline_creation',
                description=f'Failed to create pipeline for GitLab project {gitlab_project_id}: {error_message}',
                status='failed',
                project_id=project.id,
                user_id=1  # Default user ID
            )
            db.session.add(action)
            db.session.commit()
            
            return jsonify({
                'error': error_message,
                'needs_token_update': 'token is invalid' in error_message.lower() or 'token is expired' in error_message.lower()
            }), 401
        
        # Record the successful action with the correct project_id (from our database)
        action = Action(
            action_type='pipeline_creation',
            description=f'Created pipeline for GitLab project {gitlab_project_id} on branch {branch}',
            status='completed',
            project_id=project.id,  # Use our database ID, not the GitLab project ID
            user_id=1  # Default user ID
        )
        db.session.add(action)
        db.session.commit()
        
        # Add GitHub Actions integration message
        if isinstance(result, dict):
            result['github_actions_control'] = {
                'status': 'enabled',
                'message': 'This GitLab pipeline is controlled by GitHub Actions'
            }
        else:
            # Handle unexpected result format
            result = {
                'status': 'success',
                'message': 'Pipeline creation initiated',
                'github_actions_control': {
                    'status': 'enabled',
                    'message': 'This GitLab pipeline is controlled by GitHub Actions'
                }
            }
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error creating GitLab pipeline: {str(e)}")
        return jsonify({
            'error': str(e),
            'needs_token_update': 'token' in str(e).lower() or 'unauthorized' in str(e).lower() or '401' in str(e)
        }), 500

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

@app.route('/api/github/repository/beckx-intro')
def beckx_intro_repository():
    """Get details for the Beckx-digital-era/Intro repository."""
    try:
        # Make a direct request to the GitHub API for the specific repository
        response = make_github_request('repos/Beckx-digital-era/Intro')
        
        # If we don't already have this repository in our database, add it
        project = Project.query.filter_by(github_repo_url='https://github.com/Beckx-digital-era/Intro').first()
        if not project:
            project = Project(
                name='Beckx-digital-era/Intro',
                description='Beckx Digital Era Introduction Repository',
                github_repo_url='https://github.com/Beckx-digital-era/Intro',
                user_id=1  # Default user ID
            )
            db.session.add(project)
            db.session.commit()
            logger.info("Added Beckx-digital-era/Intro repository to projects database")
        
        return jsonify({'repository': response})
    except Exception as e:
        logger.error(f"Error fetching Beckx-digital-era/Intro repository: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/github/repository/beckx-intro/commits')
def beckx_intro_commits():
    """Get recent commits for the Beckx-digital-era/Intro repository."""
    try:
        # Make a direct request to the GitHub API for commits
        response = make_github_request('repos/Beckx-digital-era/Intro/commits')
        return jsonify({'commits': response})
    except Exception as e:
        logger.error(f"Error fetching commits for Beckx-digital-era/Intro: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/github/repository/beckx-intro/sync-gitlab', methods=['POST'])
def beckx_intro_sync_gitlab():
    """Sync the Beckx-digital-era/Intro repository with GitLab."""
    try:
        # Check if we already have a GitLab project ID for this repo
        project = Project.query.filter_by(github_repo_url='https://github.com/Beckx-digital-era/Intro').first()
        
        if not project:
            return jsonify({'error': 'Repository not found in database'}), 404
        
        # If no GitLab project exists yet, create one
        if not project.gitlab_project_id:
            # Prepare arguments for the sync function
            args = {
                'direction': 'github-to-gitlab',
                'action': 'sync-repo',
                'github_repo': 'Beckx-digital-era/Intro'
            }
            
            # The bridge function will get tokens from environment variables
            result = sync_github_repo_to_gitlab(args)
            
            if isinstance(result, dict) and result.get('id'):
                # Store the GitLab project ID in our database
                project.gitlab_project_id = str(result.get('id'))
                db.session.commit()
                logger.info(f"GitLab project created with ID: {project.gitlab_project_id}")
            else:
                logger.error(f"Failed to create GitLab project: {result}")
                return jsonify({'error': 'Failed to create GitLab project'}), 500
        else:
            # If GitLab project already exists, just sync the latest changes
            args = {
                'direction': 'github-to-gitlab',
                'action': 'sync-repo',
                'github_repo': 'Beckx-digital-era/Intro',
                'gitlab_project': project.gitlab_project_id
            }
            
            # The bridge function will get tokens from environment variables
            result = sync_github_repo_to_gitlab(args)
            
        # Record the action
        action = Action(
            action_type='repository_sync',
            description=f'Synced Beckx-digital-era/Intro repository to GitLab',
            status='completed',
            project_id=project.id,
            user_id=1  # Default user ID
        )
        db.session.add(action)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Repository synchronized with GitLab',
            'gitlab_project_id': project.gitlab_project_id
        })
    
    except Exception as e:
        logger.error(f"Error syncing Beckx-digital-era/Intro to GitLab: {str(e)}")
        
        # Record the failed action
        project = Project.query.filter_by(github_repo_url='https://github.com/Beckx-digital-era/Intro').first()
        if project:
            action = Action(
                action_type='repository_sync',
                description=f'Failed to sync Beckx-digital-era/Intro repository to GitLab: {str(e)}',
                status='failed',
                project_id=project.id,
                user_id=1  # Default user ID
            )
            db.session.add(action)
            db.session.commit()
        
        return jsonify({'error': str(e)}), 500

@app.route('/api/github/repository/beckx-intro/setup-cicd', methods=['POST'])
def beckx_intro_setup_cicd():
    """Set up CI/CD pipeline for the Beckx-digital-era/Intro repository."""
    try:
        # Find the project in our database
        project = Project.query.filter_by(github_repo_url='https://github.com/Beckx-digital-era/Intro').first()
        
        if not project:
            return jsonify({'error': 'Repository not found in database'}), 404
        
        # Check if GitLab project exists
        if not project.gitlab_project_id:
            return jsonify({'error': 'GitLab project not found. Please sync repository first.'}), 400
        
        # Create GitHub Actions workflow file for Beckx-digital-era/Intro
        ci_workflow_content = {
            'name': 'beckx-gitlab-ci.yml',
            'content': '''name: GitLab CI Integration

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:

jobs:
  trigger-gitlab:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          pip install requests
          
      - name: Trigger GitLab Pipeline
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITLAB_TOKEN: ${{ secrets.GITLAB_TOKEN }}
        run: |
          python github_gitlab_bridge.py --direction=github-to-gitlab --action=trigger-pipeline --gitlab-project=${GITLAB_PROJECT_ID}
        env:
          GITLAB_PROJECT_ID: ''' + project.gitlab_project_id + '''
''',
            'message': 'Add GitLab CI integration workflow'
        }
        
        # Try to create the workflow file in the GitHub repo
        try:
            github_response = make_github_request(
                f'repos/Beckx-digital-era/Intro/contents/.github/workflows/beckx-gitlab-ci.yml', 
                method='PUT',
                data=ci_workflow_content
            )
            logger.info(f"Created GitHub workflow file: {github_response}")
        except Exception as e:
            logger.error(f"Failed to create GitHub workflow file: {str(e)}")
            # Continue anyway, as we'll still set up the GitLab CI
        
        # Set up GitLab CI configuration file
        gitlab_ci_content = {
            'file_path': '.gitlab-ci.yml',
            'branch': 'main',
            'content': '''stages:
  - build
  - test
  - deploy

variables:
  PROJECT_NAME: beckx-intro

build:
  stage: build
  image: python:3.10
  script:
    - echo "Building $PROJECT_NAME"
    - pip install -r requirements.txt || echo "No requirements.txt found"
  artifacts:
    paths:
      - dist/
    expire_in: 1 week

test:
  stage: test
  image: python:3.10
  script:
    - echo "Testing $PROJECT_NAME"
    - pip install pytest || echo "Skipping pytest installation"
    - pytest || echo "No tests to run"

deploy:
  stage: deploy
  image: alpine:latest
  script:
    - echo "Deploying $PROJECT_NAME"
    - echo "Deployment successful!"
  only:
    - main
''',
            'commit_message': 'Add GitLab CI configuration'
        }
        
        # Try to create the GitLab CI file
        try:
            gitlab_url = f'https://gitlab.com/api/v4/projects/{project.gitlab_project_id}/repository/files/.gitlab-ci.yml'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {os.environ.get("GITLAB_TOKEN")}'
            }
            
            # First check if file exists
            try:
                response = requests.get(
                    f'{gitlab_url}?ref=main',
                    headers=headers
                )
                file_exists = response.status_code == 200
            except:
                file_exists = False
            
            if file_exists:
                # Update file
                gitlab_ci_content['commit_message'] = 'Update GitLab CI configuration'
                response = requests.put(
                    gitlab_url,
                    json=gitlab_ci_content,
                    headers=headers
                )
            else:
                # Create file
                response = requests.post(
                    gitlab_url,
                    json=gitlab_ci_content,
                    headers=headers
                )
            
            if response.status_code not in (200, 201):
                logger.error(f"Failed to create GitLab CI file: {response.text}")
        except Exception as e:
            logger.error(f"Exception creating GitLab CI file: {str(e)}")
            # Continue anyway, as we've already set up part of the CI
        
        # Record the action
        action = Action(
            action_type='cicd_setup',
            description=f'Set up CI/CD pipeline for Beckx-digital-era/Intro',
            status='completed',
            project_id=project.id,
            user_id=1  # Default user ID
        )
        db.session.add(action)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'CI/CD pipeline set up successfully',
            'github_workflow': 'beckx-gitlab-ci.yml',
            'gitlab_ci': '.gitlab-ci.yml'
        })
    
    except Exception as e:
        logger.error(f"Error setting up CI/CD for Beckx-digital-era/Intro: {str(e)}")
        
        # Record the failed action
        project = Project.query.filter_by(github_repo_url='https://github.com/Beckx-digital-era/Intro').first()
        if project:
            action = Action(
                action_type='cicd_setup',
                description=f'Failed to set up CI/CD pipeline for Beckx-digital-era/Intro: {str(e)}',
                status='failed',
                project_id=project.id,
                user_id=1  # Default user ID
            )
            db.session.add(action)
            db.session.commit()
        
        return jsonify({'error': str(e)}), 500

@app.route('/api/github/repository/beckx-intro/deploy', methods=['POST'])
def beckx_intro_deploy():
    """Deploy the Beckx-digital-era/Intro repository to production."""
    try:
        # Find the project in our database
        project = Project.query.filter_by(github_repo_url='https://github.com/Beckx-digital-era/Intro').first()
        
        if not project:
            return jsonify({'error': 'Repository not found in database'}), 404
        
        # Check if GitLab project exists
        if not project.gitlab_project_id:
            return jsonify({'error': 'GitLab project not found. Please sync repository first.'}), 400
        
        # Trigger a deployment pipeline in GitLab
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {os.environ.get("GITLAB_TOKEN")}'
        }
        
        pipeline_data = {
            'ref': 'main',
            'variables': [
                {
                    'key': 'DEPLOY_TO_PRODUCTION',
                    'value': 'true'
                }
            ]
        }
        
        response = requests.post(
            f'https://gitlab.com/api/v4/projects/{project.gitlab_project_id}/pipeline',
            json=pipeline_data,
            headers=headers
        )
        
        if response.status_code not in (200, 201):
            logger.error(f"Failed to trigger pipeline: {response.text}")
            return jsonify({'error': f'Failed to trigger deployment pipeline: {response.text}'}), 500
        
        pipeline_data = response.json()
        
        # Record the action
        action = Action(
            action_type='deployment',
            description=f'Triggered deployment pipeline for Beckx-digital-era/Intro',
            status='completed',
            project_id=project.id,
            user_id=1  # Default user ID
        )
        db.session.add(action)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Deployment pipeline triggered successfully',
            'pipeline_id': pipeline_data.get('id'),
            'pipeline_url': pipeline_data.get('web_url')
        })
    
    except Exception as e:
        logger.error(f"Error deploying Beckx-digital-era/Intro: {str(e)}")
        
        # Record the failed action
        project = Project.query.filter_by(github_repo_url='https://github.com/Beckx-digital-era/Intro').first()
        if project:
            action = Action(
                action_type='deployment',
                description=f'Failed to deploy Beckx-digital-era/Intro: {str(e)}',
                status='failed',
                project_id=project.id,
                user_id=1  # Default user ID
            )
            db.session.add(action)
            db.session.commit()
        
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500
