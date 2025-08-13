#!/usr/bin/env python3
"""
Scheduled job execution logic.
This handles the actual running of scheduled jobs.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def run_scheduled_job(job_id, app):
    """Function that runs when a scheduled job is triggered"""
    try:
        logger.info(f"🚀 Running scheduled job {job_id}")
        
        # Import here to avoid circular imports
        from models.models import ImportSession
        from db import db
        
        # Run within Flask application context
        with app.app_context():
            try:
                # Get the session
                session = ImportSession.query.get(job_id)
                if not session:
                    logger.error(f"❌ Scheduled job {job_id}: Session not found")
                    return
                    
                # Check if job is already running
                if session.status == 'running':
                    logger.info(f"⏸️ Scheduled job {job_id}: Already running, skipping")
                    return
                    
                # Update last scheduled run time
                session.last_scheduled_run = datetime.now()
                db.session.commit()
                
                # Start the agent directly in this context to avoid circular imports
                logger.info(f"▶️ Starting agent for scheduled job {job_id}")
                
                # Import and run the agent function directly
                from agent_runner import run_agent_for_job
                run_agent_for_job(job_id)
                
                logger.info(f"✅ Scheduled job {job_id} started successfully")
                
            except Exception as inner_e:
                logger.error(f"❌ Inner error in scheduled job {job_id}: {inner_e}")
                logger.error(f"❌ Error type: {type(inner_e).__name__}")
                import traceback
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                raise
        
    except Exception as e:
        logger.error(f"❌ Failed to run scheduled job {job_id}: {e}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
