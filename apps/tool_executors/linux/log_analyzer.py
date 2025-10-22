"""Intelligent log analyzer for Linux systems."""

import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """Single log entry."""

    timestamp: Optional[datetime]
    level: str
    service: str
    message: str
    raw: str


@dataclass
class LogAnalysis:
    """Log analysis results."""

    total_entries: int
    errors: List[LogEntry]
    warnings: List[LogEntry]
    patterns: Dict[str, int]
    top_errors: List[tuple]
    time_range: tuple
    summary: str


class LogAnalyzer:
    """Intelligent log analyzer with pattern recognition."""

    # Common log patterns
    SYSLOG_PATTERN = r"(?P<timestamp>\w+\s+\d+\s+\d+:\d+:\d+)\s+(?P<hostname>\S+)\s+(?P<service>\S+?)(\[(?P<pid>\d+)\])?: (?P<message>.*)"
    APACHE_PATTERN = r'(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] "(?P<request>[^"]+)" (?P<status>\d+) (?P<size>\S+)'
    NGINX_PATTERN = r'(?P<ip>\S+) - \S+ \[(?P<timestamp>[^\]]+)\] "(?P<request>[^"]+)" (?P<status>\d+) (?P<size>\S+)'

    # Error keywords
    ERROR_KEYWORDS = [
        "error",
        "fail",
        "exception",
        "critical",
        "fatal",
        "panic",
        "segfault",
        "killed",
        "died",
    ]

    WARNING_KEYWORDS = ["warning", "warn", "deprecated", "timeout", "retry"]

    def __init__(self, ssh_executor):
        self.ssh = ssh_executor

    async def analyze_file(
        self,
        log_file: str,
        lines: int = 1000,
        filter_errors: bool = True,
    ) -> LogAnalysis:
        """Analyze a log file."""
        logger.info(f"Analyzing log file: {log_file}")

        # Read log file
        result = await self.ssh.execute(f"tail -n {lines} {log_file}")

        if not result.output:
            raise ValueError(f"Could not read log file: {log_file}")

        return self.analyze_text(result.output, filter_errors=filter_errors)

    def analyze_text(
        self,
        log_text: str,
        filter_errors: bool = True,
    ) -> LogAnalysis:
        """Analyze log text."""
        entries = self.parse_logs(log_text)

        # Filter errors and warnings
        errors = [e for e in entries if e.level == "ERROR"]
        warnings = [e for e in entries if e.level == "WARNING"]

        # Find common patterns
        patterns = self._find_patterns(errors if filter_errors else entries)

        # Get top errors
        top_errors = sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:10]

        # Get time range
        timestamps = [e.timestamp for e in entries if e.timestamp]
        time_range = (min(timestamps), max(timestamps)) if timestamps else (None, None)

        # Generate summary
        summary = self._generate_summary(
            len(entries), len(errors), len(warnings), top_errors
        )

        return LogAnalysis(
            total_entries=len(entries),
            errors=errors,
            warnings=warnings,
            patterns=patterns,
            top_errors=top_errors,
            time_range=time_range,
            summary=summary,
        )

    def parse_logs(self, log_text: str) -> List[LogEntry]:
        """Parse log text into structured entries."""
        entries = []

        for line in log_text.strip().split("\n"):
            if not line.strip():
                continue

            entry = self._parse_line(line)
            if entry:
                entries.append(entry)

        return entries

    def _parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single log line."""
        # Try syslog format
        match = re.search(self.SYSLOG_PATTERN, line)
        if match:
            return self._parse_syslog(match, line)

        # Try Apache/Nginx format
        match = re.search(self.APACHE_PATTERN, line)
        if not match:
            match = re.search(self.NGINX_PATTERN, line)

        if match:
            return self._parse_web_log(match, line)

        # Fallback: generic parsing
        return self._parse_generic(line)

    def _parse_syslog(self, match: re.Match, raw: str) -> LogEntry:
        """Parse syslog format."""
        timestamp_str = match.group("timestamp")
        service = match.group("service")
        message = match.group("message")

        # Try to parse timestamp
        try:
            timestamp = datetime.strptime(
                timestamp_str, "%b %d %H:%M:%S"
            ).replace(year=datetime.now().year)
        except:
            timestamp = None

        # Determine level
        level = self._determine_level(message)

        return LogEntry(
            timestamp=timestamp,
            level=level,
            service=service,
            message=message,
            raw=raw,
        )

    def _parse_web_log(self, match: re.Match, raw: str) -> LogEntry:
        """Parse Apache/Nginx log format."""
        request = match.group("request")
        status = int(match.group("status"))

        # Determine level from status code
        if status >= 500:
            level = "ERROR"
        elif status >= 400:
            level = "WARNING"
        else:
            level = "INFO"

        return LogEntry(
            timestamp=None,  # Could parse but skipping for now
            level=level,
            service="web",
            message=f"{status} {request}",
            raw=raw,
        )

    def _parse_generic(self, line: str) -> LogEntry:
        """Generic log parsing."""
        level = self._determine_level(line)

        return LogEntry(
            timestamp=None,
            level=level,
            service="unknown",
            message=line,
            raw=line,
        )

    def _determine_level(self, text: str) -> str:
        """Determine log level from text."""
        text_lower = text.lower()

        for keyword in self.ERROR_KEYWORDS:
            if keyword in text_lower:
                return "ERROR"

        for keyword in self.WARNING_KEYWORDS:
            if keyword in text_lower:
                return "WARNING"

        return "INFO"

    def _find_patterns(self, entries: List[LogEntry]) -> Dict[str, int]:
        """Find common patterns in log entries."""
        patterns = {}

        for entry in entries:
            # Extract pattern by removing numbers and specific values
            pattern = re.sub(r'\d+', 'N', entry.message)
            pattern = re.sub(r'0x[0-9a-fA-F]+', '0xHEX', pattern)
            pattern = re.sub(r'/\S+', '/PATH', pattern)
            pattern = re.sub(r'\b([0-9]{1,3}\.){3}[0-9]{1,3}\b', 'IP', pattern)

            # Truncate long patterns
            if len(pattern) > 100:
                pattern = pattern[:100] + "..."

            patterns[pattern] = patterns.get(pattern, 0) + 1

        return patterns

    def _generate_summary(
        self,
        total: int,
        errors: int,
        warnings: int,
        top_errors: List[tuple],
    ) -> str:
        """Generate analysis summary."""
        summary = f"""
