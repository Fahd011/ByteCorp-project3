"""Audit logging utility for tracking important actions in the system."""

from app.db import SessionLocal
from app.models import AuditLog
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class AuditLogger:
    """Helper class for creating audit log entries."""
    
    @staticmethod
    def log(
        entity_type: str,
        action: str,
        triggered_by: str,
        entity_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        status: Optional[str] = "success",
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create an audit log entry.
        
        Args:
            entity_type: Type of entity (credential, billing_result, provider, manual_bill)
            action: Action performed (create, update, delete, extract_start, extract_complete, etc.)
            triggered_by: "user" for manual actions, "agent" for automated actions
            entity_id: ID of the affected entity
            entity_name: Human-readable name (provider name, filename, email, etc.)
            status: Status of the action (success, failure, pending)
            details: Additional context as dictionary
            
        Returns:
            ID of the created audit log entry, or None if logging failed
        """
        db = SessionLocal()
        try:
            audit_entry = AuditLog(
                id=str(uuid.uuid4()),
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                action=action,
                status=status,
                triggered_by=triggered_by,
                timestamp=datetime.utcnow(),
                details=details
            )
            
            db.add(audit_entry)
            db.commit()
            
            # Emoji for better console visibility
            emoji = "👤" if triggered_by == "user" else "🤖"
            status_emoji = "✅" if status == "success" else "❌" if status == "failure" else "⏳"
            print(f"📝 {emoji} Audit: {entity_type}.{action} - {status_emoji} {status}")
            
            return audit_entry.id
            
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to create audit log: {e}")
            # Don't raise - audit logging shouldn't break the main flow
            return None
        finally:
            db.close()
    
    # Convenience methods for common patterns
    
    @staticmethod
    def user_action(
        entity_type: str,
        action: str,
        entity_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Log a user-initiated action.
        
        Args:
            entity_type: Type of entity being acted upon
            action: Action performed
            entity_id: ID of the affected entity
            entity_name: Human-readable name
            details: Additional context
            
        Returns:
            ID of the created audit log entry
        """
        return AuditLogger.log(
            entity_type=entity_type,
            action=action,
            triggered_by="user",
            entity_id=entity_id,
            entity_name=entity_name,
            status="success",
            details=details
        )
    
    @staticmethod
    def agent_action(
        entity_type: str,
        action: str,
        entity_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Log an agent-initiated action.
        
        Args:
            entity_type: Type of entity being acted upon
            action: Action performed
            entity_id: ID of the affected entity
            entity_name: Human-readable name
            status: Status of the action (success, failure, pending)
            details: Additional context
            
        Returns:
            ID of the created audit log entry
        """
        return AuditLogger.log(
            entity_type=entity_type,
            action=action,
            triggered_by="agent",
            entity_id=entity_id,
            entity_name=entity_name,
            status=status,
            details=details
        )
    
    # Domain-specific convenience methods
    
    @staticmethod
    def log_credential_upload(
        credential_ids: list,
        provider_name: str,
        count: int
    ) -> Optional[str]:
        """Log bulk credential upload."""
        return AuditLogger.user_action(
            entity_type="credential",
            action="bulk_upload",
            details={
                "provider": provider_name,
                "count": count,
                "credential_ids": credential_ids
            }
        )
    
    @staticmethod
    def log_credential_delete(
        credential_id: str,
        email: str
    ) -> Optional[str]:
        """Log credential deletion."""
        return AuditLogger.user_action(
            entity_type="credential",
            action="delete",
            entity_id=credential_id,
            entity_name=email
        )
    
    @staticmethod
    def log_manual_bill_upload(
        billing_result_id: str,
        filename: str,
        provider_name: str,
        month: str,
        year: str
    ) -> Optional[str]:
        """Log manual bill upload."""
        return AuditLogger.user_action(
            entity_type="manual_bill",
            action="upload",
            entity_id=billing_result_id,
            entity_name=filename,
            details={
                "provider": provider_name,
                "month": month,
                "year": year
            }
        )
    
    @staticmethod
    def log_extraction_start(
        billing_result_id: str,
        provider_name: str,
        email: str
    ) -> Optional[str]:
        """Log the start of automated extraction."""
        return AuditLogger.agent_action(
            entity_type="billing_result",
            action="extract_start",
            entity_id=billing_result_id,
            entity_name=f"{provider_name} - {email}",
            status="pending",
            details={
                "provider": provider_name,
                "email": email
            }
        )
    
    @staticmethod
    def log_extraction_complete(
        billing_result_id: str,
        provider_name: str,
        email: str,
        success: bool,
        excel_url: Optional[str] = None,
        json_url: Optional[str] = None,
        error: Optional[str] = None
    ) -> Optional[str]:
        """Log the completion of automated extraction."""
        details = {"provider": provider_name, "email": email}
        
        if success:
            details["excel_url"] = excel_url
            details["json_url"] = json_url
        else:
            details["error"] = error
        
        return AuditLogger.agent_action(
            entity_type="billing_result",
            action="extract_complete",
            entity_id=billing_result_id,
            entity_name=f"{provider_name} - {email}",
            status="success" if success else "failure",
            details=details
        )
    
    @staticmethod
    def log_provider_action(
        action: str,
        provider_id: str,
        provider_name: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Log provider creation, update, or deletion."""
        return AuditLogger.user_action(
            entity_type="provider",
            action=action,
            entity_id=provider_id,
            entity_name=provider_name,
            details=details
        )
    
    @staticmethod
    def log_agent_control(
        action: str,
        credential_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Log agent start/stop actions."""
        return AuditLogger.user_action(
            entity_type="agent",
            action=action,
            entity_id=credential_id,
            details=details
        )

