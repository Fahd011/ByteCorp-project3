import uuid
from app.db import get_db
from app.agent_utils import simulate_agent_run
from app.models import AgentAction, UserBillingCredential, UserBillingCredentialResponse
from app.routes.auth import verify_token
from fastapi import Depends,UploadFile, File, Form, APIRouter, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from typing import List

import csv
import io
import os
from datetime import datetime
from azure_storage_service import azure_storage_service


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
    
    # Create a set of existing emails for duplicate checking
    existing_emails = {cred.email for cred in existing_creds}
    
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
                if email in existing_emails:
                    print(f"⚠️ Skipped duplicate credential for: {email}")  # Debug log
                else:
                    credential = UserBillingCredential(
                        user_id=user_id,
                        email=email,
                        password=password,
                        billing_cycle_day=int(cleaned_row.get('billing_cycle_date', 10) or 10),  # 👈 convert to int
                        client_name=cleaned_row.get('client_name', ''),
                        utility_co_id=str(cleaned_row.get('utility_co_id', '')),
                        utility_co_name=cleaned_row.get('utility_co_name', ''),
                        cred_id=str(cleaned_row.get('cred_id', '')),
                        login_url=login_url,
                        billing_url=billing_url
                    )
                    new_credentials.append(credential)
                    existing_emails.add(email)  # Add to set to prevent duplicates within same upload
                    print(f"✅ Added credential #{len(new_credentials)} for: {email}")  # Debug log
            else:
                print(f"❌ Skipped row {row_count} - missing email or password")  # Debug log
        
        print(f"Total rows processed: {row_count}")  # Debug log
        print(f"Total credentials created: {len(new_credentials)}")  # Debug log
        
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")
    
    db.add_all(new_credentials)
    db.commit()
    
    return {"message": f"Uploaded {len(new_credentials)} credentials"}

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
    
    # Download PDF from Azure storage
    success, pdf_content = azure_storage_service.download_manual_credential_pdf(credential.uploaded_bill_url)
    
    if not success:
        raise HTTPException(status_code=404, detail="PDF file not found in Azure storage")
    
    # Return PDF as streaming response
    return StreamingResponse(
        io.BytesIO(pdf_content),
        media_type='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="bill_{credential.email}_{credential.cred_id}.pdf"'
        }
    )

@router.get("/api/credentials", response_model=List[UserBillingCredentialResponse])
def get_credentials(
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    credentials = db.query(UserBillingCredential).filter(
        UserBillingCredential.user_id == user_id,
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
    
    credential.is_deleted = True
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
        
        return {"message": "Agent started"}
    
    elif action.action == "STOPPED":
        credential.last_state = "idle"
        db.commit()
        return {"message": "Agent stopped"}
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
