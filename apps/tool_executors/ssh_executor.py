"""SSH executor for remote command execution."""

import asyncio
import time
import logging
from typing import Any, Dict, AsyncGenerator, Optional
import asyncssh

from .base import BaseToolExecutor, ToolConfig, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class SSHExecutor(BaseToolExecutor):
    """SSH executor for remote command execution.
    
    Features:
    - Direct SSH connections
    - Jump host/bastion support
    - Sudo/privilege escalation
    - Key-based and password authentication
    - Connection pooling
    - Timeout handling
    """

    def __init__(self, config: ToolConfig, connection_config: Dict[str, Any]):
        super().__init__(config)
        self.connection_config = connection_config
        self.host = connection_config.get("host")
        self.port = connection_config.get("port", 22)
        self.username = connection_config.get("username")
        self.password = connection_config.get("password")
        self.key_file = connection_config.get("key_file")
        self.jump_host = connection_config.get("jump_host")
        self.sudo_password = connection_config.get("sudo_password")  # Пароль для sudo
        self.become_user = connection_config.get("become_user")  # Пользователь для sudo
        self.connection = None
        self.jump_connection = None
        self._connection_attempts = 0
        self._max_connection_attempts = connection_config.get("max_connection_attempts", 3)

    async def _connect(self) -> None:
        """Establish SSH connection with retry logic."""
        if self.connection and not self.connection.is_closed():
            return

        for attempt in range(self._max_connection_attempts):
            try:
                self._connection_attempts = attempt + 1
                logger.info(
                    f"Connecting to {self.host}:{self.port} (attempt {self._connection_attempts}/{self._max_connection_attempts})"
                )

                if self.jump_host:
                    # Connect through jump host
                    jump_config = self.jump_host
                    logger.info(f"Connecting through jump host: {jump_config['host']}")
                    
                    self.jump_connection = await asyncssh.connect(
                        jump_config["host"],
                        port=jump_config.get("port", 22),
                        username=jump_config.get("username"),
                        password=jump_config.get("password"),
                        known_hosts=None,
                        client_keys=[jump_config.get("key_file")]
                        if jump_config.get("key_file")
                        else None,
                        connect_timeout=10,
                    )

                    # Create tunnel through jump host
                    tunnel = await self.jump_connection.forward_local_port(
                        "", 0, self.host, self.port
                    )

                    self.connection = await asyncssh.connect(
                        "localhost",
                        port=tunnel[1],
                        username=self.username,
                        password=self.password,
                        known_hosts=None,
                        client_keys=[self.key_file] if self.key_file else None,
                        connect_timeout=10,
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
                        connect_timeout=10,
                    )

                logger.info(f"Successfully connected to {self.host}:{self.port}")
                return

            except asyncssh.Error as e:
                logger.warning(
                    f"SSH connection attempt {self._connection_attempts} failed: {str(e)}"
                )
                if attempt < self._max_connection_attempts - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise self._create_error(
                        f"Failed to connect to {self.host}:{self.port} after {self._max_connection_attempts} attempts: {str(e)}"
                    )
            except Exception as e:
                logger.error(f"Unexpected error during SSH connection: {str(e)}")
                raise self._create_error(
                    f"Failed to connect to {self.host}:{self.port}: {str(e)}"
                )

    def _prepare_sudo_command(self, command: str, use_sudo: bool = False) -> str:
        """Prepare command with sudo if needed."""
        if not use_sudo:
            return command

        # Если указан пользователь для sudo
        if self.become_user:
            sudo_cmd = f"sudo -u {self.become_user}"
        else:
            sudo_cmd = "sudo"

        # Если нужен пароль для sudo
        if self.sudo_password:
            # Используем -S для чтения пароля из stdin
            return f"echo '{self.sudo_password}' | {sudo_cmd} -S {command}"
        else:
            return f"{sudo_cmd} {command}"

    async def execute(
        self,
        command: str,
        use_sudo: bool = False,
        become_user: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """Execute a command over SSH.
        
        Args:
            command: Command to execute
            use_sudo: Whether to use sudo for privilege escalation
            become_user: User to become (for sudo -u)
            **kwargs: Additional arguments
            
        Returns:
            ToolResult with execution details
        """
        start_time = time.time()

        try:
            # Подготовить команду
            if become_user:
                self.become_user = become_user
            
            prepared_command = self._prepare_sudo_command(command, use_sudo)

            if self.dry_run:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    f"[DRY RUN] Would execute: {prepared_command}",
                    execution_time=0.0,
                    metadata={
                        "dry_run": True,
                        "original_command": command,
                        "use_sudo": use_sudo,
                    },
                )

            await self._connect()

            logger.debug(f"Executing on {self.host}: {prepared_command}")

            # Execute command with timeout
            try:
                result = await asyncio.wait_for(
                    self.connection.run(prepared_command, check=False),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                execution_time = time.time() - start_time
                logger.warning(
                    f"Command timed out after {self.timeout}s on {self.host}: {command}"
                )
                return self._create_result(
                    ToolStatus.TIMEOUT,
                    "",
                    error=f"Command timed out after {self.timeout} seconds",
                    execution_time=execution_time,
                    metadata={"host": self.host, "command": command},
                )

            execution_time = time.time() - start_time

            # Логирование результата
            if result.exit_status == 0:
                logger.info(
                    f"Command succeeded on {self.host} (exit {result.exit_status}, {execution_time:.2f}s)"
                )
                return self._create_result(
                    ToolStatus.SUCCESS,
                    result.stdout,
                    exit_code=result.exit_status,
                    execution_time=execution_time,
                    metadata={
                        "stderr": result.stderr,
                        "host": self.host,
                        "command": command,
                        "use_sudo": use_sudo,
                    },
                )
            else:
                logger.warning(
                    f"Command failed on {self.host} (exit {result.exit_status}): {result.stderr}"
                )
                return self._create_result(
                    ToolStatus.FAILED,
                    result.stdout,
                    error=result.stderr,
                    exit_code=result.exit_status,
                    execution_time=execution_time,
                    metadata={"host": self.host, "command": command},
                )

        except asyncssh.Error as e:
            execution_time = time.time() - start_time
            logger.error(f"SSH error on {self.host}: {str(e)}")
            return self._create_result(
                ToolStatus.FAILED,
                "",
                error=f"SSH error: {str(e)}",
                execution_time=execution_time,
                metadata={"host": self.host, "error_type": "ssh_error"},
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Unexpected error on {self.host}: {str(e)}")
            return self._create_result(
                ToolStatus.FAILED,
                "",
                error=f"Unexpected error: {str(e)}",
                execution_time=execution_time,
                metadata={"host": self.host, "error_type": "unexpected"},
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

    async def execute_multiple(
        self, commands: list[str], use_sudo: bool = False, stop_on_error: bool = True
    ) -> list[ToolResult]:
        """Execute multiple commands sequentially.
        
        Args:
            commands: List of commands to execute
            use_sudo: Whether to use sudo for all commands
            stop_on_error: Stop execution if any command fails
            
        Returns:
            List of ToolResults
        """
        results = []
        for command in commands:
            result = await self.execute(command, use_sudo=use_sudo)
            results.append(result)
            
            if stop_on_error and result.status != ToolStatus.SUCCESS:
                logger.warning(f"Stopping execution due to failed command: {command}")
                break
                
        return results

    async def upload_file(self, local_path: str, remote_path: str) -> ToolResult:
        """Upload a file to remote host.
        
        Args:
            local_path: Path to local file
            remote_path: Path on remote host
            
        Returns:
            ToolResult
        """
        start_time = time.time()
        
        try:
            if self.dry_run:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    f"[DRY RUN] Would upload {local_path} to {remote_path}",
                    execution_time=0.0,
                    metadata={"dry_run": True},
                )
            
            await self._connect()
            
            async with self.connection.start_sftp_client() as sftp:
                await sftp.put(local_path, remote_path)
            
            execution_time = time.time() - start_time
            logger.info(f"Uploaded {local_path} to {self.host}:{remote_path}")
            
            return self._create_result(
                ToolStatus.SUCCESS,
                f"File uploaded successfully to {remote_path}",
                execution_time=execution_time,
                metadata={
                    "local_path": local_path,
                    "remote_path": remote_path,
                    "host": self.host,
                },
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Failed to upload file: {str(e)}")
            return self._create_result(
                ToolStatus.FAILED,
                "",
                error=f"Upload failed: {str(e)}",
                execution_time=execution_time,
            )

    async def download_file(self, remote_path: str, local_path: str) -> ToolResult:
        """Download a file from remote host.
        
        Args:
            remote_path: Path on remote host
            local_path: Path to save locally
            
        Returns:
            ToolResult
        """
        start_time = time.time()
        
        try:
            if self.dry_run:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    f"[DRY RUN] Would download {remote_path} to {local_path}",
                    execution_time=0.0,
                    metadata={"dry_run": True},
                )
            
            await self._connect()
            
            async with self.connection.start_sftp_client() as sftp:
                await sftp.get(remote_path, local_path)
            
            execution_time = time.time() - start_time
            logger.info(f"Downloaded {self.host}:{remote_path} to {local_path}")
            
            return self._create_result(
                ToolStatus.SUCCESS,
                f"File downloaded successfully to {local_path}",
                execution_time=execution_time,
                metadata={
                    "remote_path": remote_path,
                    "local_path": local_path,
                    "host": self.host,
                },
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Failed to download file: {str(e)}")
            return self._create_result(
                ToolStatus.FAILED,
                "",
                error=f"Download failed: {str(e)}",
                execution_time=execution_time,
            )

    async def close(self):
        """Close SSH connection and cleanup."""
        try:
            if self.connection and not self.connection.is_closed():
                logger.info(f"Closing connection to {self.host}")
                self.connection.close()
                await self.connection.wait_closed()
                
            if self.jump_connection and not self.jump_connection.is_closed():
                logger.info("Closing jump host connection")
                self.jump_connection.close()
                await self.jump_connection.wait_closed()
        except Exception as e:
            logger.warning(f"Error closing SSH connections: {str(e)}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self._connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
