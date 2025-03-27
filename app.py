import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

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

# Configure the SQLite database for development
# In production, this would be replaced with a proper database URL
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///devops_ai.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the SQLAlchemy extension
db.init_app(app)

# Import routes after app is initialized to avoid circular imports
from routes import *

with app.app_context():
    # Import the models for table creation
    import models
    
    # Create all database tables
    db.create_all()
    
    logger.info("Database tables created successfully")

# Register GitLab token from environment variable
app.config["GITLAB_TOKEN"] = os.environ.get("GITLAB_TOKEN", "")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
