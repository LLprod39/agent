"""Kubectl executor for Kubernetes operations."""

import asyncio
import time
from typing import List, Optional, AsyncGenerator
import tempfile
import os

from .base import BaseToolExecutor, ToolConfig, ToolResult, ToolStatus


class KubectlExecutor(BaseToolExecutor):
    """Kubectl executor for Kubernetes operations."""

    def __init__(
        self,
        config: ToolConfig,
        kubeconfig: Optional[str] = None,
        context: Optional[str] = None,
    ):
        super().__init__(config)
        self.kubeconfig = kubeconfig
        self.context = context
        self.namespace = None
        self._temp_kubeconfig = None

    def _prepare_kubeconfig(self) -> str:
        """Prepare kubeconfig file for use."""
        if self.kubeconfig and os.path.exists(self.kubeconfig):
            return self.kubeconfig

        # Create temporary kubeconfig if none provided
        if not self._temp_kubeconfig:
            self._temp_kubeconfig = tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            )
            # Write default kubeconfig content
            default_config = {
                "apiVersion": "v1",
                "kind": "Config",
                "clusters": [],
                "contexts": [],
                "current-context": "",
                "users": [],
            }
            import yaml

            yaml.dump(default_config, self._temp_kubeconfig)
            self._temp_kubeconfig.close()

        return self._temp_kubeconfig.name

    def _build_kubectl_command(self, command: str) -> List[str]:
        """Build kubectl command with proper arguments."""
        cmd = ["kubectl"]

        # Add kubeconfig
        if self.kubeconfig or self._temp_kubeconfig:
            cmd.extend(["--kubeconfig", self._prepare_kubeconfig()])

        # Add context
        if self.context:
            cmd.extend(["--context", self.context])

        # Add namespace
        if self.namespace:
            cmd.extend(["--namespace", self.namespace])

        # Add the actual command
        cmd.extend(command.split())

        return cmd

    async def execute(self, command: str, **kwargs) -> ToolResult:
        """Execute a kubectl command."""
        start_time = time.time()

        try:
            if self.dry_run:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    f"[DRY RUN] Would execute: kubectl {command}",
                    execution_time=0.0,
                    metadata={"dry_run": True},
                )

            # Build command
            cmd = self._build_kubectl_command(command)

            # Set environment
            env = os.environ.copy()
            env.update(self.environment)

            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=self.working_directory,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                execution_time = time.time() - start_time
                return self._create_result(
                    ToolStatus.TIMEOUT,
                    "",
                    error=f"Command timed out after {self.timeout} seconds",
                    execution_time=execution_time,
                )

            execution_time = time.time() - start_time
            stdout_str = stdout.decode("utf-8")
            stderr_str = stderr.decode("utf-8")

            if process.returncode == 0:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    stdout_str,
                    exit_code=process.returncode,
                    execution_time=execution_time,
                    metadata={"stderr": stderr_str, "command": " ".join(cmd)},
                )
            else:
                return self._create_result(
                    ToolStatus.FAILED,
                    stdout_str,
                    error=stderr_str,
                    exit_code=process.returncode,
                    execution_time=execution_time,
                    metadata={"command": " ".join(cmd)},
                )

        except Exception as e:
            execution_time = time.time() - start_time
            return self._create_result(
                ToolStatus.FAILED, "", error=str(e), execution_time=execution_time
            )

    async def stream_execute(self, command: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream kubectl command execution output."""
        try:
            if self.dry_run:
                yield f"[DRY RUN] Would execute: kubectl {command}"
                return

            # Build command
            cmd = self._build_kubectl_command(command)

            # Set environment
            env = os.environ.copy()
            env.update(self.environment)

            # Execute command with streaming
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
                cwd=self.working_directory,
            )

            # Stream output
            async for line in process.stdout:
                yield line.decode("utf-8").rstrip()

            # Wait for process to complete
            await process.wait()

            if process.returncode != 0:
                yield f"Command failed with exit code: {process.returncode}"

        except Exception as e:
            yield f"Error: {str(e)}"

    async def health_check(self) -> bool:
        """Check if kubectl is available and cluster is accessible."""
        try:
            result = await self.execute("cluster-info")
            return result.status == ToolStatus.SUCCESS
        except Exception:
            return False

    def set_namespace(self, namespace: str):
        """Set the default namespace for kubectl commands."""
        self.namespace = namespace

    def get_current_context(self) -> Optional[str]:
        """Get the current kubectl context."""
        return self.context

    def list_contexts(self) -> List[str]:
        """List available kubectl contexts."""
        try:
            result = asyncio.run(self.execute("config get-contexts -o name"))
            if result.status == ToolStatus.SUCCESS:
                return [
                    line.strip() for line in result.output.split("\n") if line.strip()
                ]
        except Exception:
            pass
        return []

    def __del__(self):
        """Cleanup temporary kubeconfig file."""
        if self._temp_kubeconfig and os.path.exists(self._temp_kubeconfig.name):
            try:
                os.unlink(self._temp_kubeconfig.name)
            except OSError:
                pass
