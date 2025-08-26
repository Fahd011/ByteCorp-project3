# BillingResult model for job results

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

# Removed ImportSessionResponse - no longer needed

class UserBillingCredentialResponse(BaseModel):
    id: str
    email: str
    client_name: Optional[str]
    utility_co_id: Optional[str]
    utility_co_name: Optional[str]
    cred_id: Optional[str]
    login_url: Optional[str]
    billing_url: Optional[str]
    billing_cycle_day: Optional[int]  # New field
    is_deleted: bool
    last_state: str
    last_error: Optional[str]
    last_run_time: Optional[datetime]
    uploaded_bill_url: Optional[str]
    created_at: datetime

# Removed ImportResultResponse - no longer needed

# SQLAlchemy models
class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Removed ImportSession - no longer needed

# Removed ImportResult - no longer needed

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

class BillingResult(Base):
    __tablename__ = 'billing_results'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_billing_credential_id = Column(String, ForeignKey('user_billing_credentials.id'), nullable=False)
    azure_blob_url = Column(String, nullable=False)
    run_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String, nullable=False)
    year = Column(String, nullable=False)
    month = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)