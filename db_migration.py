"""
Database migration script to add GitHub ID column to the User table.

This is a standalone script that should be run after updating the models.py file
with the new github_id field.
"""

import os
import logging
from app import app, db
from sqlalchemy import inspect, Column, String

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns

def add_github_id_column():
    """Add the github_id column to the User table if it doesn't exist."""
    with app.app_context():
        try:
            # Check if the column already exists
            if not column_exists('user', 'github_id'):
                logger.info("Adding 'github_id' column to the User table...")
                conn = db.engine.connect()
                conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN github_id VARCHAR(64) UNIQUE"))
                conn.close()
                logger.info("Column 'github_id' added successfully!")
            else:
                logger.info("Column 'github_id' already exists in the User table.")
        except Exception as e:
            logger.error(f"Error adding 'github_id' column: {e}")
            raise

if __name__ == "__main__":
    logger.info("Starting database migration...")
    add_github_id_column()
    logger.info("Database migration completed!")