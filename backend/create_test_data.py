import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import User, UserBillingCredential, BillingResult
from app.utils import hash_password
from datetime import datetime
import uuid

# Load environment variables
load_dotenv()

# Create database connection
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_test_data():
    session = SessionLocal()
    try:
        # Create a test user
        user_id = str(uuid.uuid4())
        test_user = User(
            id=user_id,
            email="test@example.com",
            password_hash=hash_password("password123"),
            created_at=datetime.utcnow()
        )
        session.add(test_user)
        print("✅ Created test user")
        
        # Create a test credential
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
        
        # Create a test billing result (manual upload)
        billing_result = BillingResult(
            id=str(uuid.uuid4()),
            user_billing_credential_id=cred_id,
            azure_blob_url="user_credentials_bills_manual/2025/01/test_user_test_cred_bill.pdf",
            run_time=datetime.utcnow(),
            status="manual_upload",
            year="2025",
            month="01",
            created_at=datetime.utcnow()
        )
        session.add(billing_result)
        print("✅ Created test billing result")
        
        # Commit all changes
        session.commit()
        print("✅ All test data committed successfully!")
        
        # Verify the data
        users = session.query(User).all()
        credentials = session.query(UserBillingCredential).all()
        billing_results = session.query(BillingResult).all()
        
        print(f"\n📊 Database Summary:")
        print(f"  Users: {len(users)}")
        print(f"  Credentials: {len(credentials)}")
        print(f"  Billing Results: {len(billing_results)}")
        
        return {
            "user_id": user_id,
            "credential_id": cred_id,
            "email": "test@example.com",
            "password": "password123"
        }
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error creating test data: {e}")
        return None
    finally:
        session.close()

if __name__ == "__main__":
    result = create_test_data()
    if result:
        print(f"\n🔑 Test Login Credentials:")
        print(f"  Email: {result['email']}")
        print(f"  Password: {result['password']}")
        print(f"  User ID: {result['user_id']}")
        print(f"  Credential ID: {result['credential_id']}")
