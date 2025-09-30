"""Health check router."""

import logging
import time
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse

from ..models import HealthResponse, HealthCheck
from ..dependencies import get_orchestrator, get_redis_manager, get_db_manager
from ...orchestrator import Orchestrator
from ...cache import RedisManager
from ...database.connection import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Track startup time
startup_time = time.time()


@router.get("/", response_model=HealthResponse)
async def health_check(
    request: Request,
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
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

        # Check database connectivity
        try:
            db_manager: DatabaseManager = getattr(request.app.state, "db_manager", None)
            if db_manager:
                db_healthy = await db_manager.health_check()
                components.append(
                    HealthCheck(
                        component="database",
                        status="healthy" if db_healthy else "unhealthy",
                        message="Database connectivity OK" if db_healthy else "Database unreachable",
                    )
                )
                if not db_healthy:
                    overall_status = "unhealthy"
            else:
                components.append(
                    HealthCheck(
                        component="database",
                        status="unknown",
                        message="Database manager not initialized",
                    )
                )
                overall_status = "degraded"

        except Exception as e:
            components.append(
                HealthCheck(component="database", status="unhealthy", message=str(e))
            )
            overall_status = "unhealthy"

        # Check Redis connectivity
        try:
            redis_manager: RedisManager = getattr(request.app.state, "redis_manager", None)
            if redis_manager:
                redis_healthy = await redis_manager.health_check()
                components.append(
                    HealthCheck(
                        component="redis",
                        status="healthy" if redis_healthy else "unhealthy",
                        message="Redis connectivity OK" if redis_healthy else "Redis unreachable"
                    )
                )
                if not redis_healthy:
                    overall_status = "degraded"  # Redis is not critical
            else:
                components.append(
                    HealthCheck(
                        component="redis",
                        status="unknown",
                        message="Redis manager not initialized"
                    )
                )
                overall_status = "degraded"

        except Exception as e:
            components.append(
                HealthCheck(component="redis", status="unhealthy", message=str(e))
            )
            overall_status = "degraded"  # Redis is not critical
        
        # Check LLM Cache stats
        try:
            if orchestrator.llm_router.cache_enabled:
                cache_stats = await orchestrator.llm_router.get_cache_stats()
                if cache_stats:
                    components.append(
                        HealthCheck(
                            component="llm_cache",
                            status="healthy",
                            message=f"Cache hit rate: {cache_stats.get('hit_rate', 0):.2%}",
                            details=cache_stats
                        )
                    )
            else:
                components.append(
                    HealthCheck(
                        component="llm_cache",
                        status="disabled",
                        message="LLM caching is disabled"
                    )
                )
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")

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
        from ..middleware.prometheus import get_metrics
        
        # Get Prometheus metrics in text format
        metrics_data = get_metrics()
        
        return PlainTextResponse(
            content=metrics_data.decode('utf-8'),
            media_type="text/plain; version=0.0.4"
        )

    except Exception as e:
        logger.error(f"Metrics error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}",
        )
