"""System monitoring and health checks."""

import asyncio
import psutil
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health status information."""

    component: str
    status: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    response_time: Optional[float] = None


@dataclass
class SystemMetrics:
    """System metrics information."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_bytes: int
    memory_total_bytes: int
    disk_usage_percent: float
    disk_used_bytes: int
    disk_total_bytes: int
    network_io: Dict[str, int]
    process_count: int


class HealthMonitor:
    """Monitor health of system components."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.health_checks: Dict[str, callable] = {}
        self.health_history: List[HealthStatus] = []
        self.max_history = config.get("max_history", 1000)
        self.check_interval = config.get("check_interval", 30)
        self.timeout = config.get("timeout", 10)
        self.running = False
        self._task = None

    def register_health_check(self, name: str, check_func: callable):
        """Register a health check function."""
        self.health_checks[name] = check_func

    async def start_monitoring(self):
        """Start health monitoring."""
        if self.running:
            return

        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitoring started")

    async def stop_monitoring(self):
        """Stop health monitoring."""
        if not self.running:
            return

        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Health monitoring stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                await self._run_health_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(self.check_interval)

    async def _run_health_checks(self):
        """Run all registered health checks."""
        for name, check_func in self.health_checks.items():
            try:
                start_time = time.time()

                # Run health check with timeout
                result = await asyncio.wait_for(
                    self._run_single_check(name, check_func), timeout=self.timeout
                )

                response_time = time.time() - start_time
                result.response_time = response_time

                self.health_history.append(result)

                # Keep only recent history
                if len(self.health_history) > self.max_history:
                    self.health_history = self.health_history[-self.max_history :]

            except asyncio.TimeoutError:
                logger.warning(f"Health check {name} timed out")
                self.health_history.append(
                    HealthStatus(
                        component=name,
                        status="timeout",
                        message=f"Health check timed out after {self.timeout} seconds",
                        details={},
                        timestamp=datetime.now(),
                        response_time=self.timeout,
                    )
                )
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                self.health_history.append(
                    HealthStatus(
                        component=name,
                        status="error",
                        message=f"Health check failed: {str(e)}",
                        details={"error": str(e)},
                        timestamp=datetime.now(),
                    )
                )

    async def _run_single_check(self, name: str, check_func: callable) -> HealthStatus:
        """Run a single health check."""
        try:
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()

            if isinstance(result, HealthStatus):
                return result
            elif isinstance(result, dict):
                return HealthStatus(
                    component=name,
                    status=result.get("status", "unknown"),
                    message=result.get("message", ""),
                    details=result.get("details", {}),
                    timestamp=datetime.now(),
                )
            else:
                return HealthStatus(
                    component=name,
                    status="healthy" if result else "unhealthy",
                    message="Health check completed",
                    details={"result": result},
                    timestamp=datetime.now(),
                )
        except Exception as e:
            return HealthStatus(
                component=name,
                status="error",
                message=f"Health check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
            )

    def get_health_status(self, component: Optional[str] = None) -> List[HealthStatus]:
        """Get health status for components."""
        if component:
            return [h for h in self.health_history if h.component == component]
        else:
            return self.health_history.copy()

    def get_latest_health_status(
        self, component: Optional[str] = None
    ) -> Optional[HealthStatus]:
        """Get latest health status for a component."""
        statuses = self.get_health_status(component)
        if statuses:
            return max(statuses, key=lambda x: x.timestamp)
        return None

    def is_healthy(self, component: Optional[str] = None) -> bool:
        """Check if component is healthy."""
        latest = self.get_latest_health_status(component)
        if not latest:
            return False

        return latest.status in ["healthy", "ok", "up"]


class SystemMonitor:
    """Monitor system resources and performance."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics_history: List[SystemMetrics] = []
        self.max_history = config.get("max_history", 1000)
        self.collect_interval = config.get("collect_interval", 60)
        self.running = False
        self._task = None

    async def start_monitoring(self):
        """Start system monitoring."""
        if self.running:
            return

        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("System monitoring started")

    async def stop_monitoring(self):
        """Stop system monitoring."""
        if not self.running:
            return

        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("System monitoring stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                metrics = await self._collect_system_metrics()
                self.metrics_history.append(metrics)

                # Keep only recent history
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history = self.metrics_history[-self.max_history :]

                await asyncio.sleep(self.collect_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                await asyncio.sleep(self.collect_interval)

    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system metrics."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_bytes = memory.used
        memory_total_bytes = memory.total

        # Disk usage
        disk = psutil.disk_usage("/")
        disk_usage_percent = (disk.used / disk.total) * 100
        disk_used_bytes = disk.used
        disk_total_bytes = disk.total

        # Network I/O
        network_io = psutil.net_io_counters()
        network_io_dict = {
            "bytes_sent": network_io.bytes_sent,
            "bytes_recv": network_io.bytes_recv,
            "packets_sent": network_io.packets_sent,
            "packets_recv": network_io.packets_recv,
        }

        # Process count
        process_count = len(psutil.pids())

        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_bytes=memory_used_bytes,
            memory_total_bytes=memory_total_bytes,
            disk_usage_percent=disk_usage_percent,
            disk_used_bytes=disk_used_bytes,
            disk_total_bytes=disk_total_bytes,
            network_io=network_io_dict,
            process_count=process_count,
        )

    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        """Get latest system metrics."""
        if self.metrics_history:
            return self.metrics_history[-1]
        return None

    def get_metrics_history(self, hours: int = 24) -> List[SystemMetrics]:
        """Get system metrics history for the specified hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]

    def get_average_metrics(self, hours: int = 1) -> Optional[SystemMetrics]:
        """Get average system metrics for the specified hours."""
        metrics = self.get_metrics_history(hours)
        if not metrics:
            return None

        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=sum(m.cpu_percent for m in metrics) / len(metrics),
            memory_percent=sum(m.memory_percent for m in metrics) / len(metrics),
            memory_used_bytes=sum(m.memory_used_bytes for m in metrics) // len(metrics),
            memory_total_bytes=metrics[0].memory_total_bytes,  # Total doesn't change
            disk_usage_percent=sum(m.disk_usage_percent for m in metrics)
            / len(metrics),
            disk_used_bytes=sum(m.disk_used_bytes for m in metrics) // len(metrics),
            disk_total_bytes=metrics[0].disk_total_bytes,  # Total doesn't change
            network_io={
                "bytes_sent": sum(m.network_io["bytes_sent"] for m in metrics)
                // len(metrics),
                "bytes_recv": sum(m.network_io["bytes_recv"] for m in metrics)
                // len(metrics),
                "packets_sent": sum(m.network_io["packets_sent"] for m in metrics)
                // len(metrics),
                "packets_recv": sum(m.network_io["packets_recv"] for m in metrics)
                // len(metrics),
            },
            process_count=sum(m.process_count for m in metrics) // len(metrics),
        )

    def is_system_healthy(self) -> bool:
        """Check if system is healthy based on metrics."""
        latest = self.get_latest_metrics()
        if not latest:
            return False

        # Check CPU usage
        if latest.cpu_percent > 90:
            return False

        # Check memory usage
        if latest.memory_percent > 90:
            return False

        # Check disk usage
        if latest.disk_usage_percent > 90:
            return False

        return True



