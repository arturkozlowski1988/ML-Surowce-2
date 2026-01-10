"""
Audit Service for AI Supply Assistant.
Logs user actions for compliance and debugging purposes.

Actions logged:
- User login/logout
- Configuration changes
- AI analysis requests
- Data exports
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import threading

logger = logging.getLogger('AuditService')


@dataclass
class AuditEntry:
    """Single audit log entry."""
    timestamp: str
    username: str
    action: str
    details: str = ""
    ip_address: str = ""
    module: str = ""
    

class AuditService:
    """
    Manages audit logging with file-based persistence.
    Thread-safe singleton pattern.
    """
    
    DEFAULT_LOG_FILE = "logs/audit_log.json"
    MAX_ENTRIES = 10000  # Rotate after this many entries
    
    def __init__(self, log_file: str = None):
        """
        Initialize AuditService.
        
        Args:
            log_file: Path to audit log JSON file
        """
        if log_file is None:
            project_root = Path(__file__).parent.parent.parent
            self.log_file = project_root / self.DEFAULT_LOG_FILE
        else:
            self.log_file = Path(log_file)
        
        self._entries: List[AuditEntry] = []
        self._lock = threading.Lock()
        self._load_log()
    
    def _ensure_log_dir(self):
        """Ensures log directory exists."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_log(self):
        """Loads existing log entries from file."""
        self._entries = []
        
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for entry_data in data.get('entries', []):
                        self._entries.append(AuditEntry(**entry_data))
                logger.info(f"Loaded {len(self._entries)} audit entries")
            except Exception as e:
                logger.error(f"Error loading audit log: {e}")
    
    def _save_log(self):
        """Saves log entries to file."""
        self._ensure_log_dir()
        
        try:
            # Rotate if too many entries
            if len(self._entries) > self.MAX_ENTRIES:
                self._entries = self._entries[-self.MAX_ENTRIES:]
            
            data = {
                'entries': [asdict(e) for e in self._entries],
                'last_updated': datetime.now().isoformat()
            }
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving audit log: {e}")
    
    def log(
        self,
        username: str,
        action: str,
        details: str = "",
        module: str = "",
        ip_address: str = ""
    ):
        """
        Logs an audit entry.
        
        Args:
            username: User who performed the action
            action: Action type (e.g., "LOGIN", "ANALYZE_BOM", "CHANGE_LLM")
            details: Additional details about the action
            module: Module where action occurred
            ip_address: User's IP address (if available)
        """
        with self._lock:
            entry = AuditEntry(
                timestamp=datetime.now().isoformat(),
                username=username,
                action=action,
                details=details,
                module=module,
                ip_address=ip_address
            )
            self._entries.append(entry)
            self._save_log()
            logger.debug(f"Audit: {username} - {action}")
    
    def log_login(self, username: str, success: bool = True):
        """Logs user login attempt."""
        action = "LOGIN_SUCCESS" if success else "LOGIN_FAILED"
        self.log(username=username, action=action, module="auth")
    
    def log_logout(self, username: str):
        """Logs user logout."""
        self.log(username=username, action="LOGOUT", module="auth")
    
    def log_config_change(self, username: str, setting: str, old_value: str = "", new_value: str = ""):
        """Logs configuration change."""
        details = f"{setting}: '{old_value}' -> '{new_value}'" if old_value else f"{setting}: '{new_value}'"
        self.log(username=username, action="CONFIG_CHANGE", details=details, module="admin")
    
    def log_analysis(self, username: str, analysis_type: str, product: str = ""):
        """Logs AI analysis request."""
        details = f"Produkt: {product}" if product else ""
        self.log(username=username, action=f"ANALYSIS_{analysis_type.upper()}", details=details, module="assistant")
    
    def log_export(self, username: str, export_type: str, filename: str = ""):
        """Logs data export."""
        self.log(username=username, action="EXPORT", details=f"{export_type}: {filename}", module="export")
    
    def get_entries(
        self,
        limit: int = 100,
        username: str = None,
        action_filter: str = None,
        days_back: int = None
    ) -> List[AuditEntry]:
        """
        Returns filtered audit entries.
        
        Args:
            limit: Maximum entries to return
            username: Filter by username
            action_filter: Filter by action type
            days_back: Only entries from last N days
            
        Returns:
            List of AuditEntry objects (most recent first)
        """
        with self._lock:
            entries = list(self._entries)
        
        # Apply filters
        if username:
            entries = [e for e in entries if e.username.lower() == username.lower()]
        
        if action_filter:
            entries = [e for e in entries if action_filter.upper() in e.action.upper()]
        
        if days_back:
            cutoff = datetime.now() - timedelta(days=days_back)
            entries = [e for e in entries if datetime.fromisoformat(e.timestamp) >= cutoff]
        
        # Sort by timestamp (most recent first) and limit
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        return entries[:limit]
    
    def get_user_stats(self, days_back: int = 7) -> Dict[str, Any]:
        """
        Returns user activity statistics.
        
        Args:
            days_back: Period for statistics
            
        Returns:
            Dict with user activity counts
        """
        entries = self.get_entries(limit=10000, days_back=days_back)
        
        user_counts = {}
        action_counts = {}
        
        for e in entries:
            user_counts[e.username] = user_counts.get(e.username, 0) + 1
            action_counts[e.action] = action_counts.get(e.action, 0) + 1
        
        return {
            'total_actions': len(entries),
            'unique_users': len(user_counts),
            'by_user': user_counts,
            'by_action': action_counts,
            'period_days': days_back
        }
    
    def export_to_csv(self, entries: List[AuditEntry] = None) -> str:
        """
        Exports entries to CSV format.
        
        Args:
            entries: Entries to export (defaults to all)
            
        Returns:
            CSV string
        """
        if entries is None:
            entries = self.get_entries(limit=10000)
        
        lines = ["timestamp,username,action,details,module,ip_address"]
        for e in entries:
            # Escape commas and quotes in details
            details = e.details.replace('"', '""')
            lines.append(f'{e.timestamp},{e.username},{e.action},"{details}",{e.module},{e.ip_address}')
        
        return "\n".join(lines)
    
    def clear_old_entries(self, days_to_keep: int = 90):
        """
        Removes entries older than specified days.
        
        Args:
            days_to_keep: Keep entries from last N days
        """
        with self._lock:
            cutoff = datetime.now() - timedelta(days=days_to_keep)
            self._entries = [
                e for e in self._entries 
                if datetime.fromisoformat(e.timestamp) >= cutoff
            ]
            self._save_log()
            logger.info(f"Cleared old audit entries, {len(self._entries)} remaining")


# Singleton instance
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """Returns singleton AuditService instance."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
