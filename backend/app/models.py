from app.db import Base
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, JSON
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

import uuid


# Pydantic models

# Data models
class AgentRequest(BaseModel):
    user_creds: List[dict]  # Changed from dict to List[dict]
    signin_url: str
    billing_history_url: str

class AgentResult(BaseModel):
    pdf_content: bytes
    user_creds: dict
    timestamp: str

class ErrorResult(BaseModel):
    error_message: str
    user_creds: dict
    timestamp: str
    traceback: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class CredentialUpload(BaseModel):
    login_url: str
    billing_url: str

class AgentAction(BaseModel):
    action: str  # "RUN" or "STOPPED"

class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime

class ImportSessionResponse(BaseModel):
    id: str
    csv_url: str
    login_url: str
    billing_url: str
    status: str
    created_at: datetime
    is_scheduled: bool
    schedule_type: Optional[str]
    next_run: Optional[datetime]

class UserBillingCredentialResponse(BaseModel):
    id: str
    email: str
    client_name: Optional[str]
    utility_co_id: Optional[str]
    utility_co_name: Optional[str]
    cred_id: Optional[str]
    login_url: Optional[str]
    billing_url: Optional[str]
    is_deleted: bool
    last_state: str
    last_error: Optional[str]
    last_run_time: Optional[datetime]
    uploaded_bill_url: Optional[str]
    created_at: datetime

class ImportResultResponse(BaseModel):
    id: str
    session_id: str
    email: str
    status: str
    error: Optional[str]
    file_url: Optional[str]
    retry_attempts: int
    final_error: Optional[str]
    created_at: datetime

# SQLAlchemy models
class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ImportSession(Base):
    __tablename__ = 'import_sessions'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'))
    csv_url = Column(String, nullable=False)
    login_url = Column(String, nullable=False)
    billing_url = Column(String, nullable=False)
    status = Column(String, default="idle")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_scheduled = Column(Boolean, default=False)
    schedule_type = Column(String)  # 'weekly', 'daily', 'monthly', 'custom'
    schedule_config = Column(JSON)
    next_run = Column(DateTime)
    last_scheduled_run = Column(DateTime)

class ImportResult(Base):
    __tablename__ = 'import_results'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey('import_sessions.id'))
    email = Column(String)
    status = Column(String)
    error = Column(String)
    file_url = Column(String)
    retry_attempts = Column(Integer, default=0)
    final_error = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserBillingCredential(Base):
    __tablename__ = 'user_billing_credentials'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'))
    email = Column(String, nullable=False)
    password = Column(String, nullable=False)
    client_name = Column(String)
    utility_co_id = Column(String)
    utility_co_name = Column(String)
    cred_id = Column(String)
    login_url = Column(String)  # Store login URL for each credential
    billing_url = Column(String)  # Store billing URL for each credential
    billing_cycle_day = Column(Integer, nullable=True)  # 👈 new field
    is_deleted = Column(Boolean, default=False)
    last_state = Column(String, default="idle")  # idle, running, completed, error
    last_error = Column(String)
    last_run_time = Column(DateTime)
    uploaded_bill_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
