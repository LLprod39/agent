"""Base classes for tool executors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, AsyncGenerator
from enum import Enum


class ToolStatus(Enum):
    """Status of tool execution."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ToolResult:
    """Result of tool execution."""

    status: ToolStatus
    output: str
    error: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ToolError(Exception):
    """Error during tool execution."""

    message: str
    tool: str
    command: Optional[str] = None
    exit_code: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ToolConfig:
    """Configuration for a tool executor."""

    name: str
    timeout: float = 30.0
    retry_count: int = 3
    retry_delay: float = 1.0
    dry_run: bool = False
    environment: Optional[Dict[str, str]] = None
    working_directory: Optional[str] = None


class BaseToolExecutor(ABC):
    """Abstract base class for tool executors."""

    def __init__(self, config: ToolConfig):
        self.config = config
        self.name = config.name
        self.timeout = config.timeout
        self.retry_count = config.retry_count
        self.retry_delay = config.retry_delay
        self.dry_run = config.dry_run
        self.environment = config.environment or {}
        self.working_directory = config.working_directory

    @abstractmethod
    async def execute(self, command: str, **kwargs) -> ToolResult:
        """Execute a command and return result."""
        pass

    @abstractmethod
    async def stream_execute(self, command: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream command execution output."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if tool is available and healthy."""
        pass

    def _create_result(
        self,
        status: ToolStatus,
        output: str,
        error: Optional[str] = None,
        exit_code: Optional[int] = None,
        execution_time: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """Create a standardized tool result."""
        return ToolResult(
            status=status,
            output=output,
            error=error,
            exit_code=exit_code,
            execution_time=execution_time,
            metadata=metadata,
        )

    def _create_error(
        self, message: str, command: Optional[str] = None, **kwargs
    ) -> ToolError:
        """Create a standardized tool error."""
        return ToolError(message=message, tool=self.name, command=command, **kwargs)
