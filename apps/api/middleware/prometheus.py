"""Prometheus metrics middleware for FastAPI."""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

# Define Prometheus metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint']
)

# Task metrics
active_tasks_gauge = Gauge(
    'devops_agent_active_tasks',
    'Number of active tasks',
    ['environment']
)

tasks_total = Counter(
    'devops_agent_tasks_total',
    'Total number of tasks',
    ['status', 'environment']
)

task_duration_seconds = Histogram(
    'devops_agent_task_duration_seconds',
    'Task execution duration in seconds',
    ['environment'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0]
)

# LLM metrics
llm_requests_total = Counter(
    'devops_agent_llm_requests_total',
    'Total LLM requests',
    ['provider', 'model', 'status']
)

llm_request_duration_seconds = Histogram(
    'devops_agent_llm_request_duration_seconds',
    'LLM request duration in seconds',
    ['provider', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

llm_tokens_total = Counter(
    'devops_agent_llm_tokens_total',
    'Total LLM tokens consumed',
    ['provider', 'model', 'type']
)

# Cache metrics
cache_hits_total = Counter(
    'devops_agent_cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'devops_agent_cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

# Security metrics
security_violations_total = Counter(
    'devops_agent_security_violations_total',
    'Total security violations',
    ['violation_type', 'severity']
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        # Skip metrics endpoint itself
        if request.url.path == "/metrics" or request.url.path == "/api/v1/health/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path

        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()
        
        start_time = time.time()
        status_code = 500
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            # Record metrics
            duration = time.time() - start_time
            
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status_code
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()


def get_metrics() -> bytes:
    """Get Prometheus metrics in text format."""
    return generate_latest()


# Helper functions to track metrics from other components
def track_llm_request(provider: str, model: str, status: str, duration: float):
    """Track LLM request metrics."""
    llm_requests_total.labels(provider=provider, model=model, status=status).inc()
    llm_request_duration_seconds.labels(provider=provider, model=model).observe(duration)


def track_llm_tokens(provider: str, model: str, token_type: str, count: int):
    """Track LLM token usage."""
    llm_tokens_total.labels(provider=provider, model=model, type=token_type).inc(count)


def track_task(status: str, environment: str, duration: float = None):
    """Track task metrics."""
    tasks_total.labels(status=status, environment=environment).inc()
    if duration is not None:
        task_duration_seconds.labels(environment=environment).observe(duration)


def set_active_tasks(environment: str, count: int):
    """Set number of active tasks."""
    active_tasks_gauge.labels(environment=environment).set(count)


def track_cache_hit(cache_type: str):
    """Track cache hit."""
    cache_hits_total.labels(cache_type=cache_type).inc()


def track_cache_miss(cache_type: str):
    """Track cache miss."""
    cache_misses_total.labels(cache_type=cache_type).inc()


def track_security_violation(violation_type: str, severity: str):
    """Track security violation."""
    security_violations_total.labels(violation_type=violation_type, severity=severity).inc()
