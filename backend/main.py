from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, ForeignKey, JSON, text, inspect
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from typing import List, Optional
import uuid
import jwt
import bcrypt
import os
import csv
import io
from pydantic import BaseModel, EmailStr
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
import threading
import time

# Import configuration first
from config import config

# FastAPI app
app = FastAPI(title="Sagility Backend", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
SECRET_KEY = config.SECRET_KEY
ALGORITHM = config.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = config.ACCESS_TOKEN_EXPIRE_MINUTES

# Database setup
DATABASE_URL = config.DATABASE_URL
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Create uploads directory
os.makedirs("./uploads", exist_ok=True)

# Scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Security scheme
security = HTTPBearer()

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class CredentialUpload(BaseModel):
    login_url: str
    billing_url: str

class AgentAction(BaseModel):
    action: str  # "RUN" or "STOPPED"

class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime

class ImportSessionResponse(BaseModel):
    id: str
    csv_url: str
    login_url: str
    billing_url: str
    status: str
    created_at: datetime
    is_scheduled: bool
    schedule_type: Optional[str]
    next_run: Optional[datetime]

class UserBillingCredentialResponse(BaseModel):
    id: str
    email: str
    client_name: Optional[str]
    utility_co_id: Optional[str]
    utility_co_name: Optional[str]
    cred_id: Optional[str]
    login_url: Optional[str]
    billing_url: Optional[str]
    is_deleted: bool
    last_state: str
    last_error: Optional[str]
    last_run_time: Optional[datetime]
    uploaded_bill_url: Optional[str]
    created_at: datetime

class ImportResultResponse(BaseModel):
    id: str
    session_id: str
    email: str
    status: str
    error: Optional[str]
    file_url: Optional[str]
    retry_attempts: int
    final_error: Optional[str]
    created_at: datetime

# SQLAlchemy models
class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ImportSession(Base):
    __tablename__ = 'import_sessions'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'))
    csv_url = Column(String, nullable=False)
    login_url = Column(String, nullable=False)
    billing_url = Column(String, nullable=False)
    status = Column(String, default="idle")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_scheduled = Column(Boolean, default=False)
    schedule_type = Column(String)  # 'weekly', 'daily', 'monthly', 'custom'
    schedule_config = Column(JSON)
    next_run = Column(DateTime)
    last_scheduled_run = Column(DateTime)

class ImportResult(Base):
    __tablename__ = 'import_results'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey('import_sessions.id'))
    email = Column(String)
    status = Column(String)
    error = Column(String)
    file_url = Column(String)
    retry_attempts = Column(Integer, default=0)
    final_error = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserBillingCredential(Base):
    __tablename__ = 'user_billing_credentials'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'))
    email = Column(String, nullable=False)
    password = Column(String, nullable=False)
    client_name = Column(String)
    utility_co_id = Column(String)
    utility_co_name = Column(String)
    cred_id = Column(String)
    login_url = Column(String)  # Store login URL for each credential
    billing_url = Column(String)  # Store billing URL for each credential
    is_deleted = Column(Boolean, default=False)
    last_state = Column(String, default="idle")  # idle, running, completed, error
    last_error = Column(String)
    last_run_time = Column(DateTime)
    uploaded_bill_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Add missing columns if they don't exist (database migration)
def add_missing_columns():
    try:
        with engine.connect() as conn:
            # Check if columns exist and add them if they don't
            inspector = inspect(engine)
            existing_columns = [col['name'] for col in inspector.get_columns('user_billing_credentials')]
            
            if 'client_name' not in existing_columns:
                conn.execute(text("ALTER TABLE user_billing_credentials ADD COLUMN client_name VARCHAR"))
            if 'utility_co_id' not in existing_columns:
                conn.execute(text("ALTER TABLE user_billing_credentials ADD COLUMN utility_co_id VARCHAR"))
            if 'utility_co_name' not in existing_columns:
                conn.execute(text("ALTER TABLE user_billing_credentials ADD COLUMN utility_co_name VARCHAR"))
            if 'cred_id' not in existing_columns:
                conn.execute(text("ALTER TABLE user_billing_credentials ADD COLUMN cred_id VARCHAR"))
            if 'login_url' not in existing_columns:
                conn.execute(text("ALTER TABLE user_billing_credentials ADD COLUMN login_url VARCHAR"))
            if 'billing_url' not in existing_columns:
                conn.execute(text("ALTER TABLE user_billing_credentials ADD COLUMN billing_url VARCHAR"))
            
            conn.commit()
            print("Database migration completed successfully")
    except Exception as e:
        print(f"Migration error (this is normal if columns already exist): {e}")

