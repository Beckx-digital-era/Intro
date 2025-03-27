"""
Secure API Authentication Module

This module provides enhanced security and authentication handling for GitHub and GitLab APIs.
It implements token validation, rate limiting protection, secure token storage,
and comprehensive error handling.
"""

import os
import time
import logging
import hashlib
import base64
import json
import requests
from functools import wraps
from datetime import datetime, timedelta
import hmac
from models import db, User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 5
RETRY_BACKOFF = 1.5  # Exponential backoff multiplier
RATE_LIMIT_THRESHOLD = 0.1  # 10% of rate limit remaining
TOKEN_REFRESH_WINDOW = 30  # Days before token expiration to refresh

class TokenManager:
    """Manages API tokens with enhanced security features."""
    
    def __init__(self, service_name):
        """Initialize token manager for a specific service.
        
        Args:
            service_name (str): Name of the service (e.g., 'github', 'gitlab')
        """
        self.service_name = service_name.lower()
        self.token_cache = {}
        self.rate_limit_info = {}
    
    def get_token_from_env(self):
        """Get token from environment variables with appropriate naming."""
        env_var_names = {
            'github': ['GITHUB_TOKEN', 'GH_TOKEN'],
            'gitlab': ['GITLAB_TOKEN', 'GL_TOKEN'],
        }
        
        if self.service_name not in env_var_names:
            raise ValueError(f"Unsupported service: {self.service_name}")
        
        for var_name in env_var_names[self.service_name]:
            token = os.environ.get(var_name)
            if token:
                return token
        
        return None
    
    def get_token_from_db(self, user_id=None):
        """Get token from database for a specific user or default."""
        if user_id:
            user = User.query.get(user_id)
            if user:
                if self.service_name == 'github' and hasattr(user, 'github_token'):
                    return user.github_token
                elif self.service_name == 'gitlab' and hasattr(user, 'gitlab_token'):
                    return user.gitlab_token
        
        # Get default token from the first user
        user = User.query.first()
        if user:
            if self.service_name == 'github' and hasattr(user, 'github_token'):
                return user.github_token
            elif self.service_name == 'gitlab' and hasattr(user, 'gitlab_token'):
                return user.gitlab_token
        
        return None
    
    def get_token(self, user_id=None):
        """Get a valid token with caching."""
        cache_key = f"{self.service_name}_{user_id}"
        
        # Check if we have a cached and valid token
        if cache_key in self.token_cache:
            cached = self.token_cache[cache_key]
            if cached['expires_at'] > datetime.utcnow():
                return cached['token']
        
        # Try to get token from environment and database
        token = self.get_token_from_env() or self.get_token_from_db(user_id)
        
        if not token:
            raise ValueError(f"No {self.service_name.capitalize()} token found")
        
        # Validate the token and store in cache
        if self.validate_token(token):
            # Default expiration is 24 hours from now
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            self.token_cache[cache_key] = {
                'token': token,
                'expires_at': expires_at
            }
            
            return token
        
        raise ValueError(f"Invalid {self.service_name.capitalize()} token")
    
    def validate_token(self, token):
        """Validate token by making a test API call.
        
        Args:
            token (str): API token to validate
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        try:
            if self.service_name == 'github':
                response = requests.get(
                    'https://api.github.com/user',
                    headers={
                        'Authorization': f'token {token}',
                        'Accept': 'application/vnd.github.v3+json'
                    }
                )
            elif self.service_name == 'gitlab':
                response = requests.get(
                    'https://gitlab.com/api/v4/user',
                    headers={
                        'PRIVATE-TOKEN': token
                    }
                )
            else:
                return False
            
            # Update rate limit info
            self.update_rate_limit_info(response)
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error validating {self.service_name} token: {str(e)}")
            return False
    
    def update_rate_limit_info(self, response):
        """Extract and store rate limit information from API response."""
        try:
            if self.service_name == 'github':
                if 'X-RateLimit-Limit' in response.headers and 'X-RateLimit-Remaining' in response.headers:
                    limit = int(response.headers['X-RateLimit-Limit'])
                    remaining = int(response.headers['X-RateLimit-Remaining'])
                    reset = int(response.headers.get('X-RateLimit-Reset', 0))
                    
                    self.rate_limit_info = {
                        'limit': limit,
                        'remaining': remaining,
                        'reset': reset,
                        'percent_remaining': remaining / limit if limit > 0 else 1
                    }
            elif self.service_name == 'gitlab':
                if 'RateLimit-Limit' in response.headers and 'RateLimit-Remaining' in response.headers:
                    limit = int(response.headers['RateLimit-Limit'])
                    remaining = int(response.headers['RateLimit-Remaining'])
                    reset = int(response.headers.get('RateLimit-Reset', 0))
                    
                    self.rate_limit_info = {
                        'limit': limit,
                        'remaining': remaining,
                        'reset': reset,
                        'percent_remaining': remaining / limit if limit > 0 else 1
                    }
        except Exception as e:
            logger.error(f"Error updating rate limit info: {str(e)}")
    
    def should_throttle(self):
        """Check if requests should be throttled based on rate limit."""
        if not self.rate_limit_info:
            return False
        
        percent_remaining = self.rate_limit_info.get('percent_remaining', 1)
        return percent_remaining < RATE_LIMIT_THRESHOLD
    
    def clear_cache(self):
        """Clear the token cache."""
        self.token_cache = {}


class APISecurityManager:
    """Manages API security with enhanced features."""
    
    def __init__(self):
        self.github_token_manager = TokenManager('github')
        self.gitlab_token_manager = TokenManager('gitlab')
        self.request_history = {}
    
    def secure_github_request(self, endpoint, method="GET", data=None, params=None, user_id=None, max_retries=MAX_RETRIES):
        """Make a secure request to the GitHub API with retries and rate limit handling.
        
        Args:
            endpoint (str): GitHub API endpoint (without the base URL)
            method (str): HTTP method (GET, POST, PUT, DELETE)
            data (dict): Request body for POST/PUT requests
            params (dict): Query parameters
            user_id (int): User ID to use specific tokens
            max_retries (int): Maximum number of retry attempts
            
        Returns:
            dict: API response as JSON
            
        Raises:
            Exception: If the request fails after all retries
        """
        return self._make_secure_request(
            'github',
            endpoint,
            method,
            data,
            params,
            user_id,
            max_retries
        )
    
    def secure_gitlab_request(self, endpoint, method="GET", data=None, params=None, user_id=None, max_retries=MAX_RETRIES):
        """Make a secure request to the GitLab API with retries and rate limit handling.
        
        Args:
            endpoint (str): GitLab API endpoint (without the base URL)
            method (str): HTTP method (GET, POST, PUT, DELETE)
            data (dict): Request body for POST/PUT requests
            params (dict): Query parameters
            user_id (int): User ID to use specific tokens
            max_retries (int): Maximum number of retry attempts
            
        Returns:
            dict: API response as JSON
            
        Raises:
            Exception: If the request fails after all retries
        """
        return self._make_secure_request(
            'gitlab',
            endpoint,
            method,
            data,
            params,
            user_id,
            max_retries
        )
    
    def _make_secure_request(self, service, endpoint, method, data, params, user_id, max_retries):
        """Generic method to make secure API requests with retries and error handling."""
        token_manager = self.github_token_manager if service == 'github' else self.gitlab_token_manager
        
        # Add idempotency key for non-GET requests to prevent duplicate operations
        idempotency_key = None
        if method.upper() != 'GET':
            idempotency_key = self._generate_idempotency_key(service, endpoint, method, data, params)
            
            # Check if this exact request was recently successful
            if self._is_duplicate_request(idempotency_key):
                logger.info(f"Duplicate {service} request detected, using cached response")
                return self.request_history[idempotency_key]['response']
        
        # Configure base URL and headers based on service
        if service == 'github':
            base_url = 'https://api.github.com'
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'GitHubGitLabBridge'
            }
        else:  # gitlab
            base_url = 'https://gitlab.com/api/v4'
            headers = {}
        
        # Make sure the endpoint doesn't start with a slash
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
        
        url = f"{base_url}/{endpoint}"
        
        # Add idempotency header if needed
        if idempotency_key:
            if service == 'github':
                headers['X-GitHub-Request-Id'] = idempotency_key
            else:
                headers['Idempotency-Key'] = idempotency_key
        
        retry_count = 0
        last_exception = None
        
        while retry_count < max_retries:
            try:
                # Get fresh token
                token = token_manager.get_token(user_id)
                
                # Check if we should throttle requests due to rate limiting
                if token_manager.should_throttle():
                    wait_time = 10  # Default wait time in seconds
                    if 'reset' in token_manager.rate_limit_info:
                        reset_time = datetime.fromtimestamp(token_manager.rate_limit_info['reset'])
                        wait_time = max(1, (reset_time - datetime.utcnow()).total_seconds())
                    
                    logger.warning(f"Rate limit nearly exhausted, waiting {wait_time} seconds")
                    time.sleep(wait_time)
                
                # Add auth headers
                if service == 'github':
                    headers['Authorization'] = f'token {token}'
                else:
                    headers['PRIVATE-TOKEN'] = token
                
                # Convert data to JSON if needed
                json_data = None
                if data is not None:
                    json_data = data
                
                # Make the actual request
                response = requests.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    json=json_data,
                    params=params
                )
                
                # Update rate limit info
                token_manager.update_rate_limit_info(response)
                
                # Handle rate limiting
                if response.status_code == 429:
                    wait_time = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited, waiting {wait_time} seconds")
                    time.sleep(wait_time)
                    retry_count += 1
                    continue
                
                # Handle other error responses
                if response.status_code >= 400:
                    error_message = f"{service.capitalize()} API error: {response.status_code}"
                    try:
                        error_data = response.json()
                        error_message += f" - {json.dumps(error_data)}"
                    except:
                        error_message += f" - {response.text}"
                    
                    logger.error(error_message)
                    
                    # Special handling for specific error codes
                    if response.status_code == 401:
                        # Clear token cache on authentication errors
                        token_manager.clear_cache()
                        raise ValueError(f"Authentication failed for {service}")
                    elif response.status_code in (404, 400):
                        # Don't retry client errors
                        raise ValueError(error_message)
                    
                    # For other errors, retry with backoff
                    retry_wait = RETRY_BACKOFF ** retry_count
                    logger.info(f"Retrying in {retry_wait} seconds...")
                    time.sleep(retry_wait)
                    retry_count += 1
                    continue
                
                # Process successful response
                result = response.json() if response.text.strip() else {}
                
                # Store in history for idempotency if needed
                if idempotency_key:
                    self.request_history[idempotency_key] = {
                        'timestamp': datetime.utcnow(),
                        'response': result
                    }
                
                return result
                
            except Exception as e:
                last_exception = e
                logger.error(f"Error in {service} API request: {str(e)}")
                retry_wait = RETRY_BACKOFF ** retry_count
                logger.info(f"Retrying in {retry_wait} seconds...")
                time.sleep(retry_wait)
                retry_count += 1
        
        # If we've exhausted all retries
        error_message = f"Failed to make {service} API request after {max_retries} attempts"
        if last_exception:
            error_message += f": {str(last_exception)}"
        
        raise Exception(error_message)
    
    def _generate_idempotency_key(self, service, endpoint, method, data, params):
        """Generate a unique key for a request to prevent duplicates."""
        key_parts = [
            service,
            endpoint,
            method.upper(),
            json.dumps(data, sort_keys=True) if data else '',
            json.dumps(params, sort_keys=True) if params else ''
        ]
        
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_duplicate_request(self, idempotency_key):
        """Check if a request with this idempotency key was recently successful."""
        if idempotency_key in self.request_history:
            # Only consider it a duplicate if it was made in the last 5 minutes
            timestamp = self.request_history[idempotency_key]['timestamp']
            age = (datetime.utcnow() - timestamp).total_seconds()
            return age < 300  # 5 minutes
        
        return False
    
    def validate_webhook_signature(self, payload, signature, secret, service):
        """Validate webhook signature to ensure it's legitimate.
        
        Args:
            payload (bytes): Raw request body
            signature (str): Signature from the webhook header
            secret (str): Webhook secret used to sign the payload
            service (str): 'github' or 'gitlab'
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        if not payload or not signature or not secret:
            return False
        
        try:
            if service == 'github':
                # GitHub uses "sha1=..." format
                algorithm, provided_sig = signature.split('=', 1)
                if algorithm != 'sha1':
                    return False
                
                # Calculate expected signature
                mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha1)
                expected_sig = mac.hexdigest()
                
                # Compare signatures
                return hmac.compare_digest(provided_sig, expected_sig)
            
            elif service == 'gitlab':
                # GitLab uses a token in the URL and a simple token in the header
                return signature == secret
            
            return False
        
        except Exception as e:
            logger.error(f"Error validating webhook signature: {str(e)}")
            return False


