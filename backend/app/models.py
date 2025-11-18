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

# Provider Models
class ProviderCreate(BaseModel):
    name: str
    login_url: str
    billing_url: str
    extras: Optional[dict] = None

class ProviderResponse(BaseModel):
    id: str
    name: str
    login_url: str
    billing_url: str
    extras: Optional[dict]
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
    is_active: bool
    is_deleted: bool
    last_state: str
    last_error: Optional[str]
    is_eligible_for_retry: bool
    last_run_time: Optional[datetime]
    uploaded_bill_url: Optional[str]
    created_at: datetime

class ManualBillResponse(BaseModel):
    id: str
    original_filename: Optional[str]
    provider_name: Optional[str]
    azure_blob_url: str
    excel_blob_url: Optional[str]
    json_blob_url: Optional[str]
    status: str
    year: str
    month: str
    run_time: Optional[datetime]
    created_at: datetime

class AuditLogResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: Optional[str]
    entity_name: Optional[str]
    action: str
    status: Optional[str]
    triggered_by: str
    timestamp: datetime
    details: Optional[dict]
    message: Optional[str]

# Removed ImportResultResponse - no longer needed

# SQLAlchemy models
class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Provider Table
class Provider(Base):
    __tablename__ = 'providers'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    login_url = Column(String, nullable=False)
    billing_url = Column(String, nullable=False)
    extras = Column(JSON, nullable=True)  # Store additional configuration as JSON
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
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False)
    last_state = Column(String, default="idle")  # idle, running, completed, error
    last_error = Column(String)
    is_eligible_for_retry = Column(Boolean, default=False, nullable=True)
    last_run_time = Column(DateTime)
    uploaded_bill_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class BillingResult(Base):
    __tablename__ = 'billing_results'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_billing_credential_id = Column(String, ForeignKey('user_billing_credentials.id'), nullable=True)
    azure_blob_url = Column(String, nullable=False)
    excel_blob_url = Column(String, nullable=True)   # Excel file
    json_blob_url = Column(String, nullable=True)    # JSON data file
    original_filename = Column(String, nullable=True)  # For manual uploads
    provider_name = Column(String, nullable=True)      # For manual uploads
    run_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String, nullable=False)
    year = Column(String, nullable=False)
    month = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # What was affected
    entity_type = Column(String, nullable=False)  # "credential", "billing_result", "provider", "manual_bill"
    entity_id = Column(String, nullable=True)     # ID of the affected entity
    entity_name = Column(String, nullable=True)   # Human-readable name (e.g., provider name, filename)
    
    # What happened
    action = Column(String, nullable=False)       # "create", "update", "delete", "extract_start", "extract_complete"
    status = Column(String, nullable=True)        # "success", "failure", "pending"
    
    # Who/what did it
    triggered_by = Column(String, nullable=False) # "user" or "agent"
    
    # When
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Additional context
    details = Column(JSON, nullable=True)         # Store metadata (provider, errors, file paths, etc.)
    message = Column(String, nullable=True)       # Human-readable message