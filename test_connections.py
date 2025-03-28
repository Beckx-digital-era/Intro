#!/usr/bin/env python3
"""
Test connections to GitHub and GitLab APIs.

This script tests the connection to both GitHub and GitLab APIs to ensure
that the provided tokens are valid and can retrieve basic information.
"""

import json
import logging
import os
import requests
import sys

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_github_connection():
    """Test connection to GitHub API."""
    logger.info("Testing GitHub API connection...")
    
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.error("GitHub token not found in environment variables.")
        return False
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get("https://api.github.com/user", headers=headers)
        response.raise_for_status()
        
        user_data = response.json()
        logger.info(f"Successfully connected to GitHub API as user: {user_data.get('login')}")
        logger.info(f"User ID: {user_data.get('id')}")
        return True
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to GitHub API: {e}")
        return False

def test_gitlab_connection():
    """Test connection to GitLab API."""
    logger.info("Testing GitLab API connection...")
    
    token = os.environ.get("GITLAB_TOKEN")
    if not token:
        logger.error("GitLab token not found in environment variables.")
        return False
    
    headers = {
        "PRIVATE-TOKEN": token
    }
    
    try:
        response = requests.get("https://gitlab.com/api/v4/user", headers=headers)
        response.raise_for_status()
        
        user_data = response.json()
        logger.info(f"Successfully connected to GitLab API as user: {user_data.get('username')}")
        logger.info(f"User ID: {user_data.get('id')}")
        return True
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to GitLab API: {e}")
        return False

if __name__ == "__main__":
    github_success = test_github_connection()
    gitlab_success = test_gitlab_connection()
    
    if github_success and gitlab_success:
        logger.info("All API connections successful!")
        sys.exit(0)
    else:
        logger.error("One or more API connections failed.")
        sys.exit(1)