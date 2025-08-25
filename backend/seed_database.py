#!/usr/bin/env python3
"""
Database Seeding Script
Creates test data for development purposes
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import models after setting up the path
from app.models import User, UserBillingCredential, BillingResult
from app.utils import hash_password

# Load environment variables
load_dotenv()

def seed_database():
    """Seed the database with test data"""
    
    # Get database URL
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in environment variables!")
        return False
    
    print(f"📋 Using database: {DATABASE_URL}")
    
    try:
        # Create engine and session
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        print("✅ Database connection established")
        
        # Check if data already exists
        existing_users = session.query(User).count()
        existing_credentials = session.query(UserBillingCredential).count()
        existing_billing_results = session.query(BillingResult).count()
        
        print(f"📊 Current database state:")
        print(f"  Users: {existing_users}")
        print(f"  Credentials: {existing_credentials}")
        print(f"  Billing Results: {existing_billing_results}")
        
        if existing_users > 0:
            print("⚠️  Database already has data. Skipping seeding.")
            return True
        
        # Create test user
        user_id = str(uuid.uuid4())
        test_user = User(
            id=user_id,
            email="test@example.com",
            password_hash=hash_password("password123"),
            created_at=datetime.utcnow()
        )
        session.add(test_user)
        print("✅ Created test user")
        
        # Create test credential
        cred_id = str(uuid.uuid4())
        test_credential = UserBillingCredential(
            id=cred_id,
            user_id=user_id,
            email="test@example.com",
            password="password123",
            client_name="Test Client",
            utility_co_name="Test Utility",
            cred_id="TEST123",
            login_url="https://example.com/login",
            billing_url="https://example.com/billing",
            created_at=datetime.utcnow()
        )
        session.add(test_credential)
        print("✅ Created test credential")
        
        # Create test billing results (both automated and manual)
        
        # Automated billing result
        auto_billing_result = BillingResult(
            id=str(uuid.uuid4()),
            user_billing_credential_id=cred_id,
            azure_blob_url="user_credentials_bills/2025/01/test_auto_bill.pdf",
            run_time=datetime.utcnow(),
            status="completed",
            year="2025",
            month="01",
            created_at=datetime.utcnow()
        )
        session.add(auto_billing_result)
        print("✅ Created automated billing result")
        
        # Manual billing result
        manual_billing_result = BillingResult(
            id=str(uuid.uuid4()),
            user_billing_credential_id=cred_id,
            azure_blob_url="user_credentials_bills_manual/2024/12/test_manual_bill.pdf",
            run_time=datetime.utcnow(),
            status="manual_upload",
            year="2024",
            month="12",
            created_at=datetime.utcnow()
        )
        session.add(manual_billing_result)
        print("✅ Created manual billing result")
        
        # Commit all changes
        session.commit()
        print("✅ All test data committed successfully!")
        
        # Verify the data
        final_users = session.query(User).count()
        final_credentials = session.query(UserBillingCredential).count()
        final_billing_results = session.query(BillingResult).count()
        
        print(f"\n📊 Final database state:")
        print(f"  Users: {final_users}")
        print(f"  Credentials: {final_credentials}")
        print(f"  Billing Results: {final_billing_results}")
        
        print(f"\n🔑 Test Login Credentials:")
        print(f"  Email: test@example.com")
        print(f"  Password: password123")
        print(f"  User ID: {user_id}")
        print(f"  Credential ID: {cred_id}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

if __name__ == "__main__":
    print("🚀 Starting Database Seeding...\n")
    
    success = seed_database()
    
    if success:
        print("\n🎉 Database seeding completed successfully!")
        print("You can now login to the application with the test credentials above.")
    else:
        print("\n❌ Database seeding failed!")
        sys.exit(1)
