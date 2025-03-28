import os
import logging
from app import app, db

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import routes after initializing app
import routes  # This imports and registers all the routes

# Try to import GitLab routes
try:
    from gitlab_routes import register_gitlab_routes
    register_gitlab_routes(app)
    logger.info("GitLab routes registered successfully")
except ImportError:
    logger.warning("Could not import gitlab_routes")
except Exception as e:
    logger.error(f"Error registering GitLab routes: {str(e)}")

# Try to import DevOps AI Controller
try:
    from openai_devops_controller import register_devops_routes, initialize as initialize_ai
    register_devops_routes(app)
    initialize_ai()
    logger.info("DevOps AI Controller initialized successfully")
except ImportError:
    logger.warning("Could not import openai_devops_controller")
except Exception as e:
    logger.error(f"Error initializing DevOps AI Controller: {str(e)}")

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
logger.info("DevOps System - Powered by AI")
logger.info("=" * 80)
logger.info("AI-powered DevOps Controller provides intelligent orchestration")
logger.info("All GitLab operations are controlled through GitHub Actions workflows")
logger.info("GitHub Pages serves as the control interface")
logger.info("GitLab is used for CI/CD pipeline execution")
logger.info("=" * 80)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
