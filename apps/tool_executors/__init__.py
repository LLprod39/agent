"""Tool executors for DevOps operations."""

from .base import BaseToolExecutor, ToolResult, ToolError, ToolStatus, ToolConfig

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

def get_terraform_executor():
    """Get Terraform executor with lazy import."""
    from .terraform_executor import TerraformExecutor
    return TerraformExecutor

def get_ansible_executor():
    """Get Ansible executor with lazy import."""
    from .ansible_executor import AnsibleExecutor
    return AnsibleExecutor

__all__ = [
    "BaseToolExecutor",
    "ToolResult",
    "ToolError",
    "ToolStatus",
    "ToolConfig",
    "get_ssh_executor",
    "get_kubectl_executor", 
    "get_docker_executor",
    "get_terraform_executor",
    "get_ansible_executor",
]
