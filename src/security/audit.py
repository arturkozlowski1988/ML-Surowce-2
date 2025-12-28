"""
Security Audit Log Module.
Provides logging for security-relevant events for compliance and monitoring.

Events are logged in JSON format for easy parsing and analysis.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from pathlib import Path


class AuditEventType(Enum):
    """Types of security audit events."""
    
    # Authentication & Access
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    SESSION_START = "SESSION_START"
    SESSION_END = "SESSION_END"
    
    # Data Access
    DATA_ACCESS = "DATA_ACCESS"
    DATA_EXPORT = "DATA_EXPORT"
    QUERY_EXECUTE = "QUERY_EXECUTE"
    
    # Configuration
    CONFIG_CHANGE = "CONFIG_CHANGE"
    SECRET_ACCESS = "SECRET_ACCESS"
    
    # AI Operations
    AI_QUERY = "AI_QUERY"
    AI_RESPONSE = "AI_RESPONSE"
    
    # Security
    SECURITY_WARNING = "SECURITY_WARNING"
    SECURITY_ERROR = "SECURITY_ERROR"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SecurityAuditLog:
    """
    Security audit logging system.
    
    Logs security-relevant events to a dedicated log file in JSON format.
    Supports log rotation and structured event data.
    
    Usage:
        audit = SecurityAuditLog()
        audit.log(AuditEventType.DATA_ACCESS, details={"table": "CtiZlecenieElem"})
    """
    
    _instance: Optional['SecurityAuditLog'] = None
    
    def __new__(cls, log_path: str = None):
        """Singleton pattern for consistent audit logging."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, log_path: str = None):
        if self._initialized:
            return
        
        # Configure log path
        self.log_path = log_path or os.getenv(
            'AUDIT_LOG_PATH', 
            'logs/security_audit.log'
        )
        
        # Ensure log directory exists
        log_dir = Path(self.log_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure audit logger
        self.logger = logging.getLogger('SecurityAudit')
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False  # Don't propagate to root logger
        
        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        handler = RotatingFileHandler(
            self.log_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter('%(message)s'))
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        self.logger.addHandler(handler)
        
        self._initialized = True
        
        # Log initialization
        self.log(
            AuditEventType.SESSION_START,
            severity=AuditSeverity.INFO,
            details={"message": "Security audit logging initialized"}
        )
    
    def log(
        self,
        event_type: AuditEventType,
        user: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        details: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log a security audit event.
        
        Args:
            event_type: Type of event (from AuditEventType enum)
            user: User identifier (if applicable)
            severity: Event severity level
            details: Additional event details
            source: Source module/component
            
        Returns:
            The logged event record
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type.value,
            "severity": severity.value,
            "user": user or os.getenv('USERNAME', 'SYSTEM'),
            "source": source or "AI_Supply_Assistant",
            "details": details or {}
        }
        
        # Add hostname for multi-server deployments
        try:
            import socket
            event["hostname"] = socket.gethostname()
        except Exception:
            event["hostname"] = "unknown"
        
        # Log as JSON
        log_line = json.dumps(event, ensure_ascii=False)
        
        # Use appropriate log level
        log_method = getattr(self.logger, severity.value.lower(), self.logger.info)
        log_method(log_line)
        
        return event
    
    def log_data_access(
        self,
        query_name: str,
        table: str = None,
        row_count: int = None,
        duration_ms: float = None
    ):
        """Convenience method for logging data access events."""
        return self.log(
            AuditEventType.DATA_ACCESS,
            details={
                "query_name": query_name,
                "table": table,
                "row_count": row_count,
                "duration_ms": duration_ms
            }
        )
    
    def log_ai_query(
        self,
        engine: str,
        model: str = None,
        prompt_length: int = None,
        response_length: int = None,
        duration_ms: float = None
    ):
        """Convenience method for logging AI query events."""
        return self.log(
            AuditEventType.AI_QUERY,
            details={
                "engine": engine,
                "model": model,
                "prompt_length": prompt_length,
                "response_length": response_length,
                "duration_ms": duration_ms
            }
        )
    
    def log_config_change(self, setting: str, old_value: str = None, new_value: str = None):
        """Convenience method for logging configuration changes."""
        return self.log(
            AuditEventType.CONFIG_CHANGE,
            severity=AuditSeverity.WARNING,
            details={
                "setting": setting,
                "old_value": "[MASKED]" if old_value else None,
                "new_value": "[MASKED]" if new_value else None
            }
        )
    
    def log_security_warning(self, message: str, details: Dict[str, Any] = None):
        """Convenience method for logging security warnings."""
        return self.log(
            AuditEventType.SECURITY_WARNING,
            severity=AuditSeverity.WARNING,
            details={
                "message": message,
                **(details or {})
            }
        )
    
    def get_recent_events(self, count: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent audit events from log file.
        
        Args:
            count: Number of recent events to return
            
        Returns:
            List of event dictionaries
        """
        events = []
        
        try:
            if not os.path.exists(self.log_path):
                return events
            
            with open(self.log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Get last N lines
            for line in lines[-count:]:
                try:
                    event = json.loads(line.strip())
                    events.append(event)
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logging.warning(f"Failed to read audit log: {e}")
        
        return events
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of audit events.
        
        Returns:
            Summary statistics
        """
        events = self.get_recent_events(1000)
        
        if not events:
            return {"total_events": 0}
        
        # Count by type
        by_type = {}
        by_severity = {}
        
        for event in events:
            event_type = event.get("event_type", "UNKNOWN")
            severity = event.get("severity", "UNKNOWN")
            
            by_type[event_type] = by_type.get(event_type, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            "total_events": len(events),
            "by_type": by_type,
            "by_severity": by_severity,
            "log_path": self.log_path
        }


# Global convenience function
def audit_log(
    event_type: AuditEventType,
    **kwargs
) -> Dict[str, Any]:
    """
    Quick access to audit logging.
    
    Usage:
        from src.security.audit import audit_log, AuditEventType
        audit_log(AuditEventType.DATA_ACCESS, details={"query": "get_stock"})
    """
    return SecurityAuditLog().log(event_type, **kwargs)