# Run migration
add_missing_columns()

# Import agent service after models are defined
from agent_service import agent_service

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# JWT functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Password hashing
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except (ValueError, TypeError):
        # Handle invalid hash format
        return False

# Background task for agent simulation
async def simulate_agent_run(credential_id: str, db: Session):
    """Run agent for a specific credential"""
    credential = db.query(UserBillingCredential).filter(UserBillingCredential.id == credential_id).first()
    if credential:
        # Use agent service to run the agent
        result = await agent_service.run_agent(credential, db)
        print(f"Agent result for {credential.email}: {result}")

# Scheduler job
async def daily_agent_job():
    """Daily job to run agents for idle credentials"""
    db = SessionLocal()
    try:
        credentials = db.query(UserBillingCredential).filter(
            UserBillingCredential.is_deleted == False,
            UserBillingCredential.last_state.in_(["idle", "completed", "error"])
        ).all()
        
        for credential in credentials:
            # Use agent service to run the agent
            result = await agent_service.run_agent(credential, db)
            print(f"Daily job result for {credential.email}: {result}")
            
    except Exception as e:
        print(f"Error in daily job: {e}")
    finally:
        db.close()

# Schedule daily job at 12 AM
scheduler.add_job(
    daily_agent_job,
    CronTrigger(hour=0, minute=0),
    id='daily_agent_job',
    replace_existing=True
)

# API Endpoints

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/auth/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create new user with hashed password
    hashed_password = hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate access token
    access_token = create_access_token(data={"sub": new_user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_credentials.email).first()
    
    if not user or not verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/credentials/upload")
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

@app.post("/credentials/{cred_id}/upload_pdf")
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

@app.get("/credentials/{cred_id}/download_pdf")
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

@app.get("/credentials", response_model=List[UserBillingCredentialResponse])
def get_credentials(
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    credentials = db.query(UserBillingCredential).filter(
        UserBillingCredential.user_id == user_id,
        UserBillingCredential.is_deleted == False
    ).all()
    
    return credentials

@app.delete("/credentials/{cred_id}")
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

@app.post("/credentials/{cred_id}/agent")
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

@app.post("/schedule/weekly")
def schedule_weekly(
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    credentials = db.query(UserBillingCredential).filter(
        UserBillingCredential.user_id == user_id,
        UserBillingCredential.is_deleted == False
    ).all()
    
    for credential in credentials:
        credential.is_scheduled = True
        credential.schedule_type = "weekly"
        credential.next_run = datetime.utcnow() + timedelta(weeks=1)
    
    db.commit()
    
    return {"message": f"Scheduled {len(credentials)} credentials for weekly runs"}

# Additional utility endpoints

@app.get("/sessions", response_model=List[ImportSessionResponse])
def get_sessions(
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    sessions = db.query(ImportSession).filter(
        ImportSession.user_id == user_id
    ).all()
    
    return sessions

@app.get("/results/{session_id}", response_model=List[ImportResultResponse])
def get_results(
    session_id: str,
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # Verify session belongs to user
    session = db.query(ImportSession).filter(
        ImportSession.id == session_id,
        ImportSession.user_id == user_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    results = db.query(ImportResult).filter(
        ImportResult.session_id == session_id
    ).all()
    
    return results

# Utility endpoint to create a test user (for development only)
@app.post("/create-test-user")
def create_test_user(db: Session = Depends(get_db)):
    """Create a test user for development purposes"""
    test_email = "test@example.com"
    test_password = "password123"
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == test_email).first()
    if existing_user:
        return {"message": "Test user already exists", "email": test_email}
    
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
        "message": "Test user created successfully",
        "email": test_email,
        "password": test_password,
        "user_id": new_user.id
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
