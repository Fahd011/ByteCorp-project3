"""
Configuration file for Sagility Backend
This file contains all configuration settings that can be easily modified
"""

import os
from typing import Optional

class Config:
    """Application configuration"""
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/browserpy")
    
    # Security Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Storage Configuration
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")  # "local", "azure", "aws"
    
    # Azure Storage Configuration (for future use)
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    AZURE_STORAGE_CONTAINER: str = os.getenv("AZURE_STORAGE_CONTAINER", "sagility-files")
    
    # AWS S3 Configuration (for future use)
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET", "sagility-files")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    
    # Agent Configuration
    AGENT_TYPE: str = os.getenv("AGENT_TYPE", "simulation")  # "simulation", "selenium", "playwright"
    AGENT_TIMEOUT: int = int(os.getenv("AGENT_TIMEOUT", "300"))  # 5 minutes
    
    # Scheduler Configuration
    SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    DAILY_JOB_HOUR: int = int(os.getenv("DAILY_JOB_HOUR", "0"))  # 12 AM
    DAILY_JOB_MINUTE: int = int(os.getenv("DAILY_JOB_MINUTE", "0"))
    
    # File Upload Configuration
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    ALLOWED_FILE_TYPES: list = ["csv", "pdf"]
    
    # CORS Configuration
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001"
    ]
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def get_storage_config(cls) -> dict:
        """Get storage configuration based on provider"""
        if cls.STORAGE_PROVIDER == "azure":
            return {
                "connection_string": cls.AZURE_STORAGE_CONNECTION_STRING,
                "container": cls.AZURE_STORAGE_CONTAINER
            }
        elif cls.STORAGE_PROVIDER == "aws":
            return {
                "access_key_id": cls.AWS_ACCESS_KEY_ID,
                "secret_access_key": cls.AWS_SECRET_ACCESS_KEY,
                "bucket": cls.AWS_S3_BUCKET,
                "region": cls.AWS_REGION
            }
        else:
            return {"local_path": "./uploads"}
    
    @classmethod
    def validate_config(cls) -> list:
        """Validate configuration and return list of errors"""
        errors = []
        
        if cls.STORAGE_PROVIDER == "azure" and not cls.AZURE_STORAGE_CONNECTION_STRING:
            errors.append("AZURE_STORAGE_CONNECTION_STRING is required when using Azure storage")
        
        if cls.STORAGE_PROVIDER == "aws" and not cls.AWS_ACCESS_KEY_ID:
            errors.append("AWS_ACCESS_KEY_ID is required when using AWS storage")
        
        if cls.STORAGE_PROVIDER == "aws" and not cls.AWS_SECRET_ACCESS_KEY:
            errors.append("AWS_SECRET_ACCESS_KEY is required when using AWS storage")
        
        return errors

# Global config instance
config = Config()
