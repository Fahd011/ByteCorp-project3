import uuid
from app.db import get_db
from app.agent_utils import simulate_agent_run
from app.models import AgentAction, UserBillingCredential, UserBillingCredentialResponse
from app.routes.auth import verify_token
from fastapi import Depends,UploadFile, File, Form, APIRouter, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from typing import List

import csv
import io
import os
from datetime import datetime
from azure_storage_service import azure_storage_service
from app.audit_logger import AuditLogger


router = APIRouter()

@router.post("/api/credentials/upload")
def upload_credentials(
    background_tasks: BackgroundTasks,
    csv_file: UploadFile = File(...),
    login_url: str = Form(...),
    billing_url: str = Form(...),
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # Check if user has existing credentials
    existing_creds = db.query(UserBillingCredential).filter(
        UserBillingCredential.user_id == user_id,
        UserBillingCredential.is_deleted == False
    ).all()
    # Check if any are running
    running_creds = [cred for cred in existing_creds if cred.last_state == "running"]
    if running_creds:
        raise HTTPException(status_code=400, detail="Cannot upload while agents are running")
    # Save CSV file to Azure storage
    content = csv_file.file.read()
    csv_filename = f"{uuid.uuid4()}_{csv_file.filename}"
    # Upload CSV to Azure storage
    success, csv_url, csv_blob_name = azure_storage_service.upload_manual_credential_pdf(
        content, user_id, "csv_upload", csv_filename
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload CSV file to Azure storage")
    # Parse CSV and create credentials
    try:
        csv_content = content.decode('utf-8')
        print(f"CSV Content (first 200 chars): {csv_content[:200]}")  # Debug log
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        print(f"CSV Headers detected: {csv_reader.fieldnames}")  # Debug log
        new_credentials = []
        updated_credentials = []
        row_count = 0
        for row in csv_reader:
            row_count += 1
            print(f"Row {row_count}: {dict(row)}")  # Debug log
            # Clean up the row data - remove extra spaces and quotes from all values
            cleaned_row = {}
            for key, value in row.items():
                if value:
                    cleaned_row[key.strip()] = value.strip().strip('"').strip()
                else:
                    cleaned_row[key.strip()] = ''
            print(f"Cleaned row: {cleaned_row}")  # Debug log
            # Handle multiple CSV formats - check for different column names
            email = (cleaned_row.get('cred_username', '') or
                    cleaned_row.get('cred_user', '') or
                    cleaned_row.get('email', '')).strip()
            password = (cleaned_row.get('cred_password', '') or
                       cleaned_row.get('password', '')).strip()
            print(f"Extracted email: '{email}', password: '{password}'")  # Debug log
            if email and password:
                # Check if credential already exists
                existing_credential = None
                for cred in existing_creds:
                    if cred.email == email:
                        existing_credential = cred
                        break
                
                if existing_credential:
                    # Update existing credential
                    existing_credential.password = password
                    existing_credential.billing_cycle_day = int(cleaned_row.get('billing_cycle_date', 10) or 10)
                    existing_credential.client_name = cleaned_row.get('client_name', '')
                    existing_credential.utility_co_id = str(cleaned_row.get('utility_co_id', ''))
                    existing_credential.utility_co_name = cleaned_row.get('utility_co_name', '')
                    existing_credential.cred_id = str(cleaned_row.get('cred_id', ''))
                    existing_credential.login_url = login_url
                    existing_credential.billing_url = billing_url
                    existing_credential.is_eligible_for_retry = False   # 👈 force set here
                    updated_credentials.append(existing_credential)
                    print(f":arrows_counterclockwise: Updated existing credential for: {email}")  # Debug log
                else:
                    # Create new credential
                    credential = UserBillingCredential(
                        user_id=user_id,
                        email=email,
                        password=password,
                        billing_cycle_day=int(cleaned_row.get('billing_cycle_date', 10) or 10),
                        client_name=cleaned_row.get('client_name', ''),
                        utility_co_id=str(cleaned_row.get('utility_co_id', '')),
                        utility_co_name=cleaned_row.get('utility_co_name', ''),
                        cred_id=str(cleaned_row.get('cred_id', '')),
                        login_url=login_url,
                        billing_url=billing_url,
                        is_eligible_for_retry=False   # 👈 force set here
                    )
                    new_credentials.append(credential)
                    print(f":white_check_mark: Added new credential #{len(new_credentials)} for: {email}")  # Debug log
            else:
                print(f":x: Skipped row {row_count} - missing email or password")  # Debug log
        print(f"Total rows processed: {row_count}")  # Debug log
        print(f"Total new credentials created: {len(new_credentials)}")  # Debug log
        print(f"Total existing credentials updated: {len(updated_credentials)}")  # Debug log
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")
    db.add_all(new_credentials)
    db.commit()
    
    # Log credential bulk upload
    credential_ids = [cred.id for cred in new_credentials]
    provider_name = f"{login_url.split('//')[-1].split('/')[0]}"  # Extract domain
    AuditLogger.log_credential_upload(
        credential_ids=credential_ids,
        provider_name=provider_name,
        count=len(new_credentials) + len(updated_credentials)
    )
    
    total_processed = len(new_credentials) + len(updated_credentials)
    return {
        "message": f"Processed {total_processed} credentials",
        "details": {
            "new_credentials": len(new_credentials),
            "updated_credentials": len(updated_credentials)
        }
    }


@router.post("/api/credentials/{cred_id}/upload_pdf")
def upload_pdf(
    cred_id: str,
    pdf_file: UploadFile = File(...),
    year: str = Form(...),
    month: str = Form(...),
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # Verify credential belongs to user
    credential = db.query(UserBillingCredential).filter(
        UserBillingCredential.id == cred_id,
        UserBillingCredential.user_id == user_id,
        UserBillingCredential.is_deleted == False
    ).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    # Read PDF file content
    content = pdf_file.file.read()
    # Upload PDF to Azure storage with custom year/month path
    success, blob_url, blob_name = azure_storage_service.upload_manual_credential_pdf_with_custom_path(
        content, user_id, cred_id, pdf_file.filename, year, month
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload PDF to Azure storage")
    # Create BillingResult entry for manual upload
    from app.models import BillingResult
    billing_result = BillingResult(
        user_billing_credential_id=cred_id,
        azure_blob_url=blob_name,
        run_time=datetime.utcnow(),
        status="manual_upload",
        year=year,
        month=month
    )
    db.add(billing_result)
    db.commit()
    return {"message": "PDF uploaded successfully", "file_url": blob_name, "azure_url": blob_url}

@router.get("/api/credentials/{cred_id}/download_pdf")
def download_pdf(
    cred_id: str,
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    credential = db.query(UserBillingCredential).filter(
        UserBillingCredential.id == cred_id,
        UserBillingCredential.user_id == user_id,
        UserBillingCredential.is_deleted == False
    ).first()
    
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    if not credential.uploaded_bill_url:
        raise HTTPException(status_code=404, detail="No PDF uploaded for this credential")
    
    # Check if file exists
    if not os.path.exists(credential.uploaded_bill_url):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    # Return file for download
    return FileResponse(
        path=credential.uploaded_bill_url,
        filename=f"bill_{credential.email}_{credential.cred_id}.pdf",
        media_type="application/pdf"
    )

@router.get("/api/credentials", response_model=List[UserBillingCredentialResponse])
def get_credentials(
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # Handle root user case: if user_id is an email, look up the actual user ID
    from app.models import User
    from config import config
    
    actual_user_id = user_id
    
    # Check if user_id is an email (root user case)
    if user_id == config.ROOT_USER_EMAIL:
        user = db.query(User).filter(User.email == user_id).first()
        if user:
            actual_user_id = user.id
        else:
            # If root user doesn't exist in DB, return empty list
            return []
    
    credentials = db.query(UserBillingCredential).filter(
        UserBillingCredential.user_id == actual_user_id,
        UserBillingCredential.is_deleted == False
    ).all()
    
    return credentials

@router.delete("/api/credentials/{cred_id}")
def delete_credential(
    cred_id: str,
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    credential = db.query(UserBillingCredential).filter(
        UserBillingCredential.id == cred_id,
        UserBillingCredential.user_id == user_id,
        UserBillingCredential.is_deleted == False
    ).first()
    
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    # Import BillingResult here
    from app.models import BillingResult
    
    # Set foreign key to NULL in related billing results
    db.query(BillingResult).filter(
        BillingResult.user_billing_credential_id == cred_id
    ).update({BillingResult.user_billing_credential_id: None})
    
    # Log credential deletion
    AuditLogger.log_credential_delete(
        credential_id=credential.id,
        email=credential.email
    )
    
    # Now delete the credential
    db.delete(credential)
    db.commit()
    
    return {"message": "Credential deleted"}

@router.post("/api/credentials/{cred_id}/agent")
def control_agent(
    cred_id: str,
    action: AgentAction,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    credential = db.query(UserBillingCredential).filter(
        UserBillingCredential.id == cred_id,
        UserBillingCredential.user_id == user_id,
        UserBillingCredential.is_deleted == False
    ).first()
    
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    if action.action == "RUN":
        if credential.last_state == "running":
            raise HTTPException(status_code=400, detail="Agent is already running")
        
        # Start background task using agent service
        background_tasks.add_task(simulate_agent_run, cred_id, db)
        
        # Log agent start
        AuditLogger.log_agent_control(
            action="start",
            credential_id=credential.id,
            details={"email": credential.email, "provider": credential.utility_co_name}
        )
        
        return {"message": "Agent started"}
    
    elif action.action == "STOPPED":
        credential.last_state = "idle"
        db.commit()
        
        # Log agent stop
        AuditLogger.log_agent_control(
            action="stop",
            credential_id=credential.id,
            details={"email": credential.email, "provider": credential.utility_co_name}
        )
        
        return {"message": "Agent stopped"}
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
