"""Ansible executor for configuration management and automation."""

import asyncio
import json
import time
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator
import os
import tempfile
import yaml

from .base import BaseToolExecutor, ToolConfig, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class AnsibleExecutor(BaseToolExecutor):
    """Ansible executor for configuration management.
    
    Features:
    - Playbook execution
    - Ad-hoc commands
    - Inventory management
    - Vault integration
    - Module execution
    - Limit and tags support
    """

    def __init__(
        self,
        config: ToolConfig,
        inventory_file: Optional[str] = None,
        inventory: Optional[Dict[str, Any]] = None,
        extra_vars: Optional[Dict[str, Any]] = None,
        vault_password_file: Optional[str] = None,
        private_key_file: Optional[str] = None,
    ):
        super().__init__(config)
        self.inventory_file = inventory_file
        self.inventory = inventory or {}
        self.extra_vars = extra_vars or {}
        self.vault_password_file = vault_password_file
        self.private_key_file = private_key_file
        self._temp_inventory_file = None
        self._temp_vars_file = None

    def _prepare_inventory_file(self) -> Optional[str]:
        """Create a temporary inventory file if inventory dict is provided."""
        if not self.inventory or self.inventory_file:
            return self.inventory_file

        if not self._temp_inventory_file:
            self._temp_inventory_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".yml", delete=False
            )
            yaml.dump(self.inventory, self._temp_inventory_file)
            self._temp_inventory_file.close()

        return self._temp_inventory_file.name

    def _prepare_extra_vars_file(self) -> Optional[str]:
        """Create a temporary extra vars file."""
        if not self.extra_vars:
            return None

        if not self._temp_vars_file:
            self._temp_vars_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            )
            json.dump(self.extra_vars, self._temp_vars_file)
            self._temp_vars_file.close()

        return self._temp_vars_file.name

    def _build_ansible_playbook_command(
        self,
        playbook: str,
        extra_args: Optional[List[str]] = None,
        limit: Optional[str] = None,
        tags: Optional[List[str]] = None,
        skip_tags: Optional[List[str]] = None,
        check: bool = False,
    ) -> List[str]:
        """Build ansible-playbook command."""
        cmd = ["ansible-playbook"]

        # Add inventory
        inventory_file = self._prepare_inventory_file()
        if inventory_file:
            cmd.extend(["-i", inventory_file])

        # Add extra vars
        vars_file = self._prepare_extra_vars_file()
        if vars_file:
            cmd.extend(["-e", f"@{vars_file}"])

        # Add vault password file
        if self.vault_password_file:
            cmd.extend(["--vault-password-file", self.vault_password_file])

        # Add private key
        if self.private_key_file:
            cmd.extend(["--private-key", self.private_key_file])

        # Add limit
        if limit:
            cmd.extend(["-l", limit])

        # Add tags
        if tags:
            cmd.extend(["-t", ",".join(tags)])

        # Add skip tags
        if skip_tags:
            cmd.extend(["--skip-tags", ",".join(skip_tags)])

        # Add check mode
        if check:
            cmd.append("--check")

        # Add playbook
        cmd.append(playbook)

        # Add extra arguments
        if extra_args:
            cmd.extend(extra_args)

        return cmd

    def _build_ansible_command(
        self,
        module: str,
        args: Optional[str] = None,
        hosts: str = "all",
        extra_args: Optional[List[str]] = None,
    ) -> List[str]:
        """Build ansible ad-hoc command."""
        cmd = ["ansible"]

        # Add inventory
        inventory_file = self._prepare_inventory_file()
        if inventory_file:
            cmd.extend(["-i", inventory_file])

        # Add vault password file
        if self.vault_password_file:
            cmd.extend(["--vault-password-file", self.vault_password_file])

        # Add private key
        if self.private_key_file:
            cmd.extend(["--private-key", self.private_key_file])

        # Add hosts pattern
        cmd.append(hosts)

        # Add module
        cmd.extend(["-m", module])

        # Add module arguments
        if args:
            cmd.extend(["-a", args])

        # Add extra arguments
        if extra_args:
            cmd.extend(extra_args)

        return cmd

    async def run_playbook(
        self,
        playbook: str,
        limit: Optional[str] = None,
        tags: Optional[List[str]] = None,
        skip_tags: Optional[List[str]] = None,
        check: bool = False,
        verbose: int = 0,
    ) -> ToolResult:
        """Execute an Ansible playbook.
        
        Args:
            playbook: Path to playbook file
            limit: Limit execution to specific hosts
            tags: Run only tasks with specific tags
            skip_tags: Skip tasks with specific tags
            check: Run in check mode (dry-run)
            verbose: Verbosity level (0-4)
            
        Returns:
            ToolResult
        """
        start_time = time.time()

        try:
            if self.dry_run:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    f"[DRY RUN] Would run playbook: {playbook}",
                    execution_time=0.0,
                    metadata={"dry_run": True, "playbook": playbook},
                )

            extra_args = []
            if verbose > 0:
                extra_args.append("-" + "v" * min(verbose, 4))

            cmd = self._build_ansible_playbook_command(
                playbook=playbook,
                extra_args=extra_args,
                limit=limit,
                tags=tags,
                skip_tags=skip_tags,
                check=check,
            )

            logger.info(f"Running playbook: {playbook}")
            logger.debug(f"Command: {' '.join(cmd)}")

            env = os.environ.copy()
            env.update(self.environment)

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
                logger.warning(f"Playbook execution timed out after {self.timeout}s")
                return self._create_result(
                    ToolStatus.TIMEOUT,
                    "",
                    error=f"Playbook timed out after {self.timeout} seconds",
                    execution_time=execution_time,
                )

            execution_time = time.time() - start_time
            stdout_str = stdout.decode("utf-8")
            stderr_str = stderr.decode("utf-8")

            if process.returncode == 0:
                logger.info(f"Playbook {playbook} completed in {execution_time:.2f}s")
                return self._create_result(
                    ToolStatus.SUCCESS,
                    stdout_str,
                    exit_code=process.returncode,
                    execution_time=execution_time,
                    metadata={
                        "stderr": stderr_str,
                        "playbook": playbook,
                        "limit": limit,
                        "tags": tags,
                        "check_mode": check,
                    },
                )
            else:
                logger.error(f"Playbook {playbook} failed: {stderr_str}")
                return self._create_result(
                    ToolStatus.FAILED,
                    stdout_str,
                    error=stderr_str,
                    exit_code=process.returncode,
                    execution_time=execution_time,
                    metadata={"playbook": playbook},
                )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Playbook execution exception: {e}")
            return self._create_result(
                ToolStatus.FAILED, "", error=str(e), execution_time=execution_time
            )

    async def run_module(
        self,
        module: str,
        args: Optional[str] = None,
        hosts: str = "all",
        become: bool = False,
        become_user: str = "root",
    ) -> ToolResult:
        """Execute an Ansible module (ad-hoc command).
        
        Args:
            module: Ansible module name
            args: Module arguments
            hosts: Host pattern
            become: Use privilege escalation
            become_user: User to become
            
        Returns:
            ToolResult
        """
        start_time = time.time()

        try:
            if self.dry_run:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    f"[DRY RUN] Would run module: {module} on {hosts}",
                    execution_time=0.0,
                    metadata={"dry_run": True, "module": module, "hosts": hosts},
                )

            extra_args = []
            if become:
                extra_args.append("--become")
                extra_args.extend(["--become-user", become_user])

            cmd = self._build_ansible_command(
                module=module, args=args, hosts=hosts, extra_args=extra_args
            )

            logger.info(f"Running module {module} on {hosts}")
            logger.debug(f"Command: {' '.join(cmd)}")

            env = os.environ.copy()
            env.update(self.environment)

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
                logger.warning(f"Module execution timed out after {self.timeout}s")
                return self._create_result(
                    ToolStatus.TIMEOUT,
                    "",
                    error=f"Module timed out after {self.timeout} seconds",
                    execution_time=execution_time,
                )

            execution_time = time.time() - start_time
            stdout_str = stdout.decode("utf-8")
            stderr_str = stderr.decode("utf-8")

            if process.returncode == 0:
                logger.info(
                    f"Module {module} completed on {hosts} in {execution_time:.2f}s"
                )
                return self._create_result(
                    ToolStatus.SUCCESS,
                    stdout_str,
                    exit_code=process.returncode,
                    execution_time=execution_time,
                    metadata={
                        "stderr": stderr_str,
                        "module": module,
                        "hosts": hosts,
                        "args": args,
                    },
                )
            else:
                logger.error(f"Module {module} failed on {hosts}: {stderr_str}")
                return self._create_result(
                    ToolStatus.FAILED,
                    stdout_str,
                    error=stderr_str,
                    exit_code=process.returncode,
                    execution_time=execution_time,
                    metadata={"module": module, "hosts": hosts},
                )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Module execution exception: {e}")
            return self._create_result(
                ToolStatus.FAILED, "", error=str(e), execution_time=execution_time
            )

    async def gather_facts(self, hosts: str = "all") -> Dict[str, Any]:
        """Gather facts from hosts using setup module.
        
        Args:
            hosts: Host pattern
            
        Returns:
            Dictionary of facts
        """
        result = await self.run_module("setup", hosts=hosts)
        
        if result.status == ToolStatus.SUCCESS:
            try:
                # Parse ansible output to extract facts
                # Ansible output for setup module is JSON per host
                facts = {}
                for line in result.output.split("\n"):
                    if "SUCCESS" in line and "{" in line:
                        # Try to parse JSON from the line
                        json_start = line.find("{")
                        json_str = line[json_start:]
                        try:
                            host_facts = json.loads(json_str)
                            # Extract hostname from previous lines or facts
                            facts[hosts] = host_facts
                        except json.JSONDecodeError:
                            continue
                return facts
            except Exception as e:
                logger.error(f"Failed to parse facts: {e}")
                return {}
        
        return {}

    async def ping(self, hosts: str = "all") -> ToolResult:
        """Test connectivity to hosts using ping module.
        
        Args:
            hosts: Host pattern
            
        Returns:
            ToolResult
        """
        return await self.run_module("ping", hosts=hosts)

    async def execute(self, command: str, **kwargs) -> ToolResult:
        """Execute an arbitrary ansible/ansible-playbook command."""
        start_time = time.time()

        try:
            if self.dry_run:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    f"[DRY RUN] Would execute: {command}",
                    execution_time=0.0,
                    metadata={"dry_run": True},
                )

            # Determine if this is playbook or ad-hoc command
            cmd_parts = command.split()
            if not cmd_parts:
                raise ValueError("Empty command")

            # For simplicity, just execute as shell command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
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
                    metadata={"stderr": stderr_str},
                )
            else:
                return self._create_result(
                    ToolStatus.FAILED,
                    stdout_str,
                    error=stderr_str,
                    exit_code=process.returncode,
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

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=self.working_directory,
            )

            async for line in process.stdout:
                yield line.decode("utf-8").rstrip()

            await process.wait()

            if process.returncode != 0:
                yield f"Command failed with exit code: {process.returncode}"

        except Exception as e:
            yield f"Error: {str(e)}"

    async def health_check(self) -> bool:
        """Check if Ansible is available."""
        try:
            process = await asyncio.create_subprocess_exec(
                "ansible",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5)
            return process.returncode == 0
        except Exception:
            return False

    def __del__(self):
        """Cleanup temporary files."""
        if self._temp_inventory_file and os.path.exists(self._temp_inventory_file.name):
            try:
                os.unlink(self._temp_inventory_file.name)
            except OSError:
                pass
        
        if self._temp_vars_file and os.path.exists(self._temp_vars_file.name):
            try:
                os.unlink(self._temp_vars_file.name)
            except OSError:
                pass
