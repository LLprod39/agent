"""Structured logging and audit logging."""

import json
import logging
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class LogLevel(Enum):
    """Log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditEventType(Enum):
    """Types of audit events."""

    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_APPROVED = "task_approved"
    TASK_REJECTED = "task_rejected"
    SECURITY_VIOLATION = "security_violation"
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    COMMAND_EXECUTED = "command_executed"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    CONFIGURATION_CHANGE = "configuration_change"


@dataclass
class AuditEvent:
    """Audit event data structure."""

    timestamp: datetime
    event_type: AuditEventType
    user_id: str
    session_id: Optional[str]
    task_id: Optional[str]
    environment: Optional[str]
    details: Dict[str, Any]
    severity: str = "info"
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None


class StructuredLogger:
    """Structured logger for application events."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("devops_agent")
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration."""
        log_level = getattr(logging, self.config.get("level", "INFO").upper())
        log_format = self.config.get("format", "json")

        # Clear existing handlers
        self.logger.handlers.clear()

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        if log_format == "json":
            console_handler.setFormatter(JsonFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )

        self.logger.addHandler(console_handler)
        self.logger.setLevel(log_level)

    def log(self, level: LogLevel, message: str, **kwargs):
        """Log a structured message."""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "message": message,
            **kwargs,
        }

        if level == LogLevel.DEBUG:
            self.logger.debug(json.dumps(log_data))
        elif level == LogLevel.INFO:
            self.logger.info(json.dumps(log_data))
        elif level == LogLevel.WARNING:
            self.logger.warning(json.dumps(log_data))
        elif level == LogLevel.ERROR:
            self.logger.error(json.dumps(log_data))
        elif level == LogLevel.CRITICAL:
            self.logger.critical(json.dumps(log_data))

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self.log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self.log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.log(LogLevel.CRITICAL, message, **kwargs)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id
        if hasattr(record, "environment"):
            log_data["environment"] = record.environment
        if hasattr(record, "duration"):
            log_data["duration"] = record.duration
        if hasattr(record, "error"):
            log_data["error"] = record.error

        return json.dumps(log_data)


class AuditLogger:
    """Audit logger for security and compliance events."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("devops_agent.audit")
        self.setup_audit_logging()
        self.events: List[AuditEvent] = []
        self.max_events = config.get("max_events", 10000)

    def setup_audit_logging(self):
        """Setup audit logging configuration."""
        log_level = logging.INFO
        log_format = self.config.get("format", "json")

        # Clear existing handlers
        self.logger.handlers.clear()

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        if log_format == "json":
            console_handler.setFormatter(AuditJsonFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter("%(asctime)s - AUDIT - %(message)s")
            )

        self.logger.addHandler(console_handler)
        self.logger.setLevel(log_level)

    def log_event(self, event: AuditEvent):
        """Log an audit event."""
        # Store in memory
        self.events.append(event)

        # Keep only recent events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]

        # Log to file
        event_data = asdict(event)
        event_data["timestamp"] = event.timestamp.isoformat()
        event_data["event_type"] = event.event_type.value

        self.logger.info(json.dumps(event_data))

    def log_task_started(
        self,
        task_id: str,
        user_id: str,
        session_id: str,
        environment: str,
        details: Dict[str, Any],
    ):
        """Log task started event."""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type=AuditEventType.TASK_STARTED,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            environment=environment,
            details=details,
            severity="info",
        )
        self.log_event(event)

    def log_task_completed(
        self,
        task_id: str,
        user_id: str,
        session_id: str,
        environment: str,
        details: Dict[str, Any],
    ):
        """Log task completed event."""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type=AuditEventType.TASK_COMPLETED,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            environment=environment,
            details=details,
            severity="info",
        )
        self.log_event(event)

    def log_task_failed(
        self,
        task_id: str,
        user_id: str,
        session_id: str,
        environment: str,
        details: Dict[str, Any],
    ):
        """Log task failed event."""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type=AuditEventType.TASK_FAILED,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            environment=environment,
            details=details,
            severity="error",
        )
        self.log_event(event)

    def log_security_violation(
        self, user_id: str, session_id: str, environment: str, details: Dict[str, Any]
    ):
        """Log security violation event."""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type=AuditEventType.SECURITY_VIOLATION,
            user_id=user_id,
            session_id=session_id,
            task_id=None,
            environment=environment,
            details=details,
            severity="warning",
        )
        self.log_event(event)

    def log_llm_request(
        self,
        user_id: str,
        session_id: str,
        provider: str,
        model: str,
        details: Dict[str, Any],
    ):
        """Log LLM request event."""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type=AuditEventType.LLM_REQUEST,
            user_id=user_id,
            session_id=session_id,
            task_id=None,
            environment=None,
            details={"provider": provider, "model": model, **details},
            severity="info",
        )
        self.log_event(event)

    def log_command_executed(
        self,
        task_id: str,
        user_id: str,
        session_id: str,
        environment: str,
        command: str,
        details: Dict[str, Any],
    ):
        """Log command executed event."""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type=AuditEventType.COMMAND_EXECUTED,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            environment=environment,
            details={"command": command, **details},
            severity="info",
        )
        self.log_event(event)

    def get_events(self, limit: int = 100) -> List[AuditEvent]:
        """Get recent audit events."""
        return self.events[-limit:]

    def get_events_by_type(
        self, event_type: AuditEventType, limit: int = 100
    ) -> List[AuditEvent]:
        """Get recent audit events by type."""
        filtered_events = [e for e in self.events if e.event_type == event_type]
        return filtered_events[-limit:]

    def get_events_by_user(self, user_id: str, limit: int = 100) -> List[AuditEvent]:
        """Get recent audit events by user."""
        filtered_events = [e for e in self.events if e.user_id == user_id]
        return filtered_events[-limit:]


class AuditJsonFormatter(logging.Formatter):
    """JSON formatter for audit logging."""

    def format(self, record):
        """Format audit log record as JSON."""
        try:
            # Parse the JSON message
            log_data = json.loads(record.getMessage())
            return json.dumps(log_data)
        except (json.JSONDecodeError, TypeError):
            # Fallback to simple format
            return json.dumps(
                {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "message": record.getMessage(),
                }
            )





