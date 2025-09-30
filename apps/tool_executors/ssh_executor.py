"""SSH executor for remote command execution."""

import asyncio
import time
from typing import Any, Dict, AsyncGenerator
import asyncssh

from .base import BaseToolExecutor, ToolConfig, ToolResult, ToolStatus


class SSHExecutor(BaseToolExecutor):
    """SSH executor for remote command execution."""

    def __init__(self, config: ToolConfig, connection_config: Dict[str, Any]):
        super().__init__(config)
        self.connection_config = connection_config
        self.host = connection_config.get("host")
        self.port = connection_config.get("port", 22)
        self.username = connection_config.get("username")
        self.password = connection_config.get("password")
        self.key_file = connection_config.get("key_file")
        self.jump_host = connection_config.get("jump_host")
        self.connection = None

    async def _connect(self) -> None:
        """Establish SSH connection."""
        if self.connection and not self.connection.is_closed():
            return

        try:
            if self.jump_host:
                # Connect through jump host
                jump_config = self.jump_host
                jump_conn = await asyncssh.connect(
                    jump_config["host"],
                    port=jump_config.get("port", 22),
                    username=jump_config.get("username"),
                    password=jump_config.get("password"),
                    known_hosts=None,
                    client_keys=[jump_config.get("key_file")]
                    if jump_config.get("key_file")
                    else None,
                )

                # Create tunnel through jump host
                tunnel = await jump_conn.create_tunnel(self.host, self.port)

                self.connection = await asyncssh.connect(
                    "localhost",
                    port=tunnel.get_port(),
                    username=self.username,
                    password=self.password,
                    known_hosts=None,
                    client_keys=[self.key_file] if self.key_file else None,
                )
            else:
                # Direct connection
                self.connection = await asyncssh.connect(
                    self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    known_hosts=None,
                    client_keys=[self.key_file] if self.key_file else None,
                )

        except Exception as e:
            raise self._create_error(f"Failed to connect to {self.host}: {str(e)}")

    async def execute(self, command: str, **kwargs) -> ToolResult:
        """Execute a command over SSH."""
        start_time = time.time()

        try:
            if self.dry_run:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    f"[DRY RUN] Would execute: {command}",
                    execution_time=0.0,
                    metadata={"dry_run": True},
                )

            await self._connect()

            # Execute command
            result = await self.connection.run(
                command, timeout=self.timeout, check=False
            )

            execution_time = time.time() - start_time

            if result.exit_status == 0:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    result.stdout,
                    exit_code=result.exit_status,
                    execution_time=execution_time,
                    metadata={"stderr": result.stderr, "host": self.host},
                )
            else:
                return self._create_result(
                    ToolStatus.FAILED,
                    result.stdout,
                    error=result.stderr,
                    exit_code=result.exit_status,
                    execution_time=execution_time,
                    metadata={"host": self.host},
                )

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            return self._create_result(
                ToolStatus.TIMEOUT,
                "",
                error=f"Command timed out after {self.timeout} seconds",
                execution_time=execution_time,
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return self._create_result(
                ToolStatus.FAILED, "", error=str(e), execution_time=execution_time
            )

    async def stream_execute(self, command: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream command execution output."""
        try:
            if self.dry_run:
                yield f"[DRY RUN] Would execute: {command}"
                return

            await self._connect()

            # Execute command with streaming
            async with self.connection.create_process(command) as process:
                async for line in process.stdout:
                    yield line.rstrip()

                # Wait for process to complete
                await process.wait()

                if process.exit_status != 0:
                    yield f"Command failed with exit code: {process.exit_status}"
                    if process.stderr:
                        async for line in process.stderr:
                            yield f"STDERR: {line.rstrip()}"

        except Exception as e:
            yield f"Error: {str(e)}"

    async def health_check(self) -> bool:
        """Check if SSH connection is healthy."""
        try:
            await self._connect()
            # Test with a simple command
            result = await self.connection.run("echo 'health_check'", timeout=5)
            return result.exit_status == 0
        except Exception:
            return False

    async def close(self):
        """Close SSH connection."""
        if self.connection and not self.connection.is_closed():
            self.connection.close()
            await self.connection.wait_closed()

    async def __aenter__(self):
        """Async context manager entry."""
        await self._connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
