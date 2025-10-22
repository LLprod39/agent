"""Pydantic models for the API."""

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(str, Enum):
    """Task status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskLevel(str, Enum):
    """Risk level enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MessageRole(str, Enum):
    """Message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# Base models
class BaseResponse(BaseModel):
    """Base response model."""

    model_config = ConfigDict(ser_json_timedelta='iso8601')

    success: bool = True
    message: str = "Success"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ErrorResponse(BaseResponse):
    """Error response model."""

    success: bool = False
    error: str
    status_code: int
    details: Optional[Dict[str, Any]] = None


# Conversation models
class Message(BaseModel):
    """Message model."""

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: Optional[Dict[str, Any]] = None


class ConversationRequest(BaseModel):
    """Conversation request model."""

    message: str
    session_id: Optional[str] = None
    environment_profile: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    stream: bool = False


class ConversationResponse(BaseResponse):
    """Conversation response model."""

    session_id: str
    message: str
    task_id: Optional[str] = None
    requires_approval: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    metadata: Optional[Dict[str, Any]] = None


# Task models
class TaskStep(BaseModel):
    """Task step model."""

    id: str
    description: str
    command: Optional[str] = None
    tool: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    dependencies: Optional[List[str]] = None


class TaskPlan(BaseModel):
    """Task plan model."""

    task_id: str
    description: str
    steps: List[TaskStep]
    estimated_duration: Optional[int] = None
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False


class TaskRequest(BaseModel):
    """Task request model."""

    task: str
    environment_profile: Optional[Union[str, Dict[str, Any]]] = None
    context: Optional[Dict[str, Any]] = None
    auto_approve: bool = False
    metadata: Optional[Dict[str, Any]] = None


class TaskResponse(BaseResponse):
    """Task response model."""

    task_id: str
    status: TaskStatus
    message: str
    results: List[Dict[str, Any]]
    requires_approval: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    metadata: Optional[Dict[str, Any]] = None


class TaskStatusResponse(BaseResponse):
    """Task status response model."""

    task_id: str
    status: TaskStatus
    current_step: str
    results: List[Dict[str, Any]]
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskApprovalRequest(BaseModel):
    """Task approval request model."""

    approved: bool = True
    reason: Optional[str] = None


# Environment models
class EnvironmentProfile(BaseModel):
    """Environment profile model."""

    id: str
    display_name: Optional[str] = None
    type: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    cluster: Optional[Dict[str, Any]] = None
    networking: Optional[Dict[str, Any]] = None
    auth: Optional[Dict[str, Any]] = None
    policies: Optional[Dict[str, Any]] = None
    defaults: Optional[Dict[str, Any]] = None
    runbooks: Optional[List[str]] = None
    notes: Optional[str] = None
    ssh: Optional[Dict[str, Any]] = None
    extensions: Optional[Dict[str, Any]] = None


class EnvironmentListResponse(BaseResponse):
    """Environment list response model."""

    environments: List[EnvironmentProfile]


class EnvironmentResponse(BaseResponse):
    """Environment response model."""

    environment: EnvironmentProfile


# Health models
class HealthCheck(BaseModel):
    """Health check model."""

    component: str
    status: str
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseResponse):
    """Health response model."""

    status: str
    components: List[HealthCheck]
    uptime: Optional[float] = None


# Session models
class Session(BaseModel):
    """Session model."""

    id: str
    user_id: Optional[str] = None
    environment_profile: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    messages: List[Message] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class SessionResponse(BaseResponse):
    """Session response model."""

    session: Session


class SessionListResponse(BaseResponse):
    """Session list response model."""

    sessions: List[Session]
    total: int
    page: int
    size: int
