from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from browser_use.llm import ChatOpenAI

from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.models import UserBillingCredential  # ✅ safe now
from app.routes.auth import router as auth_bp, verify_token
from app.routes.additionals import router as additionals_bp
from app.routes.credentials import router as credentials_bp
from app.db import SessionLocal, get_db
from app.routes.agent import router as agents_bp

from config import config


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
            UserBillingCredential.is_deleted == False
            # UserBillingCredential.last_state.in_(["idle", "completed", "error"])
        ).all()
        
        print(f"Daily job found {len(credentials)} credentials to process")
        
        for credential in credentials:
            # Use agent service to run the agent
            print(f"EMAIL {credential.email}")
            print(f"PASS {credential.password}")
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

# # ⏰ For production: run daily at 10 AM
scheduler.add_job(
    daily_agent_job,
    CronTrigger(hour=18, minute=20),
    # CronTrigger(hour=23, minute=8),
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
