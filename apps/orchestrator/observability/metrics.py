"""Metrics collection and Prometheus integration."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""

    name: str
    value: float
    labels: Dict[str, str]
    timestamp: datetime


class MetricsCollector:
    """Base class for metrics collection."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics: Dict[str, List[MetricPoint]] = {}
        self.enabled = config.get("enabled", True)

    def increment_counter(
        self, name: str, labels: Optional[Dict[str, str]] = None, value: float = 1.0
    ):
        """Increment a counter metric."""
        if not self.enabled:
            return

        labels = labels or {}
        self._add_metric(name, value, labels)

    def set_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ):
        """Set a gauge metric value."""
        if not self.enabled:
            return

        labels = labels or {}
        self._add_metric(name, value, labels)

    def observe_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ):
        """Observe a histogram metric."""
        if not self.enabled:
            return

        labels = labels or {}
        self._add_metric(name, value, labels)

    def _add_metric(self, name: str, value: float, labels: Dict[str, str]):
        """Add a metric point."""
        if name not in self.metrics:
            self.metrics[name] = []

        self.metrics[name].append(
            MetricPoint(name=name, value=value, labels=labels, timestamp=datetime.now())
        )

    def get_metrics(self) -> Dict[str, List[MetricPoint]]:
        """Get all collected metrics."""
        return self.metrics.copy()

    def clear_metrics(self):
        """Clear all collected metrics."""
        self.metrics.clear()


class PrometheusMetrics(MetricsCollector):
    """Prometheus-compatible metrics collector."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.metric_types = {
            "counter": {},
            "gauge": {},
            "histogram": {},
        }
        self._initialize_metrics()

    def _initialize_metrics(self):
        """Initialize standard metrics."""
        # LLM metrics
        self.metric_types["counter"]["llm_requests_total"] = {
            "help": "Total number of LLM requests",
            "labels": ["provider", "model", "status"],
        }

        self.metric_types["histogram"]["llm_request_duration_seconds"] = {
            "help": "LLM request duration in seconds",
            "labels": ["provider", "model"],
            "buckets": [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
        }

        self.metric_types["counter"]["llm_tokens_total"] = {
            "help": "Total number of LLM tokens",
            "labels": ["provider", "model", "type"],
        }

        # Task metrics
        self.metric_types["counter"]["tasks_total"] = {
            "help": "Total number of tasks",
            "labels": ["status", "environment", "user_role"],
        }

        self.metric_types["histogram"]["task_duration_seconds"] = {
            "help": "Task duration in seconds",
            "labels": ["environment", "user_role"],
            "buckets": [1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0],
        }

        self.metric_types["gauge"]["active_tasks"] = {
            "help": "Number of active tasks",
            "labels": ["environment"],
        }

        # Security metrics
        self.metric_types["counter"]["security_violations_total"] = {
            "help": "Total number of security violations",
            "labels": ["violation_type", "severity", "environment"],
        }

        self.metric_types["counter"]["approvals_total"] = {
            "help": "Total number of approvals",
            "labels": ["status", "user_role", "environment"],
        }

        # System metrics
        self.metric_types["gauge"]["system_memory_usage_bytes"] = {
            "help": "System memory usage in bytes",
            "labels": [],
        }

        self.metric_types["gauge"]["system_cpu_usage_percent"] = {
            "help": "System CPU usage percentage",
            "labels": [],
        }

    def increment_llm_requests(self, provider: str, model: str, status: str):
        """Increment LLM requests counter."""
        self.increment_counter(
            "llm_requests_total",
            {"provider": provider, "model": model, "status": status},
        )

    def observe_llm_duration(self, provider: str, model: str, duration: float):
        """Observe LLM request duration."""
        self.observe_histogram(
            "llm_request_duration_seconds",
            duration,
            {"provider": provider, "model": model},
        )

    def increment_llm_tokens(
        self, provider: str, model: str, token_type: str, count: int
    ):
        """Increment LLM tokens counter."""
        self.increment_counter(
            "llm_tokens_total",
            {"provider": provider, "model": model, "type": token_type},
            count,
        )

    def increment_tasks(self, status: str, environment: str, user_role: str):
        """Increment tasks counter."""
        self.increment_counter(
            "tasks_total",
            {"status": status, "environment": environment, "user_role": user_role},
        )

    def observe_task_duration(self, environment: str, user_role: str, duration: float):
        """Observe task duration."""
        self.observe_histogram(
            "task_duration_seconds",
            duration,
            {"environment": environment, "user_role": user_role},
        )

    def set_active_tasks(self, environment: str, count: int):
        """Set active tasks gauge."""
        self.set_gauge("active_tasks", count, {"environment": environment})

    def increment_security_violations(
        self, violation_type: str, severity: str, environment: str
    ):
        """Increment security violations counter."""
        self.increment_counter(
            "security_violations_total",
            {
                "violation_type": violation_type,
                "severity": severity,
                "environment": environment,
            },
        )

    def increment_approvals(self, status: str, user_role: str, environment: str):
        """Increment approvals counter."""
        self.increment_counter(
            "approvals_total",
            {"status": status, "user_role": user_role, "environment": environment},
        )

    def set_system_memory_usage(self, usage_bytes: int):
        """Set system memory usage gauge."""
        self.set_gauge("system_memory_usage_bytes", usage_bytes)

    def set_system_cpu_usage(self, usage_percent: float):
        """Set system CPU usage gauge."""
        self.set_gauge("system_cpu_usage_percent", usage_percent)

    def format_prometheus(self) -> str:
        """Format metrics in Prometheus format."""
        if not self.enabled:
            return ""

        lines = []

        for metric_name, metric_points in self.metrics.items():
            if not metric_points:
                continue

            # Get metric type info
            metric_type_info = None
            for metric_type, metrics in self.metric_types.items():
                if metric_name in metrics:
                    metric_type_info = metrics[metric_name]
                    break

            if not metric_type_info:
                continue

            # Add help and type comments
            lines.append(f"# HELP {metric_name} {metric_type_info['help']}")
            lines.append(
                f"# TYPE {metric_name} {metric_type_info.get('type', 'counter')}"
            )

            # Add metric points
            for point in metric_points:
                labels_str = ""
                if point.labels:
                    label_pairs = [f'{k}="{v}"' for k, v in point.labels.items()]
                    labels_str = "{" + ",".join(label_pairs) + "}"

                lines.append(f"{metric_name}{labels_str} {point.value}")

        return "\n".join(lines)

    async def health_check(self) -> bool:
        """Check if metrics collector is healthy."""
        try:
            # Test metric collection
            self.increment_counter("health_check", {"component": "prometheus_metrics"})
            return True
        except Exception as e:
            logger.error(f"Prometheus metrics health check failed: {e}")
            return False




