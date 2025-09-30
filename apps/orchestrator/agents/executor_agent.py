"""Executor Agent for executing planned steps."""

import asyncio
import json
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentType, AgentRequest, AgentResponse, TaskStatus, TaskStep
from ..llm_router import LLMRouter, LLMRequest


class ExecutorAgent(BaseAgent):
    """Agent responsible for executing planned steps."""
    
    def __init__(self, config: Dict[str, Any], llm_router: LLMRouter):
        super().__init__(AgentType.EXECUTOR, config)
        self.llm_router = llm_router
        self.system_prompt = self._build_system_prompt()
        self.tool_executors = {}  # Will be populated with actual tool executors
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the executor."""
        return """You are a DevOps execution agent. Your role is to execute planned steps safely and efficiently.

Guidelines:
1. Execute commands and operations as specified in the plan
2. Validate inputs and check prerequisites before execution
3. Monitor execution and handle errors gracefully
4. Provide clear feedback on success/failure
5. Follow safety protocols and approval requirements
6. Log all actions for audit purposes

Available tools:
- ssh: Execute commands on remote hosts
- kubectl: Kubernetes operations
- docker: Container operations
- terraform: Infrastructure operations
- ansible: Configuration management

For each step, provide:
- Execution status (success/failure)
- Output or error messages
- Next recommended actions
- Any warnings or concerns"""
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """Process an execution request."""
        try:
            # Extract the step to execute
            step_data = request.context.get("step")
            if not step_data:
                return self._create_response(
                    content="No step provided for execution",
                    status=TaskStatus.FAILED,
                    error="Missing step data in request context"
                )
            
            step = TaskStep(**step_data) if isinstance(step_data, dict) else step_data
            
            # Check if approval is required
            if step.requires_approval and not request.context.get("approved", False):
                return self._create_response(
                    content=f"Step '{step.description}' requires approval",
                    status=TaskStatus.PENDING,
                    requires_approval=True,
                    risk_level=step.risk_level,
                    next_steps=["Wait for approval before execution"]
                )
            
            # Execute the step
            result = await self._execute_step(step, request)
            
            if result["success"]:
                return self._create_response(
                    content=f"Successfully executed: {step.description}",
                    status=TaskStatus.COMPLETED,
                    metadata={
                        "step_id": step.id,
                        "output": result.get("output"),
                        "execution_time": result.get("execution_time")
                    }
                )
            else:
                return self._create_response(
                    content=f"Failed to execute: {step.description}",
                    status=TaskStatus.FAILED,
                    error=result.get("error"),
                    metadata={
                        "step_id": step.id,
                        "output": result.get("output")
                    }
                )
                
        except Exception as e:
            return self._create_response(
                content="Execution failed",
                status=TaskStatus.FAILED,
                error=str(e)
            )
    
    async def _execute_step(self, step: TaskStep, request: AgentRequest) -> Dict[str, Any]:
        """Execute a single step."""
        try:
            # For now, simulate execution based on tool type
            # In a real implementation, this would call actual tool executors
            
            if step.tool == "ssh":
                return await self._execute_ssh_step(step, request)
            elif step.tool == "kubectl":
                return await self._execute_kubectl_step(step, request)
            elif step.tool == "docker":
                return await self._execute_docker_step(step, request)
            elif step.tool == "terraform":
                return await self._execute_terraform_step(step, request)
            else:
                # Generic command execution
                return await self._execute_generic_step(step, request)
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": None
            }
    
    async def _execute_ssh_step(self, step: TaskStep, request: AgentRequest) -> Dict[str, Any]:
        """Execute SSH step using real SSH executor."""
        try:
            # Get SSH configuration from environment profile
            ssh_config = request.environment_profile.get("ssh", {})
            host = ssh_config.get("host", "localhost")
            port = ssh_config.get("port", 22)
            username = ssh_config.get("username", "root")
            password = ssh_config.get("password")
            key_file = ssh_config.get("key_file")
            
            # Create SSH executor
            from ...tool_executors.ssh_executor import SSHExecutor
            from ...tool_executors.base import ToolConfig
            config = ToolConfig(
                name="ssh",
                timeout=30,
                retry_count=3,
                retry_delay=1.0,
                dry_run=request.context.get("dry_run", False)
            )
            
            ssh_executor = SSHExecutor(
                config=config,
                host=host,
                port=port,
                username=username,
                password=password,
                key_file=key_file
            )
            
            # Execute command
            result = await ssh_executor.execute(step.command)
            
            return {
                "success": result.status.value == "success",
                "output": result.output,
                "error": result.error,
                "execution_time": result.execution_time,
                "exit_code": result.exit_code
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": None,
                "execution_time": 0.0
            }
    
    async def _execute_kubectl_step(self, step: TaskStep, request: AgentRequest) -> Dict[str, Any]:
        """Execute kubectl step using real kubectl executor."""
        try:
            # Get Kubernetes configuration from environment profile
            k8s_config = request.environment_profile.get("kubernetes", {})
            kubeconfig = k8s_config.get("kubeconfig")
            context = k8s_config.get("context")
            namespace = k8s_config.get("namespace")
            
            # Create kubectl executor
            from ...tool_executors.kubectl_executor import KubectlExecutor
            from ...tool_executors.base import ToolConfig
            config = ToolConfig(
                name="kubectl",
                timeout=60,
                retry_count=2,
                retry_delay=2.0,
                dry_run=request.context.get("dry_run", False)
            )
            
            kubectl_executor = KubectlExecutor(
                config=config,
                kubeconfig=kubeconfig,
                context=context
            )
            
            if namespace:
                kubectl_executor.namespace = namespace
            
            # Execute command
            result = await kubectl_executor.execute(step.command)
            
            return {
                "success": result.status.value == "success",
                "output": result.output,
                "error": result.error,
                "execution_time": result.execution_time,
                "exit_code": result.exit_code
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": None,
                "execution_time": 0.0
            }
    
    async def _execute_docker_step(self, step: TaskStep, request: AgentRequest) -> Dict[str, Any]:
        """Execute docker step using real docker executor."""
        try:
            # Get Docker configuration from environment profile
            docker_config = request.environment_profile.get("docker", {})
            docker_host = docker_config.get("host")
            
            # Create docker executor
            from ...tool_executors.docker_executor import DockerExecutor
            from ...tool_executors.base import ToolConfig
            config = ToolConfig(
                name="docker",
                timeout=120,
                retry_count=2,
                retry_delay=1.0,
                dry_run=request.context.get("dry_run", False)
            )
            
            docker_executor = DockerExecutor(
                config=config,
                docker_host=docker_host
            )
            
            # Execute command
            result = await docker_executor.execute(step.command)
            
            return {
                "success": result.status.value == "success",
                "output": result.output,
                "error": result.error,
                "execution_time": result.execution_time,
                "exit_code": result.exit_code
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": None,
                "execution_time": 0.0
            }
    
    async def _execute_terraform_step(self, step: TaskStep, request: AgentRequest) -> Dict[str, Any]:
        """Execute terraform step (simulated)."""
        # Simulate terraform execution
        await asyncio.sleep(0.2)
        
        return {
            "success": True,
            "output": f"terraform command executed: {step.command}",
            "execution_time": 0.2
        }
    
    async def _execute_generic_step(self, step: TaskStep, request: AgentRequest) -> Dict[str, Any]:
        """Execute generic step (simulated)."""
        # Simulate generic execution
        await asyncio.sleep(0.05)
        
        return {
            "success": True,
            "output": f"Command executed: {step.command or step.description}",
            "execution_time": 0.05
        }
    
    async def health_check(self) -> bool:
        """Check if executor agent is healthy."""
        try:
            # Test with a simple execution request
            test_step = TaskStep(
                id="test_step",
                description="Test execution",
                command="echo 'test'",
                tool="ssh"
            )
            
            test_request = AgentRequest(
                task="Test execution",
                context={"step": test_step.__dict__, "approved": True}
            )
            
            response = await self.process(test_request)
            return response.status == TaskStatus.COMPLETED
        except Exception:
            return False

