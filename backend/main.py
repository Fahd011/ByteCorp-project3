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
import multiprocessing
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
import requests
from pathlib import Path
import asyncio
import uuid
from browser_use.llm import ChatOpenAI
from browser_use import Agent
from browser_use.browser import BrowserSession, BrowserProfile
from dotenv import load_dotenv


# Import configuration first
from config import config

# FastAPI app
app = FastAPI(title="Sagility Backend", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add explicit OPTIONS handler for CORS preflight
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    return {"message": "OK"}

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

# Data models
class AgentRequest(BaseModel):
    user_creds: List[dict]  # Changed from dict to List[dict]
    signin_url: str
    billing_history_url: str

class AgentResult(BaseModel):
    pdf_content: bytes
    user_creds: dict
    timestamp: str

class ErrorResult(BaseModel):
    error_message: str
    user_creds: dict
    timestamp: str
    traceback: str

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

# Password hashing functions (moved here before user creation)
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except (ValueError, TypeError):
        # Handle invalid hash format
        return False

# Create default user if it doesn't exist
def create_default_user():
    """Create a default user if it doesn't exist in the database"""
    print("🔍 Starting default user creation check...")
    try:
        db = SessionLocal()
        print("✅ Database session created successfully")
        
        # Check if default user already exists
        default_email = "sagiliti@yopmail.com"
        print(f"🔍 Checking if user with email '{default_email}' exists...")
        existing_user = db.query(User).filter(User.email == default_email).first()
        
        if not existing_user:
            print("❌ User not found, creating new user...")
            # Create default user
            default_password = "D3x4YR*8{Rx)Tj>"
            hashed_password = hash_password(default_password)
            print(f"🔐 Password hashed successfully")
            
            new_user = User(
                id=str(uuid.uuid4()),
                email=default_email,
                password_hash=hashed_password
            )
            
            db.add(new_user)
            db.commit()
            print("✅ User added to database successfully")
            
            print("=" * 60)
            print("🎉 DEFAULT USER CREATED SUCCESSFULLY!")
            print("=" * 60)
            print(f"📧 Email: {default_email}")
            print(f"🔑 Password: {default_password}")
            print("=" * 60)
            print("💡 You can now login with these credentials")
            print("=" * 60)
            
        else:
            print(f"✅ User '{default_email}' already exists in database")
            
        db.close()
        print("✅ Database session closed")
        
    except Exception as e:
        print(f"❌ Error creating default user: {e}")
        import traceback
        traceback.print_exc()

# Create default user
create_default_user()

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
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

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
agent_status = {"running": False, "process": None, "stop_requested": False}

# Create bills directory if it doesn't exist
BILLS_DIR = Path("bills")
BILLS_DIR.mkdir(exist_ok=True)

# Initialize LLM
llm = ChatOpenAI(model="gpt-4.1-mini")

def check_and_update_agent_status():
    """
    Check if the agent process is still alive and update status accordingly
    """
    if agent_status["running"] and agent_status["process"]:
        if not agent_status["process"].is_alive():
            print("Agent process has completed, updating status...")
            agent_status["running"] = False
            agent_status["process"] = None
            agent_status["stop_requested"] = False

def run_agent_task(user_creds: List[dict], signin_url: str, billing_history_url: str):
    """
    Agent runner function that executes the web scraping task for multiple users
    """
    total_users = len(user_creds)
    completed_users = 0
    initial_files = set(os.listdir(BILLS_DIR))
    print(f"Starting agent for {total_users} users")
    
    for user_index, user_cred in enumerate(user_creds, 1):
        print(f"\n=== Processing user {user_index}/{total_users}: {user_cred.get('username', 'unknown')} ===")
        
        max_attempts = 5
        current_attempt = 1
        
        while current_attempt <= max_attempts:
            try:
                print(f"Agent attempt {current_attempt}/{max_attempts} for user: {user_cred.get('username', 'unknown')}")
                
                # Check if stop was requested
                if agent_status.get("stop_requested", False):
                    print(f"Agent stop requested for user: {user_cred.get('username', 'unknown')}")
                    return
                
                # Create unique profile path for this session
                unique_profile_path = f'/tmp/browser_profiles/{uuid.uuid4()}'
                os.makedirs(unique_profile_path, exist_ok=True)
                
                # Create browser session with bills folder as downloads path
                browser_session = BrowserSession(
                    browser_profile=BrowserProfile(
                        downloads_path=str(BILLS_DIR),  # Downloads go directly to bills folder
                        user_data_dir=unique_profile_path,
                        headless=False,  # Show browser window
                        viewport={"width": 1920, "height": 1080},  # Full screen size
                        window_size={"width": 1920, "height": 1080},  # Browser window size
                        wait_for_network_idle_page_load_time=5.0,  # Increased wait time for slow pages
                        wait_between_actions=2.0,  # Wait 2 seconds between actions
                    )
                )
                
                task = f"""
                    1. Go to {signin_url}
        2. Wait for the page to fully load (be patient, this website is slow)
        3. Sign in using email: {user_cred.get('username')} and password: {user_cred.get('password')}
        4. Wait for login to complete and dashboard to load completely
        5. Navigate to {billing_history_url}
        6. IMPORTANT: Wait patiently for the billing history page to load completely
        7. Check the page content:
           - If you see "Oops, something went wrong." message, IMMEDIATELY close the browser session and stop
           - If you see other error messages, refresh the page and wait again
           - Keep waiting until you see "Billing & Payment Activity" text on the page
        8. Once the billing history table is visible, find the first row in the billing table
        9. Click ONLY on the "View Bill" button in the FIRST row of the table
        10. Wait for the bill to download to {BILLS_DIR}
        11. Once download is complete, close the browser session
        
        Important notes:
        - Be very patient with page loading times
        - If you see "Oops, something went wrong." - STOP and close the session immediately
        - Only click the View Bill button for the first/top item in the billing table
        - Do not interact with any other buttons or rows
        - If pages are slow, wait longer rather than giving up
    """
                
                # Create the agent with the actual task
                agent = Agent(
                    task=task,
                    llm=llm,
                    browser_session=browser_session,
                    args=["--start-maximized"],
                )
                
                # Check stop again before running
                if agent_status.get("stop_requested", False):
                    print(f"Agent stop requested before running for user: {user_cred.get('username', 'unknown')}")
                    return
                
                # Run the agent
                print(f"Starting browser automation for user: {user_cred.get('username', 'unknown')} (Attempt {current_attempt})")
                
                # Run the async agent in the current thread
                result = asyncio.run(agent.run())
                
                # Check if stop was requested during execution
                if agent_status.get("stop_requested", False):
                    print(f"Agent stop requested during execution for user: {user_cred.get('username', 'unknown')}")
                    return
                
                print(f"Agent completed successfully for user: {user_cred.get('username', 'unknown')} on attempt {current_attempt}")
                print(f"Result: {result.final_result()}")
                
                # Check if bills were actually downloaded
                bill_files = list(BILLS_DIR.glob("*.pdf")) + list(BILLS_DIR.glob("*.PDF"))
                if not bill_files:
                    print(f"❌ No bills downloaded for user: {user_cred.get('username', 'unknown')} on attempt {current_attempt}")
                    print("Task failed - no bills found, will retry...")
                    
                    # Clean up the profile directory before retry
                    try:
                        import shutil
                        shutil.rmtree(unique_profile_path)
                        print(f"Cleaned up profile directory: {unique_profile_path}")
                    except Exception as cleanup_error:
                        print(f"Warning: Could not clean up profile directory: {cleanup_error}")
                    
                    # Continue to next attempt instead of breaking
                    current_attempt += 1
                    if current_attempt <= max_attempts:
                        wait_time = min(2 ** current_attempt, 30)  # Max 30 seconds wait
                        print(f"Waiting {wait_time} seconds before retry...")
                        import time
                        time.sleep(wait_time)
                        continue  # Go to next attempt
                    else:
                        # All attempts failed due to no bills downloaded
                        print(f"All {max_attempts} attempts failed for user: {user_cred.get('username', 'unknown')} - no bills downloaded")
                        
                        # Store final error
                        error_data = {
                            "error_message": f"Failed after {max_attempts} attempts - no bills were downloaded",
                            "user_creds": user_cred,
                            "timestamp": datetime.now().isoformat(),
                            "traceback": "No bills downloaded after multiple attempts",
                            "attempts_made": max_attempts,
                            "status": "failed_no_bills"
                        }
                        
                        store_error_result_locally(error_data)
                        
                        # Automatically call the error API
                        try:
                            response = requests.post(
                                "http://localhost:8000/api/agent/error",
                                json={
                                    "error_message": f"Failed after {max_attempts} attempts - no bills were downloaded",
                                    "user_creds": user_cred,
                                    "timestamp": datetime.now().isoformat(),
                                    "traceback": "No bills downloaded after multiple attempts"
                                }
                            )
                            print(f"✅ Error API called automatically: {response.status_code}")
                        except Exception as api_error:
                            print(f"⚠️ Failed to call error API automatically: {api_error}")
                        
                        break  # Move to next user
                
                # Bills were downloaded successfully!
                print(f"✅ Bills found: {len(bill_files)} files downloaded for user: {user_cred.get('username', 'unknown')}")
                # Detect new files
                new_files = set(os.listdir(BILLS_DIR)) - initial_files
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                username = user_cred.get('username', 'unknown')
                for filename in new_files:
                    if filename.lower().endswith(".pdf"):
                        old_path = os.path.join(BILLS_DIR, filename)
                        clean_email = email.replace('@', '_').replace('+', '_').replace('.', '_')
                        new_filename = f"{clean_email}_{timestamp}.pdf"
                        new_path = os.path.join(BILLS_DIR, new_filename)
                        try:
                            os.rename(old_path, new_path)
                            print(f"[{email}] File renamed to: {new_filename}")
                        except Exception as e:
                            print(f"[{email}] Error renaming file: {e}")
                    else:
                        print(f"[{email}] Downloaded non-PDF: {filename}")
                # Print success message as requested
                
                print(f"✅ Bills for {username} at {timestamp} have been received and ready for upload")
                
                # Automatically call the results API when agent completes successfully
                try:
                    response = requests.post(
                        "http://localhost:8000/api/agent/results",
                        json={
                            "pdf_content": "",  # Empty for now since we're not capturing PDF content
                            "user_creds": user_cred,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    print(f"✅ Results API called automatically: {response.status_code}")
                except Exception as api_error:
                    print(f"⚠️ Failed to call results API automatically: {api_error}")
                
                # Clean up the profile directory
                try:
                    import shutil
                    shutil.rmtree(unique_profile_path)
                    print(f"Cleaned up profile directory: {unique_profile_path}")
                except Exception as cleanup_error:
                    print(f"Warning: Could not clean up profile directory: {cleanup_error}")
                
                # Success! Exit the retry loop for this user
                completed_users += 1
                print(f"✅ User {user_cred.get('username', 'unknown')} completed successfully ({completed_users}/{total_users})")
                break
                
            except Exception as e:
                print(f"Agent attempt {current_attempt} failed for user: {user_cred.get('username', 'unknown')} with error: {str(e)}")
                
                # Clean up the profile directory on error
                try:
                    if 'unique_profile_path' in locals():
                        import shutil
                        shutil.rmtree(unique_profile_path)
                        print(f"Cleaned up profile directory after error: {unique_profile_path}")
                except Exception as cleanup_error:
                    print(f"Warning: Could not clean up profile directory after error: {cleanup_error}")
                
                # If this was the last attempt, store the final error
                if current_attempt == max_attempts:
                    print(f"All {max_attempts} attempts failed for user: {user_cred.get('username', 'unknown')}")
                    
                    # Handle errors and store error information
                    error_data = {
                        "error_message": f"Failed after {max_attempts} attempts. Last error: {str(e)}",
                        "user_creds": user_cred,
                        "timestamp": datetime.now().isoformat(),
                        "traceback": traceback.format_exc(),
                        "attempts_made": max_attempts,
                        "status": "failed"
                    }
                    
                    store_error_result_locally(error_data)
                    
                    # Automatically call the error API when agent fails
                    try:
                        response = requests.post(
                            "http://localhost:8000/api/agent/error",
                            json={
                                "error_message": f"Failed after {max_attempts} attempts. Last error: {str(e)}",
                                "user_creds": user_cred,
                                "timestamp": datetime.now().isoformat(),
                                "traceback": traceback.format_exc()
                            }
                        )
                        print(f"✅ Error API called automatically: {response.status_code}")
                    except Exception as api_error:
                        print(f"⚠️ Failed to call error API automatically: {api_error}")
                else:
                    # Wait a bit before retrying (exponential backoff)
                    wait_time = min(2 ** current_attempt, 30)  # Max 30 seconds wait
                    print(f"Waiting {wait_time} seconds before retry...")
                    import time
                    time.sleep(wait_time)
                
                current_attempt += 1
        
        # Check if stop was requested between users
        if agent_status.get("stop_requested", False):
            print(f"Agent stop requested between users")
            return
    
    print(f"\n=== All users completed! Total: {completed_users}/{total_users} successful ===")
    
    # Update status when done (moved outside the while loop)
    agent_status["running"] = False
    agent_status["process"] = None
    agent_status["stop_requested"] = False


def store_error_result_locally(error_data: dict):
    """
    Store error results locally
    """
    try:
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        username = error_data["user_creds"].get("username", "unknown")
        filename = f"error_{username}_{timestamp}.json"
        
        # Save to bills directory
        filepath = BILLS_DIR / filename
        with open(filepath, 'w') as f:
            json.dump(error_data, f, indent=2)
        
        print(f"❌ Error for {username} at {timestamp} has been saved")
        print(f"📁 Error file saved to: {filepath}")
        
    except Exception as e:
        print(f"Error storing error result: {str(e)}")


# API Endpoints

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/agent/run")
async def run_agent(request: AgentRequest, background_tasks: BackgroundTasks):
    """
    POST API to run the agent for multiple users
    """
    if agent_status["running"]:
        raise HTTPException(status_code=400, detail="Agent is already running")
    
    try:
        # Start agent in background process with the full user_creds array
        process = multiprocessing.Process(
            target=run_agent_task,
            args=(request.user_creds, request.signin_url, request.billing_history_url)
        )
        process.start()
        
        # Update status
        agent_status["running"] = True
        agent_status["process"] = process
        
        return {
            "message": f"Agent started successfully for {len(request.user_creds)} users",
            "status": "running",
            "total_users": len(request.user_creds),
            "users": [creds.get("username", "unknown") for creds in request.user_creds],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start agent: {str(e)}")

@app.post("/api/agent/stop")
async def stop_agent():
    """
    POST API to stop the agent with force kill of all browser processes
    """
    if not agent_status["running"]:
        raise HTTPException(status_code=400, detail="Agent is not running")
    
    try:
        # Set stop flag
        agent_status["stop_requested"] = True
        
        # Try to terminate the process
        if agent_status["process"] and agent_status["process"].is_alive():
            print("Attempting to terminate agent process...")
            agent_status["process"].terminate()
            
            # Wait a bit for graceful termination
            agent_status["process"].join(timeout=10)
            
            # Force kill if still alive
            if agent_status["process"].is_alive():
                print("Force killing agent process...")
                agent_status["process"].kill()
                agent_status["process"].join(timeout=5)
        
        # Force kill all browser processes (this is the key part)
        try:
            import subprocess
            import platform
            import psutil
            
            print("Force killing all browser processes...")
            
            if platform.system() == "Windows":
                # Kill Chrome/Chromium processes on Windows
                subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], capture_output=True)
                subprocess.run(["taskkill", "/f", "/im", "chromium.exe"], capture_output=True)
                subprocess.run(["taskkill", "/f", "/im", "msedge.exe"], capture_output=True)
                
                # Also kill any remaining browser processes
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        proc_name = proc.info['name'].lower()
                        if any(browser in proc_name for browser in ['chrome', 'chromium', 'edge', 'firefox']):
                            print(f"Killing browser process: {proc.info['name']} (PID: {proc.info['pid']})")
                            proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                        
            else:
                # Kill Chrome/Chromium processes on Unix-like systems
                subprocess.run(["pkill", "-f", "chrome"], capture_output=True)
                subprocess.run(["pkill", "-f", "chromium"], capture_output=True)
                subprocess.run(["pkill", "-f", "firefox"], capture_output=True)
                
                # Also kill any remaining browser processes
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        proc_name = proc.info['name'].lower()
                        if any(browser in proc_name for browser in ['chrome', 'chromium', 'firefox']):
                            print(f"Killing browser process: {proc.info['name']} (PID: {proc.info['pid']})")
                            proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
            print("Force killed all browser processes")
            
        except Exception as kill_error:
            print(f"Warning: Could not force kill browser processes: {kill_error}")
        
        # Reset status
        agent_status["running"] = False
        agent_status["process"] = None
        
        return {
            "message": "Agent stopped and all browser processes terminated",
            "status": "stopped",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        # Reset status even on error
        agent_status["running"] = False
        agent_status["process"] = None
        agent_status["stop_requested"] = False
        raise HTTPException(status_code=500, detail=f"Failed to stop agent: {str(e)}")

@app.post("/api/agent/results")
async def store_agent_results(result: AgentResult):
    """
    POST API to store agent results
    """
    try:
        # Store the result locally
        result_data = {
            "pdf_content": result.pdf_content,
            "user_creds": result.user_creds,
            "timestamp": result.timestamp
        }
        
        # For now, we'll just print a message
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"✅ Bills for {result.user_creds.get('username', 'unknown')} at {timestamp} have been received and ready for upload")
        
        return {
            "message": "Agent results received (not stored locally)",
            "user": result.user_creds.get("username", "unknown"),
            "timestamp": result.timestamp
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store results: {str(e)}")

@app.post("/api/agent/error")
async def store_agent_error(error: ErrorResult):
    """
    POST API to store agent errors
    """
    try:
        # Store the error locally
        error_data = {
            "error_message": error.error_message,
            "user_creds": error.user_creds,
            "timestamp": error.timestamp,
            "traceback": error.traceback
        }
        
        store_error_result_locally(error_data)
        
        return {
            "message": "Agent error stored successfully",
            "user": error.user_creds.get("username", "unknown"),
            "timestamp": error.timestamp
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store error: {str(e)}")

@app.get("/api/agent/health")
async def health_check():
    """
    Health test API to check if FastAPI is responsive
    """
    # Check and update agent status
    check_and_update_agent_status()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agent_status": agent_status["running"],
        "message": "FastAPI is running and responsive"
    }

@app.get("/api/agent/status")
async def get_agent_status():
    """
    GET API to check detailed agent status
    """
    # Check and update agent status
    check_and_update_agent_status()
    
    return {
        "running": agent_status["running"],
        "stop_requested": agent_status["stop_requested"],
        "timestamp": datetime.now().isoformat()
    }

@app.post("api/auth/register", response_model=Token)
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

@app.post("/api/auth/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    print(f"🔍 Login attempt for email: {user_credentials.email}")
    
    user = db.query(User).filter(User.email == user_credentials.email).first()
    
    if not user:
        print(f"❌ User not found for email: {user_credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"✅ User found: {user.email}")
    print(f"🔍 Verifying password...")
    
    if not verify_password(user_credentials.password, user.password_hash):
        print(f"❌ Password verification failed for user: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"✅ Password verified successfully for user: {user.email}")
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/credentials/upload")
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

@app.post("/api/credentials/{cred_id}/upload_pdf")
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

@app.get("/api/credentials/{cred_id}/download_pdf")
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

@app.get("/api/credentials", response_model=List[UserBillingCredentialResponse])
def get_credentials(
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    credentials = db.query(UserBillingCredential).filter(
        UserBillingCredential.user_id == user_id,
        UserBillingCredential.is_deleted == False
    ).all()
    
    return credentials

@app.delete("/api/credentials/{cred_id}")
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

@app.post("/api/credentials/{cred_id}/agent")
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

@app.post("/api/schedule/weekly")
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

@app.get("/api/sessions", response_model=List[ImportSessionResponse])
def get_sessions(
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    sessions = db.query(ImportSession).filter(
        ImportSession.user_id == user_id
    ).all()
    
    return sessions

@app.get("/api/results/{session_id}", response_model=List[ImportResultResponse])
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
@app.post("/api/create-test-user")
def create_test_user(db: Session = Depends(get_db)):
    """Create a test user for development purposes"""
    test_email = "sagiliti@yopmail.com"
    test_password = "D3x4YR*8{Rx)Tj>"
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
