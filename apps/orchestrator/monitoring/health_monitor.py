"""Proactive health monitoring for Linux servers."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class HealthCheck:
    """Health check configuration."""

    name: str
    check_function: Callable
    interval_seconds: int
    threshold_warning: float
    threshold_critical: float
    enabled: bool = True
    last_run: Optional[datetime] = None
    last_result: Optional[Dict[str, Any]] = None


@dataclass
class HealthAlert:
    """Health alert."""

    severity: str  # info, warning, critical
    check_name: str
    message: str
    value: Any
    threshold: float
    timestamp: datetime
    acknowledged: bool = False
    auto_remediate: bool = False


class ProactiveHealthMonitor:
    """Proactive health monitoring with auto-remediation."""

    def __init__(self, ssh_executor, notification_callback: Optional[Callable] = None):
        self.ssh = ssh_executor
        self.notification_callback = notification_callback

        # Health checks
        self.checks: List[HealthCheck] = []

        # Alerts
        self.active_alerts: List[HealthAlert] = []
        self.alert_history: List[HealthAlert] = []

        # Monitoring state
        self.running = False
        self.monitor_task = None

        # Initialize default checks
        self._init_default_checks()

    def _init_default_checks(self):
        """Initialize default health checks."""
        self.add_check(
            name="memory_usage",
            check_function=self._check_memory,
            interval_seconds=60,
            threshold_warning=80.0,
            threshold_critical=90.0,
        )

        self.add_check(
            name="disk_usage",
            check_function=self._check_disk,
            interval_seconds=300,
            threshold_warning=80.0,
            threshold_critical=90.0,
        )

        self.add_check(
            name="cpu_load",
            check_function=self._check_cpu_load,
            interval_seconds=60,
            threshold_warning=2.0,  # Multiplier of CPU count
            threshold_critical=3.0,
        )

        self.add_check(
            name="failed_services",
            check_function=self._check_failed_services,
            interval_seconds=120,
            threshold_warning=1,
            threshold_critical=3,
        )

        self.add_check(
            name="recent_errors",
            check_function=self._check_recent_errors,
            interval_seconds=180,
            threshold_warning=10,
            threshold_critical=50,
        )

    def add_check(
        self,
        name: str,
        check_function: Callable,
        interval_seconds: int,
        threshold_warning: float,
        threshold_critical: float,
    ):
        """Add a custom health check."""
        check = HealthCheck(
            name=name,
            check_function=check_function,
            interval_seconds=interval_seconds,
            threshold_warning=threshold_warning,
            threshold_critical=threshold_critical,
        )

        self.checks.append(check)
        logger.info(f"Added health check: {name}")

    async def start(self):
        """Start monitoring."""
        if self.running:
            logger.warning("Health monitor already running")
            return

        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Proactive health monitor started")

    async def stop(self):
        """Stop monitoring."""
        self.running = False

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Proactive health monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Run all checks that are due
                for check in self.checks:
                    if not check.enabled:
                        continue

                    # Check if it's time to run
                    now = datetime.utcnow()
                    if check.last_run is None or (
                        now - check.last_run
                    ).total_seconds() >= check.interval_seconds:
                        await self._run_check(check)

                # Wait before next iteration
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
                await asyncio.sleep(30)

    async def _run_check(self, check: HealthCheck):
        """Run a single health check."""
        try:
            logger.debug(f"Running health check: {check.name}")

            # Execute check function
            result = await check.check_function()

            check.last_run = datetime.utcnow()
            check.last_result = result

            # Evaluate result
            await self._evaluate_result(check, result)

        except Exception as e:
            logger.error(f"Health check {check.name} failed: {e}")

    async def _evaluate_result(self, check: HealthCheck, result: Dict[str, Any]):
        """Evaluate check result and create alerts if needed."""
        value = result.get("value")
        if value is None:
            return

        # Determine severity
        severity = None
        if value >= check.threshold_critical:
            severity = "critical"
        elif value >= check.threshold_warning:
            severity = "warning"

        # Create alert if needed
        if severity:
            alert = HealthAlert(
                severity=severity,
                check_name=check.name,
                message=result.get("message", f"{check.name} threshold exceeded"),
                value=value,
                threshold=(
                    check.threshold_critical
                    if severity == "critical"
                    else check.threshold_warning
                ),
                timestamp=datetime.utcnow(),
                auto_remediate=result.get("auto_remediate", False),
            )

            await self._handle_alert(alert)

    async def _handle_alert(self, alert: HealthAlert):
        """Handle a health alert."""
        # Check if similar alert already exists
        existing = next(
            (a for a in self.active_alerts if a.check_name == alert.check_name),
            None,
        )

        if existing:
            # Update existing alert
            existing.value = alert.value
            existing.timestamp = alert.timestamp
            logger.debug(f"Updated existing alert: {alert.check_name}")
        else:
            # New alert
            self.active_alerts.append(alert)
            self.alert_history.append(alert)
            logger.warning(
                f"New {alert.severity} alert: {alert.check_name} - {alert.message}"
            )

            # Send notification
            if self.notification_callback:
                await self.notification_callback(alert)

            # Auto-remediate if enabled
            if alert.auto_remediate:
                await self._auto_remediate(alert)

    async def _auto_remediate(self, alert: HealthAlert):
        """Attempt automatic remediation."""
        logger.info(f"Attempting auto-remediation for: {alert.check_name}")

        try:
            if alert.check_name == "memory_usage":
                await self._remediate_memory()
            elif alert.check_name == "disk_usage":
                await self._remediate_disk()
            elif alert.check_name == "failed_services":
                await self._remediate_services()

        except Exception as e:
            logger.error(f"Auto-remediation failed for {alert.check_name}: {e}")

    # Health check implementations
    async def _check_memory(self) -> Dict[str, Any]:
        """Check memory usage."""
        result = await self.ssh.execute("free | grep Mem: | awk '{print ($3/$2) * 100}'")

        if result.output:
            try:
                usage_percent = float(result.output.strip())
                return {
                    "value": usage_percent,
                    "message": f"Memory usage: {usage_percent:.1f}%",
                    "auto_remediate": usage_percent >= 95.0,
                }
            except:
                pass

        return {"value": 0.0, "message": "Could not check memory"}

    async def _check_disk(self) -> Dict[str, Any]:
        """Check disk usage."""
        result = await self.ssh.execute(
            "df -h / | tail -1 | awk '{print $5}' | sed 's/%//'"
        )

        if result.output:
            try:
                usage_percent = float(result.output.strip())
                return {
                    "value": usage_percent,
                    "message": f"Disk usage: {usage_percent:.1f}%",
                    "auto_remediate": usage_percent >= 95.0,
                }
            except:
                pass

        return {"value": 0.0, "message": "Could not check disk"}

    async def _check_cpu_load(self) -> Dict[str, Any]:
        """Check CPU load average."""
        # Get CPU count
        cpu_result = await self.ssh.execute("nproc")
        cpu_count = int(cpu_result.output.strip()) if cpu_result.output else 1

        # Get load average
        load_result = await self.ssh.execute("cat /proc/loadavg | awk '{print $1}'")

        if load_result.output:
            try:
                load_1min = float(load_result.output.strip())
                load_per_cpu = load_1min / cpu_count

                return {
                    "value": load_per_cpu,
                    "message": f"Load: {load_1min:.2f} ({load_per_cpu:.2f} per CPU)",
                }
            except:
                pass

        return {"value": 0.0, "message": "Could not check CPU load"}

    async def _check_failed_services(self) -> Dict[str, Any]:
        """Check for failed systemd services."""
        result = await self.ssh.execute(
            "systemctl list-units --state=failed --no-pager | grep -c failed || echo 0"
        )

        if result.output:
            try:
                failed_count = int(result.output.strip())
                return {
                    "value": failed_count,
                    "message": f"Failed services: {failed_count}",
                    "auto_remediate": True,
                }
            except:
                pass

        return {"value": 0, "message": "Could not check services"}

    async def _check_recent_errors(self) -> Dict[str, Any]:
        """Check for recent errors in system logs."""
        result = await self.ssh.execute(
            "journalctl --since '10 minutes ago' --priority=err | wc -l"
        )

        if result.output:
            try:
                error_count = int(result.output.strip())
                return {
                    "value": error_count,
                    "message": f"Recent errors: {error_count}",
                }
            except:
                pass

        return {"value": 0, "message": "Could not check errors"}

    # Auto-remediation implementations
    async def _remediate_memory(self):
        """Attempt to free memory."""
        logger.info("Attempting memory cleanup...")

        # Drop caches (requires sudo)
        await self.ssh.execute("sync", use_sudo=True)
        await self.ssh.execute("echo 3 > /proc/sys/vm/drop_caches", use_sudo=True)

    async def _remediate_disk(self):
        """Attempt to free disk space."""
        logger.info("Attempting disk cleanup...")

        # Clean package manager cache
        await self.ssh.execute("apt-get clean || yum clean all", use_sudo=True)

        # Clean old logs
        await self.ssh.execute(
            "find /var/log -type f -name '*.gz' -mtime +30 -delete",
            use_sudo=True,
        )

    async def _remediate_services(self):
        """Attempt to restart failed services."""
        logger.info("Attempting to restart failed services...")

        # Get list of failed services
        result = await self.ssh.execute(
            "systemctl list-units --state=failed --no-pager | grep failed | awk '{print $1}'"
        )

        if result.output:
            services = result.output.strip().split("\n")
            for service in services[:3]:  # Limit to 3 services
                if service:
                    logger.info(f"Restarting service: {service}")
                    await self.ssh.execute(f"systemctl restart {service}", use_sudo=True)

    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            "running": self.running,
            "checks_count": len(self.checks),
            "active_alerts": len(self.active_alerts),
            "critical_alerts": len([a for a in self.active_alerts if a.severity == "critical"]),
            "warning_alerts": len([a for a in self.active_alerts if a.severity == "warning"]),
            "last_check_times": {
                check.name: check.last_run.isoformat() if check.last_run else None
                for check in self.checks
            },
        }

    def get_alerts(self, severity: Optional[str] = None) -> List[HealthAlert]:
        """Get active alerts, optionally filtered by severity."""
        if severity:
            return [a for a in self.active_alerts if a.severity == severity]
        return self.active_alerts

    def acknowledge_alert(self, check_name: str):
        """Acknowledge an alert."""
        for alert in self.active_alerts:
            if alert.check_name == check_name:
                alert.acknowledged = True
                logger.info(f"Alert acknowledged: {check_name}")
