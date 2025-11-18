from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
# from browser_use.llm import ChatOpenAI

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
from app.routes.pdf_extraction import router as pdf_extraction_bp
from app.routes.manual_bills import router as manual_bills_bp

from config import config

# Import agent service after models are defined
from agent_service import agent_service
from app.audit_logger import AuditLogger


# # Initialize LLM
# llm = ChatOpenAI(model="gpt-4.1-mini")

# FastAPI app

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    # Optionally: scheduler.shutdown() or other cleanup
    scheduler.shutdown(wait=False)

app = FastAPI(title="Sagiliti Backend", version="1.0.0", lifespan=lifespan)

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
app.include_router(pdf_extraction_bp)
app.include_router(manual_bills_bp)

# Add explicit OPTIONS handler for CORS preflight
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    return {"message": "OK"}

# API Endpoints

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

# --- Schedules ---

# Scheduler (AsyncIO version)
scheduler = AsyncIOScheduler()

# --- Jobs ---
    
async def daily_agent_job():
    """Daily job to run agents for idle credentials"""
    print("Daily job started")
    
    # Log scheduled job start
    AuditLogger.user_action(
        entity_type="scheduled_job",
        action="daily_job_start",
        entity_name="Daily Agent Job",
        details={"schedule": "daily at 19:07", "type": "automated"}
    )
    
    db = SessionLocal()
    processed_count = 0
    success_count = 0
    error_count = 0
    
    try:
        credentials = db.query(UserBillingCredential).filter(
            UserBillingCredential.is_deleted == False,
            UserBillingCredential.is_active == True
            # UserBillingCredential.last_state.in_(["idle", "completed", "error"])
        ).all()
        
        print(f"Daily job found {len(credentials)} credentials to process")
        
        for credential in credentials:
            if credential.last_run_time:
                current_month = datetime.now().month
                if credential.last_run_time.month == current_month:
                    print(f"Credential {credential.id} has already been run this month")
            
            try:
                result = await agent_service.run_agent(credential, db)
                processed_count += 1
                success_count += 1
            except Exception as cred_error:
                print(f"Error processing credential {credential.id}: {cred_error}")
                processed_count += 1
                error_count += 1
        
        # Log scheduled job completion (success)
        AuditLogger.user_action(
            entity_type="scheduled_job",
            action="daily_job_complete",
            entity_name="Daily Agent Job",
            details={
                "schedule": "daily at 19:07",
                "total_credentials": len(credentials),
                "processed": processed_count,
                "success": success_count,
                "errors": error_count
            }
        )
            
    except Exception as e:
        print(f"Error in daily job: {e}")
        # Log scheduled job completion (failure)
        AuditLogger.agent_action(
            entity_type="scheduled_job",
            action="daily_job_complete",
            entity_name="Daily Agent Job",
            status="failure",
            details={
                "schedule": "daily at 19:07",
                "error": str(e)
            }
        )
    finally:
        db.close()
        
async def retry_agent_job():
    """Retry job to run agents for eligible credentials"""
    
    # Log scheduled job start
    AuditLogger.agent_action(
        entity_type="scheduled_job",
        action="retry_job_start",
        entity_name="Retry Agent Job",
        status="pending",
        details={"schedule": "every 10 minutes", "type": "automated"}
    )
    
    db = SessionLocal()
    processed_count = 0
    success_count = 0
    error_count = 0
    
    try:
        credentials = db.query(UserBillingCredential).filter(
            UserBillingCredential.is_eligible_for_retry == True,
            UserBillingCredential.is_active == True
            # UserBillingCredential.last_state.in_(["idle", "completed", "error"])
        ).all()
        
        print(f"Retry job found {len(credentials)} credentials to process")
        
        for credential in credentials:
            # Use agent service to run the agent
            try:
                result = await agent_service.run_agent(credential, db)
                processed_count += 1
                success_count += 1
            except Exception as cred_error:
                print(f"Error processing credential {credential.id}: {cred_error}")
                processed_count += 1
                error_count += 1
        
        # Log scheduled job completion (success)
        AuditLogger.agent_action(
            entity_type="scheduled_job",
            action="retry_job_complete",
            entity_name="Retry Agent Job",
            status="success",
            details={
                "schedule": "every 10 minutes",
                "total_eligible": len(credentials),
                "processed": processed_count,
                "success": success_count,
                "errors": error_count
            }
        )
            
    except Exception as e:
        print(f"Error in retry job: {e}")
        # Log scheduled job completion (failure)
        AuditLogger.agent_action(
            entity_type="scheduled_job",
            action="retry_job_complete",
            entity_name="Retry Agent Job",
            status="failure",
            details={
                "schedule": "every 10 minutes",
                "error": str(e)
            }
        )
    finally:
        db.close()

# --- Add jobs ---

# 🔹 Run every 5 minutes (for testing)
scheduler.add_job(
    retry_agent_job,
    IntervalTrigger(minutes=10),
    id="retry_agent_job",
    replace_existing=True,
)

# 🔹 Cron job
scheduler.add_job(
    daily_agent_job,         
    CronTrigger(hour=14, minute=30),
    id="daily_agent_job",    
    replace_existing=True        
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)