╔══════════════════════════════════════════════════════╗
║              Log Analysis Summary                     ║
╠══════════════════════════════════════════════════════╣
║ Total Entries:  {total:<38} ║
║ Errors:         {errors:<38} ║
║ Warnings:       {warnings:<38} ║
╠══════════════════════════════════════════════════════╣
║ Top Error Patterns:                                   ║
"""

        for i, (pattern, count) in enumerate(top_errors[:5], 1):
            pattern_short = pattern[:45] + "..." if len(pattern) > 45 else pattern
            summary += f"║ {i}. ({count}x) {pattern_short:<40} ║\n"

        summary += "╚══════════════════════════════════════════════════════╝"

        return summary

    async def find_errors_in_range(
        self,
        log_file: str,
        minutes_ago: int = 60,
    ) -> List[LogEntry]:
        """Find errors in the last N minutes."""
        # Use journalctl for systemd logs
        if log_file.startswith("journalctl:"):
            service = log_file.split(":")[1] if ":" in log_file else ""
            cmd = f"journalctl --since '{minutes_ago} minutes ago' --priority=err"
            if service:
                cmd += f" -u {service}"
        else:
            # For file-based logs, approximate by reading recent lines
            cmd = f"tail -n 10000 {log_file}"

        result = await self.ssh.execute(cmd)

        if not result.output:
            return []

        entries = self.parse_logs(result.output)
        return [e for e in entries if e.level == "ERROR"]

    async def search_pattern(
        self,
        log_file: str,
        pattern: str,
        context_lines: int = 3,
    ) -> List[str]:
        """Search for a pattern in logs with context."""
        cmd = f"grep -C {context_lines} -i '{pattern}' {log_file} | tail -n 100"
        result = await self.ssh.execute(cmd)

        if result.output:
            return result.output.strip().split("\n")

        return []

    async def get_service_logs(
        self,
        service_name: str,
        lines: int = 100,
    ) -> str:
        """Get logs for a systemd service."""
        cmd = f"journalctl -u {service_name} -n {lines} --no-pager"
        result = await self.ssh.execute(cmd)

        return result.output if result.output else ""

    async def monitor_log_realtime(
        self,
        log_file: str,
        duration_seconds: int = 30,
    ):
        """Monitor log file in real-time (streaming)."""
        cmd = f"timeout {duration_seconds} tail -f {log_file}"

        async for line in self.ssh.stream_execute(cmd):
            yield line
