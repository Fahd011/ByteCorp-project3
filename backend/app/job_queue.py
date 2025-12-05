import queue
import threading
import time
from typing import Dict, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import AgentJob as AgentJobModel, UserBillingCredential

class AgentJob:
    """In-memory representation of a job"""
    def __init__(self, job_model: AgentJobModel):
        self.job_id = job_model.id
        self.user_cred = job_model.user_cred
        self.signin_url = job_model.signin_url
        self.billing_history_url = job_model.billing_history_url
        self.provider_name = job_model.provider_name
        self.retry_count = job_model.retry_count
        self.max_retries = job_model.max_retries
        self.credential_id = job_model.credential_id
        self.job_model = job_model  # Keep reference to DB model

class JobQueueManager:
    """Manages the queue of agent jobs with database persistence"""
    
    def __init__(self, max_concurrent_sessions: int = 15):
        self.job_queue = queue.Queue()
        self.active_sessions = {}  # {job_id: session_id}
        self.max_concurrent_sessions = max_concurrent_sessions
        self.lock = threading.Lock()
        self.worker_thread = None
        self.running = False
        
    def start_worker(self):
        """Start the worker thread and restore pending jobs from database"""
        if self.worker_thread and self.worker_thread.is_alive():
            return
            
        # Restore pending jobs from database
        self._restore_pending_jobs()
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        print("[QUEUE] Worker thread started")
        
    def _restore_pending_jobs(self):
        """Restore pending jobs from database on startup"""
        db: Session = SessionLocal()
        try:
            pending_jobs = db.query(AgentJobModel).filter(
                AgentJobModel.status.in_(["pending", "retrying"])
            ).all()
            
            # Also restore jobs that were running (server crashed)
            running_jobs = db.query(AgentJobModel).filter(
                AgentJobModel.status == "running"
            ).all()
            
            restored_count = 0
            for job_model in pending_jobs + running_jobs:
                # Reset status if it was running (server crashed)
                if job_model.status == "running":
                    job_model.status = "pending"
                    job_model.started_at = None
                    job_model.session_id = None
                    db.commit()
                
                job = AgentJob(job_model)
                self.job_queue.put(job)
                restored_count += 1
            
            print(f"[QUEUE] Restored {restored_count} pending jobs from database")
            
        except Exception as e:
            print(f"[QUEUE ERROR] Failed to restore pending jobs: {e}")
        finally:
            db.close()
        
    def add_job(self, user_cred: Dict, signin_url: str, billing_history_url: str, 
                 provider_name: str, credential_id: Optional[str] = None) -> str:
        """Add a job to the queue and database"""
        db: Session = SessionLocal()
        try:
            # Create job in database
            job_model = AgentJobModel(
                credential_id=credential_id,
                user_cred=user_cred,
                signin_url=signin_url,
                billing_history_url=billing_history_url,
                provider_name=provider_name,
                status="pending"
            )
            db.add(job_model)
            db.commit()
            db.refresh(job_model)
            
            # Create in-memory job
            job = AgentJob(job_model)
            self.job_queue.put(job)
            
            print(f"[QUEUE] Job {job.job_id} added to queue. Queue size: {self.job_queue.qsize()}")
            return job.job_id
            
        except Exception as e:
            db.rollback()
            print(f"[QUEUE ERROR] Failed to add job to database: {e}")
            raise
        finally:
            db.close()
    
    def _update_job_status(self, job_id: str, status: str, error_message: Optional[str] = None, 
                         session_id: Optional[str] = None):
        """Update job status in database"""
        db: Session = SessionLocal()
        try:
            job_model = db.query(AgentJobModel).filter(AgentJobModel.id == job_id).first()
            if job_model:
                job_model.status = status
                job_model.error_message = error_message
                job_model.session_id = session_id
                
                if status == "running" and not job_model.started_at:
                    job_model.started_at = datetime.now(timezone.utc)
                elif status in ["completed", "failed"]:
                    job_model.completed_at = datetime.now(timezone.utc)
                
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"[QUEUE ERROR] Failed to update job status: {e}")
        finally:
            db.close()
        
    def stop_worker(self):
        """Stop the worker thread"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        print("[QUEUE] Worker thread stopped")
        
    def _worker_loop(self):
        """Main worker loop that processes jobs from the queue"""
        while self.running:
            try:
                # STEP 1: Check Capacity BEFORE touching the queue
                with self.lock:
                    active_count = len(self.active_sessions)
                
                # If we are full, just sleep and wait. 
                # Do NOT pull a job yet. This preserves FIFO order.
                if active_count >= self.max_concurrent_sessions:
                    time.sleep(1) 
                    continue

                # STEP 2: Get the job
                try:
                    # We know we have space (mostly), so try to get a job
                    job = self.job_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # STEP 3: Reserve the slot safely
                with self.lock:
                    # RACE CONDITION SAFETY:
                    # Even though we checked in Step 1, another thread (unlikely here, but good practice)
                    # or a rapid state change could have filled the slots.
                    if len(self.active_sessions) >= self.max_concurrent_sessions:
                        print(f"[QUEUE] Edge case: Max sessions reached while fetching. Re-queuing job {job.job_id}")
                        self.job_queue.put(job) # Put it back at the front (approx)
                        time.sleep(1)
                        continue
                    
                    # Reserve the slot immediately so other loops see it as taken
                    self.active_sessions[job.job_id] = None
                    print(f"[QUEUE] Reserved slot for job {job.job_id}. Active sessions: {len(self.active_sessions)}/{self.max_concurrent_sessions}")

                # STEP 4: Spawn the thread
                thread = threading.Thread(
                    target=self._execute_job,
                    args=(job,),
                    daemon=True
                )
                thread.start()
                
            except Exception as e:
                print(f"[QUEUE ERROR] Error in worker loop: {e}")
                time.sleep(1)
    
    def _execute_job(self, job: AgentJob):
        """Execute a single job"""
        job_id = job.job_id
        print(f"[QUEUE] Starting job {job_id} (retry {job.retry_count}/{job.max_retries})")
        
        try:
            # Update status to running
            self._update_job_status(job_id, "running")
            
            # Import here to avoid circular imports
            from app.agent import run_agent_task
            
            # Note: Session slot is already reserved in worker_loop, so we don't need to add it here
            
            # Run the agent task
            run_agent_task(
                job.user_cred,
                job.signin_url,
                job.billing_history_url,
                job.provider_name
            )
            
            # Job completed successfully
            with self.lock:
                if job_id in self.active_sessions:
                    del self.active_sessions[job_id]
            
            self._update_job_status(job_id, "completed")
            print(f"[QUEUE] Job {job_id} completed successfully")
            
        except Exception as e:
            error_msg = str(e)
            print(f"[QUEUE] Job {job_id} failed: {error_msg}")
            
            # Check if it's a 429 error
            is_429_error = ("429" in error_msg or 
                          "Too many concurrent" in error_msg or 
                          "Too Many Requests" in error_msg)
            
            with self.lock:
                if job_id in self.active_sessions:
                    del self.active_sessions[job_id]
            
            # Re-queue if it's a 429 error and we haven't exceeded max retries
            if is_429_error and job.retry_count < job.max_retries:
                job.retry_count += 1
                job.job_model.retry_count = job.retry_count
                job.job_model.status = "retrying"
                job.job_model.error_message = error_msg
                
                # Update in database
                db: Session = SessionLocal()
                try:
                    db.merge(job.job_model)
                    db.commit()
                except Exception as db_err:
                    db.rollback()
                    print(f"[QUEUE ERROR] Failed to update retry count: {db_err}")
                finally:
                    db.close()
                
                print(f"[QUEUE] Re-queuing job {job_id} due to 429 error (retry {job.retry_count}/{job.max_retries})")
                time.sleep(5)
                self.job_queue.put(job)
            else:
                # Mark as failed in database
                self._update_job_status(job_id, "failed", error_message=error_msg)
                print(f"[QUEUE] Job {job_id} failed permanently: {error_msg}")
    
    def get_queue_size(self) -> int:
        """Get the current queue size"""
        return self.job_queue.qsize()
    
    def get_active_sessions_count(self) -> int:
        """Get the number of active sessions"""
        with self.lock:
            return len(self.active_sessions)
    
    def get_status(self) -> Dict:
        """Get queue status"""
        db: Session = SessionLocal()
        try:
            pending_count = db.query(AgentJobModel).filter(
                AgentJobModel.status.in_(["pending", "retrying"])
            ).count()
            running_count = db.query(AgentJobModel).filter(
                AgentJobModel.status == "running"
            ).count()
        finally:
            db.close()
            
        with self.lock:
            return {
                "queue_size": self.job_queue.qsize(),
                "active_sessions": len(self.active_sessions),
                "max_concurrent_sessions": self.max_concurrent_sessions,
                "worker_running": self.running,
                "pending_in_db": pending_count,
                "running_in_db": running_count
            }

# Global queue manager instance
job_queue_manager = JobQueueManager(max_concurrent_sessions=5)

