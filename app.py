import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the Base class
db = SQLAlchemy(model_class=Base)

# Create the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configure the database
# Use environment DATABASE_URL if available, otherwise sqlite
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///devops_ai.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the SQLAlchemy extension
db.init_app(app)

# Setup login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Register GitLab and GitHub tokens from environment variables
gitlab_token = os.environ.get("GITLAB_TOKEN")
github_token = os.environ.get("GITHUB_TOKEN")

# Check for alternative environment variable names
if not github_token:
    github_token = os.environ.get("GH_TOKEN")

if not gitlab_token:
    gitlab_token = os.environ.get("GL_TOKEN")

# Add tokens to app configuration
if github_token:
    app.config["GITHUB_TOKEN"] = github_token
    logger.info("GitHub token found in environment variables")
else:
    logger.warning("GitHub token not found in environment variables")
    app.config["GITHUB_TOKEN"] = ""

if gitlab_token:
    app.config["GITLAB_TOKEN"] = gitlab_token
    logger.info("GitLab token found in environment variables")
else:
    logger.warning("GitLab token not found in environment variables")
    app.config["GITLAB_TOKEN"] = ""

# Initialize database tables - this is done in main.py 
# to avoid circular imports

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
