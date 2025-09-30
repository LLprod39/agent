"""Docker executor for container operations."""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, AsyncGenerator
import os

from .base import BaseToolExecutor, ToolConfig, ToolResult, ToolStatus


class DockerExecutor(BaseToolExecutor):
    """Docker executor for container operations."""

    def __init__(self, config: ToolConfig, docker_host: Optional[str] = None):
        super().__init__(config)
        self.docker_host = docker_host
        self._docker_available = None

    def _build_docker_command(self, command: str) -> List[str]:
        """Build docker command with proper arguments."""
        cmd = ["docker"]

        # Add docker host if specified
        if self.docker_host:
            cmd.extend(["-H", self.docker_host])

        # Add the actual command
        cmd.extend(command.split())

        return cmd

    async def execute(self, command: str, **kwargs) -> ToolResult:
        """Execute a docker command."""
        start_time = time.time()

        try:
            if self.dry_run:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    f"[DRY RUN] Would execute: docker {command}",
                    execution_time=0.0,
                    metadata={"dry_run": True},
                )

            # Build command
            cmd = self._build_docker_command(command)

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
        """Stream docker command execution output."""
        try:
            if self.dry_run:
                yield f"[DRY RUN] Would execute: docker {command}"
                return

            # Build command
            cmd = self._build_docker_command(command)

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
        """Check if Docker is available and accessible."""
        try:
            result = await self.execute("version")
            return result.status == ToolStatus.SUCCESS
        except Exception:
            return False

    async def list_containers(
        self, all_containers: bool = False
    ) -> List[Dict[str, Any]]:
        """List Docker containers."""
        try:
            cmd = "ps -a" if all_containers else "ps"
            result = await self.execute(f"{cmd} --format json")

            if result.status == ToolStatus.SUCCESS:
                containers = []
                for line in result.output.strip().split("\n"):
                    if line.strip():
                        try:
                            container = json.loads(line)
                            containers.append(container)
                        except json.JSONDecodeError:
                            continue
                return containers
        except Exception:
            pass
        return []

    async def list_images(self) -> List[Dict[str, Any]]:
        """List Docker images."""
        try:
            result = await self.execute("images --format json")

            if result.status == ToolStatus.SUCCESS:
                images = []
                for line in result.output.strip().split("\n"):
                    if line.strip():
                        try:
                            image = json.loads(line)
                            images.append(image)
                        except json.JSONDecodeError:
                            continue
                return images
        except Exception:
            pass
        return []

    async def get_container_logs(self, container_id: str, tail: int = 100) -> str:
        """Get logs from a container."""
        try:
            result = await self.execute(f"logs --tail {tail} {container_id}")
            if result.status == ToolStatus.SUCCESS:
                return result.output
        except Exception:
            pass
        return ""

    async def inspect_container(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Inspect a container."""
        try:
            result = await self.execute(f"inspect {container_id}")
            if result.status == ToolStatus.SUCCESS:
                return json.loads(result.output)
        except Exception:
            pass
        return None

    async def inspect_image(self, image_id: str) -> Optional[Dict[str, Any]]:
        """Inspect an image."""
        try:
            result = await self.execute(f"inspect {image_id}")
            if result.status == ToolStatus.SUCCESS:
                return json.loads(result.output)
        except Exception:
            pass
        return None
