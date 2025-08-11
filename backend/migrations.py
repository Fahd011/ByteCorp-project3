# ByteCorp-project3/backend/migrations.py
"""
Database migration configuration for ByteCorp project.
This file sets up Flask-Migrate for database schema management.
"""
from flask import Flask
from flask_migrate import Migrate
from db import db
from config import Config
from models.models import User, ImportSession, ImportResult

def create_app():
    """Create Flask app with migration support."""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    migrate = Migrate(app, db)
    return app

# Create the Flask-Migrate instance for CLI commands
app = create_app()
migrate = Migrate(app, db)

if __name__ == '__main__':
    """Quick database setup for development."""
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully!")
        print("📝 Note: For production, use 'flask db migrate' and 'flask db upgrade'")