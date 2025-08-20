#!/usr/bin/env python3
"""
Database setup script for Sagiliti project.
Run this script to set up the database locally.
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_environment():
    """Check if required environment variables are set."""
    required_vars = ['DATABASE_URL', 'JWT_SECRET_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease create a .env file with the required variables.")
        return False
    
    print("Environment variables check passed!")
    return True

def setup_database():
    """Set up the database with all tables."""
    try:
        from .db import db
        from ..config import Config
        from flask import Flask
        
        # Create a Flask app with the database configuration
        app = Flask(__name__)
        app.config.from_object(Config)
        db.init_app(app)
        
        with app.app_context():
            # Import models to register them with SQLAlchemy
            from ..models.models import User, ImportSession, ImportResult
            
            # Create all tables
            db.create_all()
            print("Database tables created successfully!")
            
            # Print table information
            print(f"Created tables:")
            print(f"   - users")
            print(f"   - import_sessions")
            print(f"   - import_results")
            
            # Verify the columns were created by checking the database directly
            print("\nVerifying table structure...")
            with db.engine.connect() as conn:
                # Check ImportSession columns
                result = conn.execute(db.text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'import_sessions' 
                    ORDER BY ordinal_position
                """))
                session_columns = [row[0] for row in result.fetchall()]
                print(f"ImportSession columns: {session_columns}")
                
                # Check ImportResult columns
                result = conn.execute(db.text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'import_results' 
                    ORDER BY ordinal_position
                """))
                result_columns = [row[0] for row in result.fetchall()]
                print(f"ImportResult columns: {result_columns}")
            
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False
    
    return True

def main():
    """Main setup function."""
    print("Sagiliti Database Setup")
    print("=" * 40)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Setup database
    if not setup_database():
        sys.exit(1)
    
    print("\nDatabase setup completed successfully!")
    print("\nNext steps:")
    print("1. Start the backend server: python app.py")
    print("2. Start the frontend: cd ../frontend && npm start")
    print("3. Access the application at http://localhost:3000")

if __name__ == '__main__':
    main()
