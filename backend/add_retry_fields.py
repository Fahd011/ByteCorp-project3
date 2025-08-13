#!/usr/bin/env python3
"""
Script to add retry fields to existing import_results table.
Run this script to add the new columns without affecting existing data.
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

def add_retry_fields():
    """Add retry_attempts and final_error fields to import_results table"""
    try:
        from migrations import add_retry_fields
        add_retry_fields()
        return True
    except Exception as e:
        print(f"Error adding retry fields: {e}")
        return False

def main():
    """Main function."""
    print("Adding Retry Fields to Database")
    print("=" * 40)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Add retry fields
    if not add_retry_fields():
        sys.exit(1)
    
    print("\n✅ Retry fields added successfully!")
    print("\nThe following fields have been added to the import_results table:")
    print("   - retry_attempts (INTEGER, default 0)")
    print("   - final_error (TEXT)")
    print("\nExisting data has been preserved.")

if __name__ == '__main__':
    main()
