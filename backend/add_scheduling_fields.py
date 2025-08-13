#!/usr/bin/env python3
"""
Database migration script to add scheduling fields to ImportSession table.
Run this script to update your existing database schema.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# Load environment variables from the parent directory (where .env is located)
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

def add_scheduling_fields():
    """Add scheduling fields to the ImportSession table"""
    
    # Get database URL from environment variables
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL environment variable not found!")
        print("Please make sure your .env file contains the DATABASE_URL variable.")
        print(f"Looking for .env file at: {env_path}")
        sys.exit(1)
    
    print(f"🔗 Connecting to database: {database_url.split('@')[-1] if '@' in database_url else 'database'}")
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Check if columns already exist
        with engine.connect() as conn:
            # Check if is_scheduled column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'import_sessions' 
                AND column_name = 'is_scheduled'
            """))
            
            if result.fetchone():
                print("✅ Scheduling fields already exist. Skipping migration.")
                return
            
            print("📝 Adding scheduling fields to import_sessions table...")
            
            # Add new columns
            conn.execute(text("""
                ALTER TABLE import_sessions 
                ADD COLUMN is_scheduled BOOLEAN DEFAULT FALSE
            """))
            
            conn.execute(text("""
                ALTER TABLE import_sessions 
                ADD COLUMN schedule_type VARCHAR(20)
            """))
            
            conn.execute(text("""
                ALTER TABLE import_sessions 
                ADD COLUMN schedule_config JSON
            """))
            
            conn.execute(text("""
                ALTER TABLE import_sessions 
                ADD COLUMN next_run TIMESTAMP
            """))
            
            conn.execute(text("""
                ALTER TABLE import_sessions 
                ADD COLUMN last_scheduled_run TIMESTAMP
            """))
            
            conn.commit()
            print("✅ Successfully added scheduling fields to import_sessions table!")
            
    except OperationalError as e:
        print(f"❌ Database connection error: {e}")
        print("Please check your DATABASE_URL in the .env file.")
        print(f"Current DATABASE_URL: {database_url}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Starting database migration for scheduling fields...")
    print("=" * 60)
    add_scheduling_fields()
    print("✨ Migration completed!")
