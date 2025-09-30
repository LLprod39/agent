"""Tool executors for DevOps operations."""

from .base import BaseToolExecutor, ToolResult, ToolError

# Lazy imports to avoid dependency issues
def get_ssh_executor():
    """Get SSH executor with lazy import."""
    from .ssh_executor import SSHExecutor
    return SSHExecutor

def get_kubectl_executor():
    """Get kubectl executor with lazy import."""
    from .kubectl_executor import KubectlExecutor
    return KubectlExecutor

def get_docker_executor():
    """Get docker executor with lazy import."""
    from .docker_executor import DockerExecutor
    return DockerExecutor

__all__ = [
    "BaseToolExecutor",
    "ToolResult",
    "ToolError",
    "get_ssh_executor",
    "get_kubectl_executor", 
    "get_docker_executor",
]
