import os
import requests
import logging
from urllib.parse import urlencode
from flask import current_app, redirect, url_for, request, session, flash
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# GitHub OAuth constants
GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_BASE_URL = "https://api.github.com"

def get_github_oauth_config():
    """Get GitHub OAuth client ID and secret from environment variables."""
    client_id = os.environ.get("GITHUB_CLIENT_ID") or current_app.config.get("GITHUB_CLIENT_ID")
    client_secret = os.environ.get("GITHUB_CLIENT_SECRET") or current_app.config.get("GITHUB_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        logger.error("GitHub OAuth credentials not found. Using GITHUB_TOKEN for authentication instead.")
        return None, None
    
    return client_id, client_secret

def get_github_login_url(callback_url=None):
    """Generate GitHub OAuth login URL."""
    client_id, _ = get_github_oauth_config()
    
    if not client_id:
        logger.error("Cannot generate GitHub login URL: missing client ID")
        return None
    
    if not callback_url:
        callback_url = url_for('github_callback', _external=True)
    
    params = {
        'client_id': client_id,
        'redirect_uri': callback_url,
        'scope': 'user repo admin:repo_hook',  # Adjust scopes based on your needs
        'state': os.urandom(16).hex()  # Random state to prevent CSRF
    }
    
    # Store state in session for verification
    session['github_oauth_state'] = params['state']
    
    return f"{GITHUB_AUTH_URL}?{urlencode(params)}"

def get_github_token_from_code(code, callback_url=None):
    """Exchange authorization code for access token."""
    client_id, client_secret = get_github_oauth_config()
    
    if not client_id or not client_secret:
        logger.error("Cannot exchange code for token: missing OAuth credentials")
        return None
    
    if not callback_url:
        callback_url = url_for('github_callback', _external=True)
    
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'redirect_uri': callback_url
    }
    
    headers = {
        'Accept': 'application/json'
    }
    
    try:
        response = requests.post(GITHUB_TOKEN_URL, data=data, headers=headers)
        response.raise_for_status()
        
        # Parse the response
        token_data = response.json()
        access_token = token_data.get('access_token')
        
        if not access_token:
            logger.error(f"Failed to obtain access token: {token_data}")
            return None
        
        return access_token
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error exchanging code for token: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            logger.error(f"Response content: {e.response.text}")
        return None

def get_github_user_info(access_token):
    """Get GitHub user information using the access token."""
    if not access_token:
        logger.error("Cannot get user info: no access token provided")
        return None
    
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(f"{GITHUB_API_BASE_URL}/user", headers=headers)
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting user info: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            logger.error(f"Response content: {e.response.text}")
        return None

def github_auth_required(view_function):
    """Decorator to require GitHub authentication."""
    from functools import wraps
    
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated through GitHub
        if 'github_token' not in session:
            # Store the original URL to redirect back after authentication
            session['next_url'] = request.url
            
            # Redirect to GitHub login
            login_url = get_github_login_url()
            if not login_url:
                flash('GitHub authentication is not configured properly', 'danger')
                return redirect(url_for('login'))
            
            return redirect(login_url)
        
        # User is authenticated, proceed with the view
        return view_function(*args, **kwargs)
    
    return decorated_function