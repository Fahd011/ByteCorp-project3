import uuid

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from browser_use.llm import ChatOpenAI

from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.models import User, UserBillingCredential  # ✅ safe now
from app.routes.auth import router as auth_bp, verify_token
from app.utils import hash_password, verify_password
from app.routes.additionals import router as additionals_bp
from app.routes.credentials import router as credentials_bp
from app.db import SessionLocal, get_db, engine, Base
from app.routes.agent import router as agents_bp

from config import config

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize LLM
llm = ChatOpenAI(model="gpt-4.1-mini")

# FastAPI app

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    # Optionally: scheduler.shutdown() or other cleanup

app = FastAPI(title="Sagility Backend", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth_bp)
app.include_router(additionals_bp)
app.include_router(credentials_bp)
app.include_router(agents_bp)

# Add explicit OPTIONS handler for CORS preflight
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    return {"message": "OK"}

# API Endpoints

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

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

# Create default user if it doesn't exist
def create_default_user():
    """Create a default user if it doesn't exist in the database"""
    print("🔍 Starting default user creation check...")
    try:
        db = SessionLocal()
        print("✅ Database session created successfully")
        
        # Check if default user already exists
        default_email = config.ROOT_USER_EMAIL
        print(f"🔍 Checking if user with email '{default_email}' exists...")
        existing_user = db.query(User).filter(User.email == default_email).first()
        
        if not existing_user:
            print("❌ User not found, creating new user...")
            # Create default user
            default_password = config.ROOT_USER_PASSWORD
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
        
        print(f"Daily job found {len(credentials)} credentials to process")
        
        for credential in credentials:
            # Use agent service to run the agent
            result = await agent_service.run_agent(credential, db)
            print(f"Daily job result for {credential.email}: {result}")
            
    except Exception as e:
        print(f"Error in daily job: {e}")
    finally:
        db.close()


# --- Schedules ---


# Scheduler (AsyncIO version)
scheduler = AsyncIOScheduler()

# Start scheduler in FastAPI startup event

# ⏰ For production: run daily at 10 AM
scheduler.add_job(
    daily_agent_job,
    CronTrigger(hour=10, minute=0),
    id="daily_agent_job",
    replace_existing=True,
)

# # ⏳ For testing: run every 30 seconds
# scheduler.add_job(
#     daily_agent_job,
#     IntervalTrigger(seconds=5),
#     id="daily_agent_job_test",
#     replace_existing=True,
# )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
