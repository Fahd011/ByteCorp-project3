import uuid
from app.db import get_db
from app.agent_utils import simulate_agent_run
from app.models import AgentAction, ImportSession, UserBillingCredential, UserBillingCredentialResponse
from app.routes.auth import verify_token
from fastapi import Depends,UploadFile, File, Form, APIRouter, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from typing import List

import csv
import io
import os


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
    
    # Save CSV file
    csv_filename = f"uploads/{uuid.uuid4()}_{csv_file.filename}"
    with open(csv_filename, "wb") as buffer:
        content = csv_file.file.read()
        buffer.write(content)
    
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
    
    # Create import session
    import_session = ImportSession(
        user_id=user_id,
        csv_url=csv_filename,
        login_url=login_url,
        billing_url=billing_url
    )
    db.add(import_session)
    db.commit()
    
    return {"message": f"Uploaded {len(new_credentials)} credentials", "session_id": import_session.id}

@router.post("/api/credentials/{cred_id}/upload_pdf")
def upload_pdf(
    cred_id: str,
    pdf_file: UploadFile = File(...),
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
    
    # Save PDF file
    pdf_filename = f"uploads/{uuid.uuid4()}_{pdf_file.filename}"
    with open(pdf_filename, "wb") as buffer:
        content = pdf_file.file.read()
        buffer.write(content)
    
    # Update credential
    credential.uploaded_bill_url = pdf_filename
    db.commit()
    
    return {"message": "PDF uploaded successfully", "file_url": pdf_filename}

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
