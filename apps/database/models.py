"""Database models for the DevOps LLM Agent."""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    JSON,
    ForeignKey,
    Enum,
    Float,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

Base = declarative_base()


class TaskStatus(enum.Enum):
    """Task status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(enum.Enum):
    """Agent type enumeration."""

    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"


class MessageRole(enum.Enum):
    """Message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sessions = relationship("Session", back_populates="user")
    tasks = relationship("Task", back_populates="user")


class Session(Base):
    """Session model for conversation tracking."""

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=True)
    environment_profile = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session")
    tasks = relationship("Task", back_populates="session")

    # Indexes
    __table_args__ = (Index("idx_session_user_active", "user_id", "is_active"),)


class Message(Base):
    """Message model for conversation history."""

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("Session", back_populates="messages")

    # Indexes
    __table_args__ = (Index("idx_message_session_created", "session_id", "created_at"),)


class Task(Base):
    """Task model for tracking agent tasks."""

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    environment_profile = Column(String(100), nullable=True)
    risk_level = Column(String(20), default="low")
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="tasks")
    session = relationship("Session", back_populates="tasks")
    steps = relationship("TaskStep", back_populates="task")

    # Indexes
    __table_args__ = (
        Index("idx_task_user_status", "user_id", "status"),
        Index("idx_task_session", "session_id"),
        Index("idx_task_created", "created_at"),
    )


class TaskStep(Base):
    """Task step model for tracking individual execution steps."""

    __tablename__ = "task_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    step_id = Column(String(100), nullable=False)  # Original step ID from plan
    description = Column(Text, nullable=False)
    command = Column(Text, nullable=True)
    tool = Column(String(50), nullable=True)
    parameters = Column(JSON, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    agent_type = Column(Enum(AgentType), nullable=True)
    risk_level = Column(String(20), default="low")
    requires_approval = Column(Boolean, default=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    execution_time = Column(Float, nullable=True)
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    task = relationship("Task", back_populates="steps")

    # Indexes
    __table_args__ = (
        Index("idx_task_step_task_status", "task_id", "status"),
        Index("idx_task_step_created", "created_at"),
    )


class EnvironmentProfile(Base):
    """Environment profile model for storing configuration profiles."""

    __tablename__ = "environment_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    profile_data = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (Index("idx_env_profile_active", "is_active"),)


class AuditLog(Base):
    """Audit log model for tracking system events."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_audit_user_created", "user_id", "created_at"),
        Index("idx_audit_action_created", "action", "created_at"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )


class LLMUsage(Base):
    """LLM usage tracking model."""

    __tablename__ = "llm_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    agent_type = Column(Enum(AgentType), nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost = Column(Float, nullable=True)
    response_time = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_llm_usage_user_created", "user_id", "created_at"),
        Index("idx_llm_usage_provider_created", "provider", "created_at"),
        Index("idx_llm_usage_cost", "cost"),
    )


class SystemMetrics(Base):
    """System metrics model for performance tracking."""

    __tablename__ = "system_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_type = Column(String(50), nullable=False)  # counter, gauge, histogram
    labels = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_metrics_name_timestamp", "metric_name", "timestamp"),
        Index("idx_metrics_type_timestamp", "metric_type", "timestamp"),
    )
