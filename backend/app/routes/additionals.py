# Fetch all billing results for a credential_id
import io
import csv
import json
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config import config
from app.db import get_db
from app.models import BillingResult, Provider, ProviderResponse, UserBillingCredential, AuditLog, User, BillingResultResponse
from app.routes.auth import verify_token, get_actual_user_id
from app.utils import hash_password
from typing import List

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
    
    # Get the credential to access email/username
    credential = db.query(UserBillingCredential).filter(UserBillingCredential.id == credential_id).first()
    username = credential.email if credential else "unknown"
    
    return [
        {
            "id": r.id,
            "azure_blob_url": r.azure_blob_url,
            "excel_blob_url": r.excel_blob_url, 
            "json_blob_url": r.json_blob_url,    
            "run_time": r.run_time,
            "status": r.status,
            "year": r.year,
            "month": r.month,
            "created_at": r.created_at,
            "username": username
        }
        for r in results
    ]

@router.get("/api/billing-results", response_model=List[BillingResultResponse])
def get_all_billing_results(
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get all billing results for the current user across all credentials"""
    # Handle root user case: if user_id is an email, look up the actual user ID
    actual_user_id = get_actual_user_id(user_id, db)
    if not actual_user_id:
        return []
    
    # Get all credentials for the user
    credentials = db.query(UserBillingCredential).filter(
        UserBillingCredential.user_id == actual_user_id,
        UserBillingCredential.is_deleted == False
    ).all()
    
    credential_ids = [cred.id for cred in credentials]
    
    # Get all billing results for these credentials
    results = db.query(BillingResult).filter(
        BillingResult.user_billing_credential_id.in_(credential_ids)
    ).order_by(BillingResult.run_time.desc()).all()
    
    # Create a map of credential_id to email for username lookup
    cred_to_email = {cred.id: cred.email for cred in credentials}
    
    return [
        BillingResultResponse(
            id=r.id,
            azure_blob_url=r.azure_blob_url,
            excel_blob_url=r.excel_blob_url,
            json_blob_url=r.json_blob_url,
            run_time=r.run_time.isoformat() if r.run_time else None,
            status=r.status,
            year=r.year,
            month=r.month,
            created_at=r.created_at.isoformat() if r.created_at else None,
            username=cred_to_email.get(r.user_billing_credential_id, "unknown")
        )
        for r in results
    ]

# Provider endpoints
@router.get("/api/providers", response_model=List[ProviderResponse])
def get_providers(db: Session = Depends(get_db)):
    """Get all available providers"""
    providers = db.query(Provider).all()
    return providers

@router.get("/api/providers/{provider_id}", response_model=ProviderResponse)
def get_provider(provider_id: str, db: Session = Depends(get_db)):
    """Get a specific provider by ID"""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider

@router.get("/api/audit-logs/download")
def download_audit_logs(
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Download all audit logs as CSV"""
    
    # Query all audit logs ordered by timestamp asc
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.asc()).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'id', 'entity_type', 'entity_id', 'entity_name', 
        'action', 'status', 'triggered_by', 'timestamp', 'message', 'details_json'
    ])
    
    # Write data
    for log in logs:
        writer.writerow([
            log.id,
            log.entity_type,
            log.entity_id or '',
            log.entity_name or '',
            log.action,
            log.status or '',
            log.triggered_by,
            log.timestamp.isoformat(),
            log.message or '',
            json.dumps(log.details) if log.details else ''
        ])
    
    # Prepare response
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )