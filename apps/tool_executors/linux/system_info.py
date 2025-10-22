"""System information collector for Linux servers."""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SystemInfo:
    """System information data."""

    hostname: str
    os: str
    kernel: str
    uptime: str
    cpu_count: int
    cpu_model: str
    memory_total: str
    memory_used: str
    memory_free: str
    memory_percent: float
    disk_usage: Dict[str, Dict[str, Any]]
    load_average: tuple
    processes_count: int


class SystemInfoCollector:
    """Collects comprehensive system information from Linux servers."""

    def __init__(self, ssh_executor):
        self.ssh = ssh_executor

    async def collect_all(self) -> SystemInfo:
        """Collect all system information."""
        logger.info("Collecting system information...")

        # Run all collection commands in parallel
        hostname = await self._get_hostname()
        os_info = await self._get_os_info()
        kernel = await self._get_kernel_version()
        uptime = await self._get_uptime()
        cpu_info = await self._get_cpu_info()
        memory_info = await self._get_memory_info()
        disk_usage = await self._get_disk_usage()
        load_avg = await self._get_load_average()
        processes = await self._get_process_count()

        return SystemInfo(
            hostname=hostname,
            os=os_info,
            kernel=kernel,
            uptime=uptime,
            cpu_count=cpu_info["count"],
            cpu_model=cpu_info["model"],
            memory_total=memory_info["total"],
            memory_used=memory_info["used"],
            memory_free=memory_info["free"],
            memory_percent=memory_info["percent"],
            disk_usage=disk_usage,
            load_average=load_avg,
            processes_count=processes,
        )

    async def _get_hostname(self) -> str:
        """Get hostname."""
        result = await self.ssh.execute("hostname")
        return result.output.strip() if result.output else "unknown"

    async def _get_os_info(self) -> str:
        """Get OS information."""
        # Try multiple sources
        commands = [
            "cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"'",
            "lsb_release -d | cut -f2",
            "cat /etc/redhat-release",
        ]

        for cmd in commands:
            result = await self.ssh.execute(cmd)
            if result.status.value == "success" and result.output:
                return result.output.strip()

        return "Unknown Linux"

    async def _get_kernel_version(self) -> str:
        """Get kernel version."""
        result = await self.ssh.execute("uname -r")
        return result.output.strip() if result.output else "unknown"

    async def _get_uptime(self) -> str:
        """Get system uptime."""
        result = await self.ssh.execute("uptime -p")
        return result.output.strip() if result.output else "unknown"

    async def _get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU information."""
        # CPU count
        count_result = await self.ssh.execute("nproc")
        cpu_count = int(count_result.output.strip()) if count_result.output else 0

        # CPU model
        model_result = await self.ssh.execute(
            "cat /proc/cpuinfo | grep 'model name' | head -1 | cut -d: -f2"
        )
        cpu_model = model_result.output.strip() if model_result.output else "Unknown"

        return {"count": cpu_count, "model": cpu_model}

    async def _get_memory_info(self) -> Dict[str, Any]:
        """Get memory information."""
        result = await self.ssh.execute("free -h | grep Mem:")

        if not result.output:
            return {"total": "0", "used": "0", "free": "0", "percent": 0.0}

        parts = result.output.split()
        total = parts[1] if len(parts) > 1 else "0"
        used = parts[2] if len(parts) > 2 else "0"
        free = parts[3] if len(parts) > 3 else "0"

        # Calculate percentage
        try:
            total_bytes = self._parse_memory_size(total)
            used_bytes = self._parse_memory_size(used)
            percent = (used_bytes / total_bytes * 100) if total_bytes > 0 else 0.0
        except:
            percent = 0.0

        return {
            "total": total,
            "used": used,
            "free": free,
            "percent": round(percent, 2),
        }

    def _parse_memory_size(self, size_str: str) -> float:
        """Parse memory size string to bytes."""
        multipliers = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}

        if not size_str:
            return 0.0

        # Extract number and unit
        number = ""
        unit = ""
        for char in size_str:
            if char.isdigit() or char == ".":
                number += char
            elif char.isalpha():
                unit = char.upper()
                break

        value = float(number) if number else 0.0
        multiplier = multipliers.get(unit, 1)

        return value * multiplier

    async def _get_disk_usage(self) -> Dict[str, Dict[str, Any]]:
        """Get disk usage for all mounted filesystems."""
        result = await self.ssh.execute("df -h | grep -v tmpfs | tail -n +2")

        if not result.output:
            return {}

        disk_info = {}
        for line in result.output.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 6:
                filesystem = parts[0]
                size = parts[1]
                used = parts[2]
                available = parts[3]
                percent = parts[4].replace("%", "")
                mount = parts[5]

                disk_info[mount] = {
                    "filesystem": filesystem,
                    "size": size,
                    "used": used,
                    "available": available,
                    "percent": float(percent) if percent.isdigit() else 0.0,
                }

        return disk_info

    async def _get_load_average(self) -> tuple:
        """Get system load average."""
        result = await self.ssh.execute("cat /proc/loadavg")

        if not result.output:
            return (0.0, 0.0, 0.0)

        parts = result.output.split()
        try:
            return (float(parts[0]), float(parts[1]), float(parts[2]))
        except:
            return (0.0, 0.0, 0.0)

    async def _get_process_count(self) -> int:
        """Get total process count."""
        result = await self.ssh.execute("ps aux | wc -l")

        if result.output:
            try:
                return int(result.output.strip()) - 1  # Subtract header
            except:
                pass

        return 0

    async def check_health(self) -> Dict[str, Any]:
        """Check system health based on collected info."""
        info = await self.collect_all()

        health = {
            "status": "healthy",
            "issues": [],
            "warnings": [],
        }

        # Check memory
        if info.memory_percent > 90:
            health["status"] = "critical"
            health["issues"].append(f"Memory usage critical: {info.memory_percent}%")
        elif info.memory_percent > 80:
            health["status"] = "warning"
            health["warnings"].append(f"Memory usage high: {info.memory_percent}%")

        # Check disk
        for mount, disk in info.disk_usage.items():
            if disk["percent"] > 90:
                health["status"] = "critical"
                health["issues"].append(
                    f"Disk {mount} usage critical: {disk['percent']}%"
                )
            elif disk["percent"] > 80:
                if health["status"] == "healthy":
                    health["status"] = "warning"
                health["warnings"].append(f"Disk {mount} usage high: {disk['percent']}%")

        # Check load average (compared to CPU count)
        load_1min = info.load_average[0]
        if load_1min > info.cpu_count * 2:
            health["status"] = "critical"
            health["issues"].append(
                f"Load average very high: {load_1min} (CPUs: {info.cpu_count})"
            )
        elif load_1min > info.cpu_count * 1.5:
            if health["status"] == "healthy":
                health["status"] = "warning"
            health["warnings"].append(
                f"Load average high: {load_1min} (CPUs: {info.cpu_count})"
            )

        return health

    def format_summary(self, info: SystemInfo) -> str:
        """Format system info as human-readable summary."""
        summary = f"""
╔══════════════════════════════════════════════════════╗
║           System Information Summary                  ║
╠══════════════════════════════════════════════════════╣
║ Hostname:      {info.hostname:<35} ║
║ OS:            {info.os:<35} ║
║ Kernel:        {info.kernel:<35} ║
║ Uptime:        {info.uptime:<35} ║
╠══════════════════════════════════════════════════════╣
║ CPU:           {info.cpu_count} cores - {info.cpu_model[:30]:<30} ║
║ Load Average:  {info.load_average[0]:.2f} / {info.load_average[1]:.2f} / {info.load_average[2]:.2f}                    ║
║ Processes:     {info.processes_count:<35} ║
╠══════════════════════════════════════════════════════╣
║ Memory Total:  {info.memory_total:<35} ║
║ Memory Used:   {info.memory_used} ({info.memory_percent}%)                         ║
║ Memory Free:   {info.memory_free:<35} ║
╠══════════════════════════════════════════════════════╣
║ Disk Usage:                                           ║
"""

        for mount, disk in info.disk_usage.items():
            summary += f"║   {mount:<10} {disk['used']}/{disk['size']} ({disk['percent']}%)          ║\n"

        summary += "╚══════════════════════════════════════════════════════╝"

        return summary