# Create instances for global use
github_token_manager = TokenManager('github')
gitlab_token_manager = TokenManager('gitlab')
api_security_manager = APISecurityManager()

# Decorator for API rate limit protection
def rate_limit_safe(service):
    """Decorator to make functions safe from API rate limiting.
    
    Args:
        service (str): 'github' or 'gitlab'
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            token_manager = github_token_manager if service == 'github' else gitlab_token_manager
            
            # Check rate limits
            if token_manager.should_throttle():
                wait_time = 30  # Default wait time
                if 'reset' in token_manager.rate_limit_info:
                    reset_time = datetime.fromtimestamp(token_manager.rate_limit_info['reset'])
                    wait_time = max(1, (reset_time - datetime.utcnow()).total_seconds())
                
                logger.warning(f"Rate limit nearly exhausted for {service}, waiting {wait_time} seconds")
                time.sleep(wait_time)
            
            # Call the original function
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def get_secure_github_token():
    """Get a valid GitHub token with enhanced security checks."""
    return github_token_manager.get_token()


def get_secure_gitlab_token():
    """Get a valid GitLab token with enhanced security checks."""
    return gitlab_token_manager.get_token()


def make_secure_github_request(endpoint, method="GET", data=None, params=None, user_id=None):
    """Make a secure GitHub API request with enhanced error handling."""
    return api_security_manager.secure_github_request(
        endpoint, method, data, params, user_id
    )


def make_secure_gitlab_request(endpoint, method="GET", data=None, params=None, user_id=None):
    """Make a secure GitLab API request with enhanced error handling."""
    return api_security_manager.secure_gitlab_request(
        endpoint, method, data, params, user_id
    )