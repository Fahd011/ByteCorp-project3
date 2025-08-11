#!/usr/bin/env python3
"""
Database setup script for ByteCorp project.
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
        from migrations import app, db
        
        with app.app_context():
            # Create all tables
            db.create_all()
            print("Database tables created successfully!")
            
            # Print table information
            from models.models import User, ImportSession, ImportResult
            print(f"Created tables:")
            print(f"   - {User.__tablename__}")
            print(f"   - {ImportSession.__tablename__}")
            print(f"   - {ImportResult.__tablename__}")
            
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False
    
    return True

def main():
    """Main setup function."""
    print("ByteCorp Database Setup")
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
