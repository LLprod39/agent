"""Base classes for agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum


class AgentType(Enum):
    """Types of agents."""

    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"
    KNOWLEDGE = "knowledge"


class TaskStatus(Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentRequest:
    """Request to an agent."""

    task: str
    context: Dict[str, Any]
    environment_profile: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AgentResponse:
    """Response from an agent."""

    content: str
    status: TaskStatus
    agent_type: AgentType
    task_id: Optional[str] = None
    next_steps: Optional[List[str]] = None
    requires_approval: bool = False
    risk_level: str = "low"
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class TaskStep:
    """A step in a task plan."""

    id: str
    description: str
    command: Optional[str] = None
    tool: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    risk_level: str = "low"
    requires_approval: bool = False
    dependencies: Optional[List[str]] = None


@dataclass
class TaskPlan:
    """A plan for executing a task."""

    task_id: str
    description: str
    steps: List[TaskStep]
    estimated_duration: Optional[int] = None
    risk_level: str = "low"
    requires_approval: bool = False


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, agent_type: AgentType, config: Dict[str, Any]):
        self.agent_type = agent_type
        self.config = config
        self.name = config.get("name", agent_type.value)

    @abstractmethod
    async def process(self, request: AgentRequest) -> AgentResponse:
        """Process a request and return response."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if agent is healthy."""
        pass

    def _create_response(
        self,
        content: str,
        status: TaskStatus,
        task_id: Optional[str] = None,
        next_steps: Optional[List[str]] = None,
        requires_approval: bool = False,
        risk_level: str = "low",
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> AgentResponse:
        """Create a standardized response."""
        return AgentResponse(
            content=content,
            status=status,
            agent_type=self.agent_type,
            task_id=task_id,
            next_steps=next_steps,
            requires_approval=requires_approval,
            risk_level=risk_level,
            metadata=metadata,
            error=error,
        )
