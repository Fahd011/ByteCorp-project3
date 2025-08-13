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
from sqlalchemy import text

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

def add_retry_fields():
    """Add retry_attempts and final_error fields to import_results table"""
    with app.app_context():
        with db.engine.connect() as conn:
            # Add retry_attempts column
            conn.execute(text("""
                ALTER TABLE import_results 
                ADD COLUMN IF NOT EXISTS retry_attempts INTEGER DEFAULT 0
            """))
            
            # Add final_error column
            conn.execute(text("""
                ALTER TABLE import_results 
                ADD COLUMN IF NOT EXISTS final_error TEXT
            """))
            
            conn.commit()
            print("✅ Retry fields added to import_results table successfully!")

if __name__ == '__main__':
    """Quick database setup for development."""
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully!")
        print("📝 Note: For production, use 'flask db migrate' and 'flask db upgrade'")
        
        # Add retry fields to existing table
        add_retry_fields()