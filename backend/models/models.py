from db import db
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
