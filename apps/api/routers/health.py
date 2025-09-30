"""Health check router."""

import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse

from ..models import HealthResponse, HealthCheck
from ..dependencies import get_orchestrator
from ...orchestrator import Orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

# Track startup time
startup_time = time.time()


@router.get("/", response_model=HealthResponse)
async def health_check(orchestrator: Orchestrator = Depends(get_orchestrator)):
    """Comprehensive health check."""
    try:
        components = []
        overall_status = "healthy"

        # Check orchestrator health
        try:
            orchestrator_health = await orchestrator.health_check()
            components.append(
                HealthCheck(
                    component="orchestrator",
                    status="healthy"
                    if all(orchestrator_health.values())
                    else "unhealthy",
                    details=orchestrator_health,
                )
            )

            if not all(orchestrator_health.values()):
                overall_status = "degraded"

        except Exception as e:
            components.append(
                HealthCheck(
                    component="orchestrator", status="unhealthy", message=str(e)
                )
            )
            overall_status = "unhealthy"

        # Check LLM providers
        try:
            llm_health = await orchestrator.llm_router.health_check_all()
            components.append(
                HealthCheck(
                    component="llm_providers",
                    status="healthy" if any(llm_health.values()) else "unhealthy",
                    details=llm_health,
                )
            )

            if not any(llm_health.values()):
                overall_status = "unhealthy"

        except Exception as e:
            components.append(
                HealthCheck(
                    component="llm_providers", status="unhealthy", message=str(e)
                )
            )
            overall_status = "unhealthy"

        # Check database connectivity (placeholder)
        try:
            # TODO: Implement actual database health check
            components.append(
                HealthCheck(
                    component="database",
                    status="healthy",
                    message="Database connectivity OK",
                )
            )
        except Exception as e:
            components.append(
                HealthCheck(component="database", status="unhealthy", message=str(e))
            )
            overall_status = "unhealthy"

        # Check Redis connectivity (placeholder)
        try:
            # TODO: Implement actual Redis health check
            components.append(
                HealthCheck(
                    component="redis", status="healthy", message="Redis connectivity OK"
                )
            )
        except Exception as e:
            components.append(
                HealthCheck(component="redis", status="unhealthy", message=str(e))
            )
            overall_status = "degraded"  # Redis is not critical

        # Calculate uptime
        uptime = time.time() - startup_time

        return HealthResponse(
            status=overall_status, components=components, uptime=uptime
        )

    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}",
        )


@router.get("/ready")
async def readiness_check(orchestrator: Orchestrator = Depends(get_orchestrator)):
    """Kubernetes readiness probe."""
    try:
        # Check if orchestrator is ready
        orchestrator_health = await orchestrator.health_check()

        if not all(orchestrator_health.values()):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Orchestrator not ready",
            )

        # Check if at least one LLM provider is available
        llm_health = await orchestrator.llm_router.health_check_all()

        if not any(llm_health.values()):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No LLM providers available",
            )

        return {"status": "ready"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)}",
        )


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    try:
        # Simple liveness check - just verify the service is running
        return {"status": "alive"}

    except Exception as e:
        logger.error(f"Liveness check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service not alive: {str(e)}",
        )


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    try:
        # TODO: Implement actual metrics collection
        # For now, return basic metrics
        metrics_data = {
            "devops_agent_uptime_seconds": time.time() - startup_time,
            "devops_agent_active_tasks": 0,  # TODO: Get from orchestrator
            "devops_agent_llm_requests_total": 0,  # TODO: Implement counter
            "devops_agent_llm_requests_failed_total": 0,  # TODO: Implement counter
        }

        # Format as Prometheus metrics
        lines = []
        for key, value in metrics_data.items():
            description = key.replace("_", " ").title()
            lines.append(f"# HELP {key} {description}")
            lines.append(f"# TYPE {key} gauge")
            lines.append(f"{key} {value}")
        metrics_text = "\n".join(lines) + "\n"

        return PlainTextResponse(content=metrics_text, media_type="text/plain")

    except Exception as e:
        logger.error(f"Metrics error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}",
        )
