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
        if self.use_python_sdk and self.client:
            try:
                image = self.client.images.get(image_id)
                return image.attrs
            except (NotFound, DockerException) as e:
                logger.error(f"Failed to inspect image: {e}")
                return None
        
        # Fallback to CLI
        try:
            result = await self.execute(f"inspect {image_id}")
            if result.status == ToolStatus.SUCCESS:
                return json.loads(result.output)
        except Exception:
            pass
        return None

    async def run_container(
        self,
        image: str,
        command: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        ports: Optional[Dict[str, int]] = None,
        detach: bool = True,
        name: Optional[str] = None,
    ) -> ToolResult:
        """Run a new container."""
        start_time = time.time()
        
        if self.dry_run:
            return self._create_result(
                ToolStatus.SUCCESS,
                f"[DRY RUN] Would run container from image {image}",
                execution_time=0.0,
                metadata={"dry_run": True},
            )
        
        if self.use_python_sdk and self.client:
            try:
                container = self.client.containers.run(
                    image,
                    command=command,
                    environment=environment or {},
                    volumes=volumes or {},
                    ports=ports or {},
                    detach=detach,
                    name=name,
                )
                
                execution_time = time.time() - start_time
                logger.info(f"Started container {container.id} from image {image}")
                
                return self._create_result(
                    ToolStatus.SUCCESS,
                    f"Container started: {container.id}",
                    execution_time=execution_time,
                    metadata={
                        "container_id": container.id,
                        "image": image,
                        "name": name,
                    },
                )
            except (APIError, DockerException) as e:
                execution_time = time.time() - start_time
                logger.error(f"Failed to run container: {e}")
                return self._create_result(
                    ToolStatus.FAILED,
                    "",
                    error=str(e),
                    execution_time=execution_time,
                )
        
        # Fallback to CLI - упрощенная версия
        return await self.execute(f"run -d --name {name or ''} {image}")

    async def stop_container(self, container_id: str, timeout: int = 10) -> ToolResult:
        """Stop a running container."""
        start_time = time.time()
        
        if self.dry_run:
            return self._create_result(
                ToolStatus.SUCCESS,
                f"[DRY RUN] Would stop container {container_id}",
                execution_time=0.0,
                metadata={"dry_run": True},
            )
        
        if self.use_python_sdk and self.client:
            try:
                container = self.client.containers.get(container_id)
                container.stop(timeout=timeout)
                
                execution_time = time.time() - start_time
                logger.info(f"Stopped container {container_id}")
                
                return self._create_result(
                    ToolStatus.SUCCESS,
                    f"Container {container_id} stopped",
                    execution_time=execution_time,
                )
            except (NotFound, APIError, DockerException) as e:
                execution_time = time.time() - start_time
                logger.error(f"Failed to stop container: {e}")
                return self._create_result(
                    ToolStatus.FAILED, "", error=str(e), execution_time=execution_time
                )
        
        # Fallback to CLI
        return await self.execute(f"stop -t {timeout} {container_id}")

    async def remove_container(
        self, container_id: str, force: bool = False
    ) -> ToolResult:
        """Remove a container."""
        start_time = time.time()
        
        if self.dry_run:
            return self._create_result(
                ToolStatus.SUCCESS,
                f"[DRY RUN] Would remove container {container_id}",
                execution_time=0.0,
                metadata={"dry_run": True},
            )
        
        if self.use_python_sdk and self.client:
            try:
                container = self.client.containers.get(container_id)
                container.remove(force=force)
                
                execution_time = time.time() - start_time
                logger.info(f"Removed container {container_id}")
                
                return self._create_result(
                    ToolStatus.SUCCESS,
                    f"Container {container_id} removed",
                    execution_time=execution_time,
                )
            except (NotFound, APIError, DockerException) as e:
                execution_time = time.time() - start_time
                logger.error(f"Failed to remove container: {e}")
                return self._create_result(
                    ToolStatus.FAILED, "", error=str(e), execution_time=execution_time
                )
        
        # Fallback to CLI
        cmd = f"rm {'-f ' if force else ''}{container_id}"
        return await self.execute(cmd)

    async def pull_image(self, image: str, tag: str = "latest") -> ToolResult:
        """Pull an image from registry."""
        start_time = time.time()
        full_image = f"{image}:{tag}"
        
        if self.dry_run:
            return self._create_result(
                ToolStatus.SUCCESS,
                f"[DRY RUN] Would pull image {full_image}",
                execution_time=0.0,
                metadata={"dry_run": True},
            )
        
        if self.use_python_sdk and self.client:
            try:
                auth_config = self.registry_auth if self.registry_auth else None
                self.client.images.pull(image, tag=tag, auth_config=auth_config)
                
                execution_time = time.time() - start_time
                logger.info(f"Pulled image {full_image}")
                
                return self._create_result(
                    ToolStatus.SUCCESS,
                    f"Image {full_image} pulled successfully",
                    execution_time=execution_time,
                    metadata={"image": full_image},
                )
            except (APIError, DockerException) as e:
                execution_time = time.time() - start_time
                logger.error(f"Failed to pull image: {e}")
                return self._create_result(
                    ToolStatus.FAILED, "", error=str(e), execution_time=execution_time
                )
        
        # Fallback to CLI
        return await self.execute(f"pull {full_image}")

    def close(self):
        """Close Docker client connection."""
        if self.client:
            try:
                self.client.close()
                logger.info("Docker client closed")
            except Exception as e:
                logger.warning(f"Error closing Docker client: {e}")
