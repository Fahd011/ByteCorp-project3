from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from db.db import db
from config import Config
from routes.auth_routes import bp as auth_bp
from routes.job_routes import bp as jobs_bp
from agent_runner import cleanup_orphaned_processes, running_processes
from scheduler import scheduler
from scheduled_jobs import run_scheduled_job
import signal
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000'])  # Enable CORS for frontend
db.init_app(app)
jwt = JWTManager(app)

# Initialize scheduler with the app
scheduler.init_app(app)

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(jobs_bp, url_prefix='/api')

# Add scheduler status endpoint
@app.route('/api/scheduler/status', methods=['GET'])
def scheduler_status():
    """Get the current status of the scheduler"""
    try:
        status_data = scheduler.get_status()
        if status_data.get('status') == 'error':
            return status_data, 500
        return status_data
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return {'status': 'error', 'message': str(e)}, 500

def cleanup_on_exit(signum, frame):
    """Clean up all running processes on exit"""
    print("Shutting down, cleaning up processes...")
    from agent_runner import stop_agent_job
    # Stop all running jobs
    for session_id in list(running_processes.keys()):
        stop_agent_job(session_id)
    
    # Shutdown scheduler
    scheduler.shutdown()
    
    sys.exit(0)

# Only set up signal handlers if we're in the main thread
try:
    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup_on_exit)
    signal.signal(signal.SIGTERM, cleanup_on_exit)
    print("[INFO] Signal handlers configured for graceful shutdown")
except (ValueError, OSError) as e:
    print(f"[WARN] Could not set up signal handlers (running in background thread): {e}")
    print("[INFO] Continuing without signal handlers")

# Clean up orphaned processes on startup
cleanup_orphaned_processes()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
