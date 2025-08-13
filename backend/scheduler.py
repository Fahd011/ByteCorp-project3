#!/usr/bin/env python3
"""
Scheduler module for handling APScheduler functionality.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger(__name__)

class JobScheduler:
    """Manages job scheduling using APScheduler"""
    
    def __init__(self, app=None):
        self.app = app
        self.scheduler = None
        self._initialized = False
        
    def init_app(self, app):
        """Initialize the scheduler with the Flask app"""
        self.app = app
        self._setup_scheduler()
        
    def _setup_scheduler(self):
        """Set up and start the APScheduler"""
        if self._initialized:
            return
            
        logger.info("🚀 Initializing APScheduler...")
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("✅ APScheduler started successfully!")
        logger.info(f"📅 Scheduler status: {self.scheduler.state}")
        
        # Log all scheduled jobs on startup
        self._log_scheduled_jobs()
        self._initialized = True
        
    def _log_scheduled_jobs(self):
        """Log all currently scheduled jobs"""
        if not self.scheduler:
            return
            
        jobs = self.scheduler.get_jobs()
        logger.info(f"📋 Current scheduled jobs: {len(jobs)}")
        for job in jobs:
            logger.info(f"   - Job ID: {job.id}, Next Run: {job.next_run_time}")
            
    def get_status(self):
        """Get the current status of the scheduler"""
        if not self.scheduler:
            return {'status': 'not_initialized', 'message': 'Scheduler not initialized'}
            
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
            
            return {
                'status': 'running',
                'scheduler_state': self.scheduler.state,
                'total_jobs': len(jobs),
                'jobs': jobs
            }
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {'status': 'error', 'message': str(e)}
            
    def calculate_next_run(self, schedule_type, schedule_config):
        """Calculate the next run time based on schedule configuration"""
        try:
            now = datetime.now()
            
            if schedule_type == 'weekly':
                # Get the target day of week (0=Sunday, 1=Monday, etc.)
                target_day = schedule_config.get('day_of_week', 1)
                target_hour = schedule_config.get('hour', 9)
                target_minute = schedule_config.get('minute', 0)
                
                # Calculate days until next target day
                current_day = now.weekday()  # Monday=0, Sunday=6
                if target_day == 0:  # Sunday
                    target_day = 6
                else:
                    target_day -= 1  # Convert to 0-based index
                    
                days_ahead = target_day - current_day
                if days_ahead <= 0:  # Target day has passed this week
                    days_ahead += 7
                    
                next_run = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
                next_run += timedelta(days=days_ahead)
                
                # If the calculated time is in the past, add a week
                if next_run <= now:
                    next_run += timedelta(days=7)
                    
                return next_run
                
            elif schedule_type == 'daily':
                target_hour = schedule_config.get('hour', 9)
                target_minute = schedule_config.get('minute', 0)
                
                next_run = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
                
                # If the calculated time is in the past, add a day
                if next_run <= now:
                    next_run += timedelta(days=1)
                    
                return next_run
                
            elif schedule_type == 'custom':
                # For custom cron, we'll let APScheduler handle the calculation
                # This is a simplified version - you might want to use a cron parser library
                return None
                
            return None
        except Exception as e:
            logger.error(f"Failed to calculate next run time: {e}")
            return None
            
    def schedule_job(self, job_id, schedule_config, run_function):
        """Schedule a job to run automatically"""
        if not self.scheduler:
            logger.error("❌ Scheduler not initialized")
            return False
            
        try:
            logger.info(f"📅 Scheduling job {job_id} with config: {schedule_config}")
            
            if schedule_config['schedule_type'] == 'weekly':
                trigger = CronTrigger(
                    day_of_week=schedule_config['schedule_config']['day_of_week'],
                    hour=schedule_config['schedule_config']['hour'],
                    minute=schedule_config['schedule_config']['minute']
                )
            elif schedule_config['schedule_type'] == 'daily':
                trigger = CronTrigger(
                    hour=schedule_config['schedule_config']['hour'],
                    minute=schedule_config['schedule_config']['minute']
                )
            elif schedule_config['schedule_type'] == 'custom':
                trigger = CronTrigger.from_crontab(
                    schedule_config['schedule_config']['cron_expression']
                )
            else:
                logger.error(f"❌ Unknown schedule type: {schedule_config['schedule_type']}")
                return False
                
            # Add the job to the scheduler
            self.scheduler.add_job(
                func=run_function,
                trigger=trigger,
                args=[job_id],
                id=f'scheduled_job_{job_id}',
                replace_existing=True
            )
            
            logger.info(f"✅ Successfully scheduled job {job_id}")
            logger.info(f"📋 Total scheduled jobs: {len(self.scheduler.get_jobs())}")
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to schedule job {job_id}: {e}")
            return False
            
    def remove_job(self, job_id):
        """Remove a scheduled job"""
        if not self.scheduler:
            return False
            
        try:
            job_id_str = f'scheduled_job_{job_id}'
            if self.scheduler.get_job(job_id_str):
                self.scheduler.remove_job(job_id_str)
                logger.info(f"✅ Removed scheduled job {job_id}")
                return True
            else:
                logger.info(f"ℹ️ No scheduled job found for {job_id}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to remove scheduled job {job_id}: {e}")
            return False
            
    def get_jobs(self):
        """Get all scheduled jobs"""
        if not self.scheduler:
            return []
        return self.scheduler.get_jobs()
        
    def shutdown(self):
        """Shutdown the scheduler gracefully"""
        if self.scheduler:
            logger.info("🛑 Shutting down APScheduler...")
            self.scheduler.shutdown()
            logger.info("✅ APScheduler shutdown complete")

# Create a global scheduler instance
scheduler = JobScheduler()
