"""Terraform executor for infrastructure as code operations."""

import asyncio
import json
import time
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator
import os
import tempfile

from .base import BaseToolExecutor, ToolConfig, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class TerraformExecutor(BaseToolExecutor):
    """Terraform executor for Infrastructure as Code operations.
    
    Features:
    - terraform plan/apply/destroy workflow
    - State management
    - Variable injection
    - Workspace support
    - Output parsing
    - Dry-run mode
    """

    def __init__(
        self,
        config: ToolConfig,
        working_dir: Optional[str] = None,
        backend_config: Optional[Dict[str, Any]] = None,
        variables: Optional[Dict[str, Any]] = None,
        var_files: Optional[List[str]] = None,
    ):
        super().__init__(config)
        self.working_dir = working_dir or config.working_directory or os.getcwd()
        self.backend_config = backend_config or {}
        self.variables = variables or {}
        self.var_files = var_files or []
        self.workspace = "default"
        self._temp_var_file = None

    def _build_terraform_command(
        self, command: str, extra_args: Optional[List[str]] = None
    ) -> List[str]:
        """Build terraform command with proper arguments."""
        cmd = ["terraform"]

        # Add the subcommand
        cmd.append(command)

        # Add extra arguments
        if extra_args:
            cmd.extend(extra_args)

        return cmd

    def _prepare_var_file(self) -> Optional[str]:
        """Create a temporary variable file if variables are provided."""
        if not self.variables:
            return None

        if not self._temp_var_file:
            self._temp_var_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".tfvars.json", delete=False, dir=self.working_dir
            )
            json.dump(self.variables, self._temp_var_file)
            self._temp_var_file.close()

        return self._temp_var_file.name

    async def init(self, reconfigure: bool = False) -> ToolResult:
        """Initialize Terraform working directory.
        
        Args:
            reconfigure: Whether to reconfigure backend
            
        Returns:
            ToolResult
        """
        start_time = time.time()

        try:
            if self.dry_run:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    "[DRY RUN] Would run: terraform init",
                    execution_time=0.0,
                    metadata={"dry_run": True},
                )

            args = []
            if reconfigure:
                args.append("-reconfigure")

            # Add backend config
            for key, value in self.backend_config.items():
                args.append(f"-backend-config={key}={value}")

            cmd = self._build_terraform_command("init", args)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
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
                logger.info(f"Terraform init completed in {execution_time:.2f}s")
                return self._create_result(
                    ToolStatus.SUCCESS,
                    stdout_str,
                    exit_code=process.returncode,
                    execution_time=execution_time,
                    metadata={"stderr": stderr_str, "command": " ".join(cmd)},
                )
            else:
                logger.error(f"Terraform init failed: {stderr_str}")
                return self._create_result(
                    ToolStatus.FAILED,
                    stdout_str,
                    error=stderr_str,
                    exit_code=process.returncode,
                    execution_time=execution_time,
                )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Terraform init exception: {e}")
            return self._create_result(
                ToolStatus.FAILED, "", error=str(e), execution_time=execution_time
            )

    async def plan(
        self, out_file: Optional[str] = None, destroy: bool = False
    ) -> ToolResult:
        """Generate Terraform execution plan.
        
        Args:
            out_file: File to save plan
            destroy: Generate destroy plan
            
        Returns:
            ToolResult
        """
        start_time = time.time()

        try:
            if self.dry_run:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    "[DRY RUN] Would run: terraform plan",
                    execution_time=0.0,
                    metadata={"dry_run": True},
                )

            args = []

            # Add variable files
            var_file = self._prepare_var_file()
            if var_file:
                args.append(f"-var-file={var_file}")

            for vf in self.var_files:
                args.append(f"-var-file={vf}")

            # Add output file
            if out_file:
                args.append(f"-out={out_file}")

            # Add destroy flag
            if destroy:
                args.append("-destroy")

            cmd = self._build_terraform_command("plan", args)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
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
                logger.info(f"Terraform plan completed in {execution_time:.2f}s")
                return self._create_result(
                    ToolStatus.SUCCESS,
                    stdout_str,
                    exit_code=process.returncode,
                    execution_time=execution_time,
                    metadata={
                        "stderr": stderr_str,
                        "out_file": out_file,
                        "destroy": destroy,
                    },
                )
            else:
                logger.error(f"Terraform plan failed: {stderr_str}")
                return self._create_result(
                    ToolStatus.FAILED,
                    stdout_str,
                    error=stderr_str,
                    exit_code=process.returncode,
                    execution_time=execution_time,
                )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Terraform plan exception: {e}")
            return self._create_result(
                ToolStatus.FAILED, "", error=str(e), execution_time=execution_time
            )

    async def apply(
        self, plan_file: Optional[str] = None, auto_approve: bool = False
    ) -> ToolResult:
        """Apply Terraform changes.
        
        Args:
            plan_file: Plan file to apply
            auto_approve: Skip interactive approval
            
        Returns:
            ToolResult
        """
        start_time = time.time()

        try:
            if self.dry_run:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    "[DRY RUN] Would run: terraform apply",
                    execution_time=0.0,
                    metadata={"dry_run": True},
                )

            args = []

            if plan_file:
                # Apply specific plan
                args.append(plan_file)
            else:
                # Apply with variables
                var_file = self._prepare_var_file()
                if var_file:
                    args.append(f"-var-file={var_file}")

                for vf in self.var_files:
                    args.append(f"-var-file={vf}")

                if auto_approve:
                    args.append("-auto-approve")

            cmd = self._build_terraform_command("apply", args)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if not auto_approve else None,
                cwd=self.working_dir,
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
                logger.info(f"Terraform apply completed in {execution_time:.2f}s")
                return self._create_result(
                    ToolStatus.SUCCESS,
                    stdout_str,
                    exit_code=process.returncode,
                    execution_time=execution_time,
                    metadata={"stderr": stderr_str, "plan_file": plan_file},
                )
            else:
                logger.error(f"Terraform apply failed: {stderr_str}")
                return self._create_result(
                    ToolStatus.FAILED,
                    stdout_str,
                    error=stderr_str,
                    exit_code=process.returncode,
                    execution_time=execution_time,
                )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Terraform apply exception: {e}")
            return self._create_result(
                ToolStatus.FAILED, "", error=str(e), execution_time=execution_time
            )

    async def destroy(self, auto_approve: bool = False) -> ToolResult:
        """Destroy Terraform-managed infrastructure.
        
        Args:
            auto_approve: Skip interactive approval
            
        Returns:
            ToolResult
        """
        start_time = time.time()

        try:
            if self.dry_run:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    "[DRY RUN] Would run: terraform destroy",
                    execution_time=0.0,
                    metadata={"dry_run": True},
                )

            args = []

            # Add variable files
            var_file = self._prepare_var_file()
            if var_file:
                args.append(f"-var-file={var_file}")

            for vf in self.var_files:
                args.append(f"-var-file={vf}")

            if auto_approve:
                args.append("-auto-approve")

            cmd = self._build_terraform_command("destroy", args)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if not auto_approve else None,
                cwd=self.working_dir,
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
                logger.info(f"Terraform destroy completed in {execution_time:.2f}s")
                return self._create_result(
                    ToolStatus.SUCCESS,
                    stdout_str,
                    exit_code=process.returncode,
                    execution_time=execution_time,
                    metadata={"stderr": stderr_str},
                )
            else:
                logger.error(f"Terraform destroy failed: {stderr_str}")
                return self._create_result(
                    ToolStatus.FAILED,
                    stdout_str,
                    error=stderr_str,
                    exit_code=process.returncode,
                    execution_time=execution_time,
                )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Terraform destroy exception: {e}")
            return self._create_result(
                ToolStatus.FAILED, "", error=str(e), execution_time=execution_time
            )

    async def output(self, name: Optional[str] = None) -> ToolResult:
        """Get Terraform outputs.
        
        Args:
            name: Specific output name
            
        Returns:
            ToolResult
        """
        start_time = time.time()

        try:
            args = ["-json"]
            if name:
                args.append(name)

            cmd = self._build_terraform_command("output", args)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout
            )

            execution_time = time.time() - start_time
            stdout_str = stdout.decode("utf-8")
            stderr_str = stderr.decode("utf-8")

            if process.returncode == 0:
                try:
                    outputs = json.loads(stdout_str)
                    return self._create_result(
                        ToolStatus.SUCCESS,
                        stdout_str,
                        exit_code=process.returncode,
                        execution_time=execution_time,
                        metadata={"outputs": outputs},
                    )
                except json.JSONDecodeError:
                    return self._create_result(
                        ToolStatus.SUCCESS,
                        stdout_str,
                        exit_code=process.returncode,
                        execution_time=execution_time,
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

    async def workspace_select(self, workspace: str) -> ToolResult:
        """Select a Terraform workspace.
        
        Args:
            workspace: Workspace name
            
        Returns:
            ToolResult
        """
        result = await self.execute(f"workspace select {workspace}")
        if result.status == ToolStatus.SUCCESS:
            self.workspace = workspace
            logger.info(f"Switched to workspace: {workspace}")
        return result

    async def workspace_list(self) -> List[str]:
        """List Terraform workspaces."""
        result = await self.execute("workspace list")
        if result.status == ToolStatus.SUCCESS:
            workspaces = []
            for line in result.output.split("\n"):
                line = line.strip()
                if line:
                    # Remove asterisk from current workspace
                    workspace = line.lstrip("* ").strip()
                    workspaces.append(workspace)
            return workspaces
        return []

    async def execute(self, command: str, **kwargs) -> ToolResult:
        """Execute a terraform command."""
        start_time = time.time()

        try:
            if self.dry_run:
                return self._create_result(
                    ToolStatus.SUCCESS,
                    f"[DRY RUN] Would execute: terraform {command}",
                    execution_time=0.0,
                    metadata={"dry_run": True},
                )

            cmd = self._build_terraform_command(command.split()[0], command.split()[1:])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
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
        """Stream terraform command execution output."""
        try:
            if self.dry_run:
                yield f"[DRY RUN] Would execute: terraform {command}"
                return

            cmd = self._build_terraform_command(command.split()[0], command.split()[1:])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=self.working_dir,
            )

            async for line in process.stdout:
                yield line.decode("utf-8").rstrip()

            await process.wait()

            if process.returncode != 0:
                yield f"Command failed with exit code: {process.returncode}"

        except Exception as e:
            yield f"Error: {str(e)}"

    async def health_check(self) -> bool:
        """Check if Terraform is available."""
        try:
            result = await self.execute("version")
            return result.status == ToolStatus.SUCCESS
        except Exception:
            return False

    def __del__(self):
        """Cleanup temporary variable file."""
        if self._temp_var_file and os.path.exists(self._temp_var_file.name):
            try:
                os.unlink(self._temp_var_file.name)
            except OSError:
                pass
