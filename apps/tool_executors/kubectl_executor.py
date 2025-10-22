"""Kubectl executor for Kubernetes operations."""

import asyncio
import time
import logging
from typing import List, Optional, AsyncGenerator, Dict, Any
import tempfile
import os
import yaml

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    client = None
    config = None
    ApiException = Exception

from .base import BaseToolExecutor, ToolConfig, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class KubectlExecutor(BaseToolExecutor):
    """Kubectl executor for Kubernetes operations.
    
    Features:
    - Kubernetes Python client integration
    - kubectl CLI fallback
    - Context switching
    - Namespace management
    - RBAC awareness
    - Helm operations support (via subprocess)
    """

    def __init__(
        self,
        config: ToolConfig,
        kubeconfig: Optional[str] = None,
        context: Optional[str] = None,
        use_python_client: bool = True,
    ):
        super().__init__(config)
        self.kubeconfig = kubeconfig or os.environ.get("KUBECONFIG")
        self.context = context
        self.namespace = "default"
        self._temp_kubeconfig = None
        self.use_python_client = use_python_client and KUBERNETES_AVAILABLE
        
        # Kubernetes API clients
        self.core_v1 = None
        self.apps_v1 = None
        self.batch_v1 = None
        self.networking_v1 = None
        
        if self.use_python_client:
            self._init_k8s_clients()

    def _init_k8s_clients(self):
        """Initialize Kubernetes API clients."""
        try:
            if self.kubeconfig:
                config.load_kube_config(
                    config_file=self.kubeconfig, context=self.context
                )
            else:
                # Try in-cluster config first, then default kubeconfig
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    config.load_kube_config(context=self.context)
            
            # Initialize API clients
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.batch_v1 = client.BatchV1Api()
            self.networking_v1 = client.NetworkingV1Api()
            
            logger.info("Kubernetes Python client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize K8s Python client: {e}")
            self.use_python_client = False

    def _prepare_kubeconfig(self) -> str:
        """Prepare kubeconfig file for use."""
        if self.kubeconfig and os.path.exists(self.kubeconfig):
            return self.kubeconfig

        # Try to use default kubeconfig
        default_kubeconfig = os.path.expanduser("~/.kube/config")
        if os.path.exists(default_kubeconfig):
            return default_kubeconfig

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
            if self.use_python_client and self.core_v1:
                # Use Python client for health check
                version = self.core_v1.get_api_resources()
                logger.info("Kubernetes cluster is accessible via Python client")
                return True
            else:
                # Fallback to kubectl CLI
                result = await self.execute("cluster-info")
                return result.status == ToolStatus.SUCCESS
        except Exception as e:
            logger.error(f"Kubernetes health check failed: {e}")
            return False

    def set_namespace(self, namespace: str):
        """Set the default namespace for kubectl commands."""
        self.namespace = namespace
        logger.info(f"Set namespace to: {namespace}")

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

    async def get_pods(
        self, namespace: Optional[str] = None, label_selector: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of pods using Python client.
        
        Args:
            namespace: Namespace to query (defaults to self.namespace)
            label_selector: Label selector for filtering
            
        Returns:
            List of pod dictionaries
        """
        if not self.use_python_client:
            logger.warning("Python client not available, falling back to kubectl")
            result = await self.execute(
                f"get pods -n {namespace or self.namespace} -o json"
            )
            if result.status == ToolStatus.SUCCESS:
                import json
                data = json.loads(result.output)
                return data.get("items", [])
            return []

        try:
            ns = namespace or self.namespace
            pods = self.core_v1.list_namespaced_pod(
                namespace=ns, label_selector=label_selector
            )
            return [
                {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "status": pod.status.phase,
                    "node": pod.spec.node_name,
                    "ip": pod.status.pod_ip,
                    "labels": pod.metadata.labels,
                }
                for pod in pods.items
            ]
        except ApiException as e:
            logger.error(f"Failed to get pods: {e}")
            return []

    async def get_deployments(
        self, namespace: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of deployments.
        
        Args:
            namespace: Namespace to query
            
        Returns:
            List of deployment dictionaries
        """
        if not self.use_python_client:
            result = await self.execute(
                f"get deployments -n {namespace or self.namespace} -o json"
            )
            if result.status == ToolStatus.SUCCESS:
                import json
                data = json.loads(result.output)
                return data.get("items", [])
            return []

        try:
            ns = namespace or self.namespace
            deployments = self.apps_v1.list_namespaced_deployment(namespace=ns)
            return [
                {
                    "name": dep.metadata.name,
                    "namespace": dep.metadata.namespace,
                    "replicas": dep.status.replicas,
                    "ready_replicas": dep.status.ready_replicas,
                    "available_replicas": dep.status.available_replicas,
                }
                for dep in deployments.items
            ]
        except ApiException as e:
            logger.error(f"Failed to get deployments: {e}")
            return []

    async def get_services(
        self, namespace: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of services.
        
        Args:
            namespace: Namespace to query
            
        Returns:
            List of service dictionaries
        """
        if not self.use_python_client:
            result = await self.execute(
                f"get services -n {namespace or self.namespace} -o json"
            )
            if result.status == ToolStatus.SUCCESS:
                import json
                data = json.loads(result.output)
                return data.get("items", [])
            return []

        try:
            ns = namespace or self.namespace
            services = self.core_v1.list_namespaced_service(namespace=ns)
            return [
                {
                    "name": svc.metadata.name,
                    "namespace": svc.metadata.namespace,
                    "type": svc.spec.type,
                    "cluster_ip": svc.spec.cluster_ip,
                    "ports": [
                        {"port": p.port, "protocol": p.protocol, "name": p.name}
                        for p in (svc.spec.ports or [])
                    ],
                }
                for svc in services.items
            ]
        except ApiException as e:
            logger.error(f"Failed to get services: {e}")
            return []

    async def get_pod_logs(
        self, pod_name: str, namespace: Optional[str] = None, tail_lines: int = 100
    ) -> str:
        """Get logs from a pod.
        
        Args:
            pod_name: Name of the pod
            namespace: Namespace
            tail_lines: Number of lines to tail
            
        Returns:
            Pod logs as string
        """
        if not self.use_python_client:
            result = await self.execute(
                f"logs {pod_name} -n {namespace or self.namespace} --tail={tail_lines}"
            )
            return result.output if result.status == ToolStatus.SUCCESS else ""

        try:
            ns = namespace or self.namespace
            logs = self.core_v1.read_namespaced_pod_log(
                name=pod_name, namespace=ns, tail_lines=tail_lines
            )
            return logs
        except ApiException as e:
            logger.error(f"Failed to get pod logs: {e}")
            return f"Error: {e}"

    async def scale_deployment(
        self, deployment_name: str, replicas: int, namespace: Optional[str] = None
    ) -> ToolResult:
        """Scale a deployment.
        
        Args:
            deployment_name: Name of deployment
            replicas: Number of replicas
            namespace: Namespace
            
        Returns:
            ToolResult
        """
        start_time = time.time()
        
        if self.dry_run:
            return self._create_result(
                ToolStatus.SUCCESS,
                f"[DRY RUN] Would scale {deployment_name} to {replicas} replicas",
                execution_time=0.0,
                metadata={"dry_run": True},
            )

        if not self.use_python_client:
            return await self.execute(
                f"scale deployment {deployment_name} --replicas={replicas} -n {namespace or self.namespace}"
            )

        try:
            ns = namespace or self.namespace
            # Patch the deployment
            body = {"spec": {"replicas": replicas}}
            self.apps_v1.patch_namespaced_deployment_scale(
                name=deployment_name, namespace=ns, body=body
            )
            
            execution_time = time.time() - start_time
            logger.info(
                f"Scaled deployment {deployment_name} to {replicas} replicas in {ns}"
            )
            
            return self._create_result(
                ToolStatus.SUCCESS,
                f"Deployment {deployment_name} scaled to {replicas} replicas",
                execution_time=execution_time,
                metadata={
                    "deployment": deployment_name,
                    "replicas": replicas,
                    "namespace": ns,
                },
            )
        except ApiException as e:
            execution_time = time.time() - start_time
            logger.error(f"Failed to scale deployment: {e}")
            return self._create_result(
                ToolStatus.FAILED,
                "",
                error=str(e),
                execution_time=execution_time,
            )

    async def apply_manifest(self, manifest_path: str) -> ToolResult:
        """Apply a Kubernetes manifest.
        
        Args:
            manifest_path: Path to manifest file
            
        Returns:
            ToolResult
        """
        # Use kubectl for apply (Python client doesn't support this well)
        return await self.execute(f"apply -f {manifest_path}")

    async def delete_resource(
        self,
        resource_type: str,
        resource_name: str,
        namespace: Optional[str] = None,
    ) -> ToolResult:
        """Delete a Kubernetes resource.
        
        Args:
            resource_type: Type of resource (pod, deployment, etc.)
            resource_name: Name of resource
            namespace: Namespace
            
        Returns:
            ToolResult
        """
        ns = namespace or self.namespace
        return await self.execute(
            f"delete {resource_type} {resource_name} -n {ns}"
        )

    def __del__(self):
        """Cleanup temporary kubeconfig file."""
        if self._temp_kubeconfig and os.path.exists(self._temp_kubeconfig.name):
            try:
                os.unlink(self._temp_kubeconfig.name)
            except OSError:
                pass
