"""Middleware components for FastAPI."""

from .prometheus import (
    PrometheusMiddleware,
    get_metrics,
    track_llm_request,
    track_llm_tokens,
    track_task,
    set_active_tasks,
    track_cache_hit,
    track_cache_miss,
    track_security_violation,
)

__all__ = [
    "PrometheusMiddleware",
    "get_metrics",
    "track_llm_request",
    "track_llm_tokens",
    "track_task",
    "set_active_tasks",
    "track_cache_hit",
    "track_cache_miss",
    "track_security_violation",
]
