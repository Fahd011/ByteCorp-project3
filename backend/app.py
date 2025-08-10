from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from db import db
from config import Config
from routes.auth_routes import bp as auth_bp
from routes.job_routes import bp as jobs_bp
from agent_runner import cleanup_orphaned_processes, running_processes
import signal
import sys

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000'])  # Enable CORS for frontend
db.init_app(app)
jwt = JWTManager(app)

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(jobs_bp, url_prefix='/api')

def cleanup_on_exit(signum, frame):
    """Clean up all running processes on exit"""
    print("Shutting down, cleaning up processes...")
    from agent_runner import stop_agent_job
    # Stop all running jobs
    for session_id in list(running_processes.keys()):
        stop_agent_job(session_id)
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, cleanup_on_exit)
signal.signal(signal.SIGTERM, cleanup_on_exit)

# Clean up orphaned processes on startup
cleanup_orphaned_processes()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)     # use_reloader=False to prevent agent from restarting the server when job is run
