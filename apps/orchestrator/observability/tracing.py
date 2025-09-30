"""Distributed tracing and OpenTelemetry integration."""

import uuid
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Span:
    """A tracing span."""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[float]
    tags: Dict[str, Any]
    logs: List[Dict[str, Any]]
    status: str = "started"


class TracingManager:
    """Manager for distributed tracing."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.service_name = config.get("service_name", "devops-agent")
        self.spans: List[Span] = []
        self.max_spans = config.get("max_spans", 10000)
        self.active_spans: Dict[str, Span] = {}

    def start_span(
        self,
        operation_name: str,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Start a new tracing span."""
        if not self.enabled:
            return ""

        span_id = str(uuid.uuid4())
        trace_id = parent_span_id or str(uuid.uuid4())

        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=datetime.now(),
            end_time=None,
            duration=None,
            tags=tags or {},
            logs=[],
        )

        self.active_spans[span_id] = span
        return span_id

    def finish_span(
        self,
        span_id: str,
        status: str = "completed",
        tags: Optional[Dict[str, Any]] = None,
    ):
        """Finish a tracing span."""
        if not self.enabled or span_id not in self.active_spans:
            return

        span = self.active_spans[span_id]
        span.end_time = datetime.now()
        span.duration = (span.end_time - span.start_time).total_seconds()
        span.status = status

        if tags:
            span.tags.update(tags)

        # Move to completed spans
        self.spans.append(span)
        del self.active_spans[span_id]

        # Keep only recent spans
        if len(self.spans) > self.max_spans:
            self.spans = self.spans[-self.max_spans :]

    def add_span_log(self, span_id: str, message: str, level: str = "info", **kwargs):
        """Add a log entry to a span."""
        if not self.enabled or span_id not in self.active_spans:
            return

        span = self.active_spans[span_id]
        span.logs.append(
            {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message,
                **kwargs,
            }
        )

    def add_span_tag(self, span_id: str, key: str, value: Any):
        """Add a tag to a span."""
        if not self.enabled or span_id not in self.active_spans:
            return

        span = self.active_spans[span_id]
        span.tags[key] = value

    @contextmanager
    def span(
        self,
        operation_name: str,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ):
        """Context manager for tracing spans."""
        span_id = self.start_span(operation_name, parent_span_id, tags)
        try:
            yield span_id
        except Exception as e:
            self.add_span_tag(span_id, "error", True)
            self.add_span_tag(span_id, "error.message", str(e))
            self.finish_span(span_id, "error")
            raise
        else:
            self.finish_span(span_id, "completed")

    def get_spans_by_trace(self, trace_id: str) -> List[Span]:
        """Get all spans for a trace."""
        return [span for span in self.spans if span.trace_id == trace_id]

    def get_spans_by_operation(self, operation_name: str) -> List[Span]:
        """Get all spans for an operation."""
        return [span for span in self.spans if span.operation_name == operation_name]

    def get_recent_spans(self, limit: int = 100) -> List[Span]:
        """Get recent spans."""
        return self.spans[-limit:]

    def get_span_statistics(self) -> Dict[str, Any]:
        """Get span statistics."""
        if not self.spans:
            return {}

        completed_spans = [span for span in self.spans if span.duration is not None]

        if not completed_spans:
            return {}

        durations = [span.duration for span in completed_spans]

        return {
            "total_spans": len(self.spans),
            "completed_spans": len(completed_spans),
            "active_spans": len(self.active_spans),
            "average_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "operations": {
                op: len([s for s in completed_spans if s.operation_name == op])
                for op in set(span.operation_name for span in completed_spans)
            },
        }


class OpenTelemetryTracer:
    """OpenTelemetry-compatible tracer."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", False)
        self.service_name = config.get("service_name", "devops-agent")
        self.endpoint = config.get("endpoint", "http://localhost:4317")
        self.tracing_manager = TracingManager(config)

        if self.enabled:
            self._setup_opentelemetry()

    def _setup_opentelemetry(self):
        """Setup OpenTelemetry components."""
        try:
            # Import OpenTelemetry components
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.resources import Resource

            # Create resource
            resource = Resource.create(
                {
                    "service.name": self.service_name,
                    "service.version": "0.1.0",
                }
            )

            # Create tracer provider
            tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(tracer_provider)

            # Create OTLP exporter
            otlp_exporter = OTLPSpanExporter(endpoint=self.endpoint)

            # Create span processor
            span_processor = BatchSpanProcessor(otlp_exporter)
            tracer_provider.add_span_processor(span_processor)

            # Get tracer
            self.tracer = trace.get_tracer(self.service_name)

            logger.info("OpenTelemetry tracing enabled")

        except ImportError:
            logger.warning("OpenTelemetry not available, using basic tracing")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to setup OpenTelemetry: {e}")
            self.enabled = False

    def start_span(
        self,
        operation_name: str,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Start a new tracing span."""
        if self.enabled and hasattr(self, "tracer"):
            # Use OpenTelemetry tracer
            span = self.tracer.start_span(operation_name)
            if tags:
                for key, value in tags.items():
                    span.set_attribute(key, value)
            return span
        else:
            # Use basic tracing
            return self.tracing_manager.start_span(operation_name, parent_span_id, tags)

    def finish_span(
        self,
        span_id: str,
        status: str = "completed",
        tags: Optional[Dict[str, Any]] = None,
    ):
        """Finish a tracing span."""
        if self.enabled and hasattr(self, "tracer") and hasattr(span_id, "end"):
            # OpenTelemetry span
            if tags:
                for key, value in tags.items():
                    span_id.set_attribute(key, value)
            span_id.end()
        else:
            # Basic tracing
            self.tracing_manager.finish_span(span_id, status, tags)

    @contextmanager
    def span(
        self,
        operation_name: str,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ):
        """Context manager for tracing spans."""
        if self.enabled and hasattr(self, "tracer"):
            # Use OpenTelemetry tracer
            with self.tracer.start_as_current_span(operation_name) as span:
                if tags:
                    for key, value in tags.items():
                        span.set_attribute(key, value)
                yield span
        else:
            # Use basic tracing
            with self.tracing_manager.span(
                operation_name, parent_span_id, tags
            ) as span_id:
                yield span_id

    def get_tracing_manager(self) -> TracingManager:
        """Get the underlying tracing manager."""
        return self.tracing_manager

    async def health_check(self) -> bool:
        """Check if tracing is healthy."""
        try:
            if self.enabled and hasattr(self, "tracer"):
                # Test OpenTelemetry tracer
                with self.tracer.start_as_current_span("health_check"):
                    pass
                return True
            else:
                # Test basic tracing
                span_id = self.tracing_manager.start_span("health_check")
                self.tracing_manager.finish_span(span_id)
                return True
        except Exception as e:
            logger.error(f"Tracing health check failed: {e}")
            return False




