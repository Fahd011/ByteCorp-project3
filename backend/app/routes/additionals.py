# Fetch all billing results for a credential_id
from fastapi import APIRouter, Depends, HTTPException
from app.models import BillingResult
from app.db import get_db
from sqlalchemy.orm import Session


from typing import List
from app.db import get_db
from app.utils import hash_password
from app.models import User
from app.routes.auth import verify_token
from config import config

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime

router = APIRouter()


# Removed unused session and result endpoints - no longer needed

# Utility endpoint to create a test user (for development only)
@router.post("/api/create-test-user")
def create_test_user(db: Session = Depends(get_db)):
    """Create a test user for development purposes"""
    test_email = config.ROOT_USER_EMAIL
    test_password = config.ROOT_USER_PASSWORD
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == test_email).first()
    if existing_user:
        return {"message": "Default user already exists", "email": test_email}
    
    # Create new user with hashed password
    hashed_password = hash_password(test_password)
    new_user = User(
        email=test_email,
        password_hash=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "message": "Default user created successfully",
        "email": test_email,
        "password": test_password,
        "user_id": new_user.id
    }


@router.get("/api/billing-results/{credential_id}")
def get_billing_results(credential_id: str, db: Session = Depends(get_db)):
    results = db.query(BillingResult).filter(BillingResult.user_billing_credential_id == credential_id).order_by(BillingResult.run_time.desc()).all()
    return [
        {
            "id": r.id,
            "azure_blob_url": r.azure_blob_url,
            "run_time": r.run_time,
            "status": r.status,
            "year": r.year,
            "month": r.month,
            "created_at": r.created_at
        }
        for r in results
    ]