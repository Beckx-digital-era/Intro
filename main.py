import os
import logging
from app import app, db
import routes  # This imports and registers all the routes
from gitlab_routes import register_gitlab_routes

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Register GitLab routes
register_gitlab_routes(app)

# Initialize database if needed
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")

# Check if GitHub token is available
if os.environ.get("GITHUB_TOKEN"):
    logger.info("GitHub token found in environment variables")
else:
    logger.warning("GitHub token not found in environment variables")

# Check if GitLab token is available
if os.environ.get("GITLAB_TOKEN"):
    logger.info("GitLab token found in environment variables")
else:
    logger.warning("GitLab token not found in environment variables")

# Print startup message with GitHub integration info
logger.info("=" * 80)
logger.info("DevOps System - GitLab operations controlled by GitHub Actions")
logger.info("=" * 80)
logger.info("All GitLab operations are controlled through GitHub Actions workflows")
logger.info("GitHub Pages serves as the control interface")
logger.info("GitLab is used for CI/CD pipeline execution")
logger.info("=" * 80)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
