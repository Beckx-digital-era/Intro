#!/usr/bin/env python3

import logging
import json
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_github_connection():
    """Test connection to GitHub API."""
    logger.info("Testing GitHub API connection...")
    try:
        from github_api import get_github_repositories
        repos = get_github_repositories()
        
        if not repos:
            logger.info("Successfully connected to GitHub API, but no repositories found.")
        else:
            logger.info(f"Successfully connected to GitHub API. Found {len(repos)} repositories.")
            # Print first 3 repos
            for i, repo in enumerate(repos[:3]):
                logger.info(f"  {i+1}. {repo.get('name', 'Unknown')} ({repo.get('html_url', 'No URL')})")
        
        return True
    except Exception as e:
        logger.error(f"Failed to connect to GitHub API: {str(e)}")
        return False

def test_gitlab_connection():
    """Test connection to GitLab API."""
    logger.info("Testing GitLab API connection...")
    try:
        from gitlab_api import get_gitlab_projects
        projects = get_gitlab_projects()
        
        if isinstance(projects, dict) and projects.get('status') == 'error':
            logger.error(f"GitLab API error: {projects.get('message', 'Unknown error')}")
            return False
        
        if not projects:
            logger.info("Successfully connected to GitLab API, but no projects found.")
        else:
            logger.info(f"Successfully connected to GitLab API. Found {len(projects)} projects.")
            # Print first 3 projects
            for i, project in enumerate(projects[:3]):
                logger.info(f"  {i+1}. {project.get('name', 'Unknown')} (ID: {project.get('id', 'No ID')})")
        
        return True
    except Exception as e:
        logger.error(f"Failed to connect to GitLab API: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting API connection tests...")
    
    github_success = test_github_connection()
    gitlab_success = test_gitlab_connection()
    
    logger.info("\nConnection test results:")
    logger.info(f"GitHub API: {'SUCCESS' if github_success else 'FAILED'}")
    logger.info(f"GitLab API: {'SUCCESS' if gitlab_success else 'FAILED'}")
    
    if github_success and gitlab_success:
        logger.info("All connections successful!")
        sys.exit(0)
    else:
        logger.error("One or more connection tests failed.")
        sys.exit(1)