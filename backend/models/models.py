from db.db import db
import uuid
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ImportSession(db.Model):
    __tablename__ = 'import_sessions'
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String, db.ForeignKey('users.id'))
    csv_url = db.Column(db.String, nullable=False)
    login_url = db.Column(db.String, nullable=False)
    billing_url = db.Column(db.String, nullable=False)
    status = db.Column(db.String, default="idle")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # New scheduling fields
    is_scheduled = db.Column(db.Boolean, default=False)
    schedule_type = db.Column(db.String)  # 'weekly', 'daily', 'monthly', 'custom'
    schedule_config = db.Column(db.JSON)  # Store schedule configuration as JSON
    next_run = db.Column(db.DateTime)  # Next scheduled run time
    last_scheduled_run = db.Column(db.DateTime)  # Last scheduled run time

class ImportResult(db.Model):
    __tablename__ = 'import_results'
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String, db.ForeignKey('import_sessions.id'))
    email = db.Column(db.String)
    status = db.Column(db.String)
    error = db.Column(db.String)
    file_url = db.Column(db.String)
    retry_attempts = db.Column(db.Integer, default=0)  # New field to track retry attempts
    final_error = db.Column(db.String)  # New field for final error after all retries
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
