"""Audit logging utility for tracking important actions in the system."""

from app.db import get_db_context
from app.models import AuditLog
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


def format_audit_log_message(
    entity_type: str,
    entity_name: Optional[str],
    entity_id: Optional[str],
    action: str,
    status: Optional[str],
    triggered_by: str,
    details: Optional[Dict[str, Any]],
    timestamp: datetime
) -> str:
    """Convert audit log data to human-readable message"""
    details = details or {}
    entity = entity_name or entity_id or "Unknown"
    
    # Format timestamp as readable string
    time_str = timestamp.strftime("%Y-%m-%d %I:%M:%S %p UTC")
    
    # Manual bill logs
    if entity_type == "manual_bill":
        if action == "upload":
            return f"User uploaded manual bill '{entity}' for {details.get('provider', 'Unknown')} ({details.get('month', '')} {details.get('year', '')}) at {time_str}"
        elif action == "extract_start":
            return f"Agent started extracting '{entity}' for {details.get('provider', 'Unknown')} at {time_str}"
        elif action == "extract_complete":
            if status == "success":
                return f"Agent successfully extracted '{entity}' for {details.get('provider', 'Unknown')} at {time_str}"
            else:
                return f"Agent failed to extract '{entity}' for {details.get('provider', 'Unknown')} at {time_str}: {details.get('error', 'Unknown error')}"
    
    # Billing result (automated extraction)
    elif entity_type == "billing_result":
        if action == "extract_start":
            return f"Agent started extraction for {details.get('provider', 'Unknown')} - {details.get('email', 'Unknown')} at {time_str}"
        elif action == "extract_complete":
            if status == "success":
                return f"Agent completed extraction for {details.get('provider', 'Unknown')} - {details.get('email', 'Unknown')} at {time_str}"
            else:
                return f"Agent failed extraction for {details.get('provider', 'Unknown')} - {details.get('email', 'Unknown')} at {time_str}: {details.get('error', 'Unknown error')}"
    
    # Credential logs
    elif entity_type == "credential":
        if action == "bulk_upload":
            return f"User uploaded {details.get('count', 0)} credential(s) for {details.get('provider', 'Unknown')} at {time_str}"
        elif action == "delete":
            return f"User deleted credential for {entity} at {time_str}"
    
    # Agent control
    elif entity_type == "agent":
        if action == "start":
            return f"User started agent for {details.get('email', 'Unknown')} ({details.get('provider', 'Unknown')}) at {time_str}"
        elif action == "stop":
            return f"User stopped agent for {details.get('email', 'Unknown')} ({details.get('provider', 'Unknown')}) at {time_str}"
    
    # Scheduled jobs
    elif entity_type == "scheduled_job":
        job_name = entity_name or "Job"
        if action in ["daily_job_start", "retry_job_start"]:
            return f"{job_name} started at {time_str} (schedule: {details.get('schedule', 'Unknown')})"
        elif action in ["daily_job_complete", "retry_job_complete"]:
            if status == "success":
                return f"{job_name} completed at {time_str}: {details.get('processed', 0)} processed, {details.get('success', 0)} success, {details.get('errors', 0)} errors"
            else:
                return f"{job_name} failed at {time_str}: {details.get('error', 'Unknown error')}"
    
    # Provider logs
    elif entity_type == "provider":
        if action == "create":
            return f"User created provider '{entity}' at {time_str}"
        elif action == "update":
            return f"User updated provider '{entity}' at {time_str}"
        elif action == "delete":
            return f"User deleted provider '{entity}' at {time_str}"
    
    # Fallback
    return f"{triggered_by.capitalize()} performed {action} on {entity_type} {entity} at {time_str}"


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
        try:
            with get_db_context() as db:
                # Create timestamp
                timestamp = datetime.utcnow()
                
                # Generate human-readable message
                message = format_audit_log_message(
                    entity_type=entity_type,
                    entity_name=entity_name,
                    entity_id=entity_id,
                    action=action,
                    status=status,
                    triggered_by=triggered_by,
                    details=details,
                    timestamp=timestamp
                )
                
                audit_entry = AuditLog(
                    id=str(uuid.uuid4()),
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    action=action,
                    status=status,
                    triggered_by=triggered_by,
                    timestamp=timestamp,
                    details=details,
                    message=message
                )
                
                db.add(audit_entry)
                db.commit()
                
                # Emoji for better console visibility
                emoji = "👤" if triggered_by == "user" else "🤖"
                status_emoji = "✅" if status == "success" else "❌" if status == "failure" else "⏳"
                print(f"📝 {emoji} Audit: {entity_type}.{action} - {status_emoji} {status}")
                
                return audit_entry.id
            
        except Exception as e:
            print(f"❌ Failed to create audit log: {e}")
            # Don't raise - audit logging shouldn't break the main flow
            return None
    
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

