"""Admin and system management router."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from ..dependencies import (
    get_orchestrator,
    get_redis_manager,
    get_session_manager,
    get_llm_cache,
)
from ...orchestrator import Orchestrator
from ...cache import RedisManager, SessionManager, LLMCache

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class CacheStatsResponse(BaseModel):
    """Cache statistics response."""

    enabled: bool
    stats: Dict[str, Any] | None = None


class CacheClearResponse(BaseModel):
    """Cache clear response."""

    cleared: int
    message: str


class SessionStatsResponse(BaseModel):
    """Session statistics response."""

    total_sessions: int
    message: str


# ========== Cache Management ==========


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """Get LLM cache statistics."""
    try:
        if not orchestrator.llm_router.cache_enabled:
            return CacheStatsResponse(enabled=False, stats=None)

        stats = await orchestrator.llm_router.get_cache_stats()
        return CacheStatsResponse(enabled=True, stats=stats)

    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache statistics: {str(e)}",
        )


@router.post("/cache/clear", response_model=CacheClearResponse)
async def clear_cache(
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """Clear the LLM cache."""
    try:
        if not orchestrator.llm_router.cache_enabled:
            return CacheClearResponse(
                cleared=0, message="Cache is not enabled"
            )

        cleared = await orchestrator.llm_router.clear_cache()
        return CacheClearResponse(
            cleared=cleared,
            message=f"Cleared {cleared} cached responses",
        )

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}",
        )


# ========== Session Management ==========


@router.get("/sessions/stats", response_model=SessionStatsResponse)
async def get_session_stats(
    session_manager: SessionManager = Depends(get_session_manager),
):
    """Get session statistics."""
    try:
        session_count = await session_manager.get_session_count()
        return SessionStatsResponse(
            total_sessions=session_count,
            message=f"Total active sessions: {session_count}",
        )

    except Exception as e:
        logger.error(f"Failed to get session stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session statistics: {str(e)}",
        )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """Delete a specific session."""
    try:
        deleted = await session_manager.delete_session(session_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        return {"message": f"Session {session_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}",
        )


# ========== System Information ==========


@router.get("/system/info")
async def get_system_info(
    request: Request,
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """Get system information."""
    try:
        # Get LLM providers info
        providers_health = await orchestrator.llm_router.health_check_all()
        available_models = orchestrator.llm_router.get_available_models()

        # Get cache info
        cache_enabled = orchestrator.llm_router.cache_enabled
        cache_stats = None
        if cache_enabled:
            cache_stats = await orchestrator.llm_router.get_cache_stats()

        # Get Redis info
        redis_healthy = False
        redis_manager = getattr(request.app.state, "redis_manager", None)
        if redis_manager:
            redis_healthy = await redis_manager.health_check()

        # Get DB info
        db_healthy = False
        db_manager = getattr(request.app.state, "db_manager", None)
        if db_manager:
            db_healthy = await db_manager.health_check()

        return {
            "version": "0.3.1",
            "components": {
                "llm_providers": {
                    "available": list(providers_health.keys()),
                    "healthy": [
                        k for k, v in providers_health.items() if v
                    ],
                    "models": available_models,
                },
                "cache": {
                    "enabled": cache_enabled,
                    "stats": cache_stats,
                },
                "redis": {
                    "enabled": redis_manager is not None,
                    "healthy": redis_healthy,
                },
                "database": {
                    "enabled": db_manager is not None,
                    "healthy": db_healthy,
                },
            },
            "features": {
                "llm_caching": cache_enabled,
                "session_management": redis_manager is not None,
                "rate_limiting": redis_manager is not None,
                "audit_logging": db_manager is not None,
            },
        }

    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system information: {str(e)}",
        )


# ========== Redis Management ==========


@router.get("/redis/info")
async def get_redis_info(
    redis_manager: RedisManager = Depends(get_redis_manager),
):
    """Get Redis information."""
    try:
        healthy = await redis_manager.health_check()

        return {
            "healthy": healthy,
            "url": redis_manager.redis_url,
            "message": (
                "Redis is healthy" if healthy else "Redis is unhealthy"
            ),
        }

    except Exception as e:
        logger.error(f"Failed to get Redis info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Redis information: {str(e)}",
        )


# ========== LLM Configuration Management ==========


class ProviderConfigUpdate(BaseModel):
    """Model for updating provider configuration."""
    
    api_key: str | None = None
    model: str | None = None
    enabled: bool | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class ProviderConfigResponse(BaseModel):
    """Response model for provider configuration update."""
    
    success: bool
    message: str
    provider: str
    config: Dict[str, Any]


@router.get("/llm/config")
async def get_llm_config(
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """Get current LLM configuration."""
    try:
        providers = orchestrator.llm_router.providers
        all_available_models = orchestrator.llm_router.get_available_models()
        
        config = {
            "providers": [],
            "cache_enabled": orchestrator.llm_router.cache_enabled,
            "available_models": all_available_models,
        }

        for provider_name, provider in providers.items():
            # Get current config
            provider_config = {}
            if hasattr(provider, 'config'):
                provider_config = provider.config
            
            # Get available models for this provider
            provider_models = all_available_models.get(provider_name, [])
            
            provider_info = {
                "name": provider_name,
                "type": getattr(provider, "provider_type", provider_name),
                "enabled": getattr(provider, "enabled", True),
                "priority": getattr(provider, "priority", 0),
                "models": provider_models,
                "current_model": getattr(provider, "model_name", provider_config.get("model")),
                "has_api_key": bool(getattr(provider, "api_key", None)) if provider_name == "gemini" else None,
            }
            config["providers"].append(provider_info)

        return config

    except Exception as e:
        logger.error(f"Failed to get LLM config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get LLM configuration: {str(e)}",
        )


@router.get("/llm/providers/health")
async def check_providers_health(
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """Check health of all LLM providers."""
    try:
        health_status = await orchestrator.llm_router.health_check_all()
        
        results = []
        for provider_name, is_healthy in health_status.items():
            results.append({
                "name": provider_name,
                "healthy": is_healthy,
                "status": "online" if is_healthy else "offline",
            })

        return {
            "providers": results,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to check providers health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check providers health: {str(e)}",
        )


@router.post("/llm/providers/{provider_name}/config", response_model=ProviderConfigResponse)
async def update_provider_config(
    provider_name: str,
    config_update: ProviderConfigUpdate,
    request: Request,
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """Update configuration for a specific LLM provider."""
    try:
        # Get the provider
        provider = orchestrator.llm_router.providers.get(provider_name)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider {provider_name} not found",
            )
        
        updated_config = {}
        
        # Update API key if provided
        if config_update.api_key is not None:
            if provider_name == "gemini":
                # Update Gemini provider API key
                provider.api_key = config_update.api_key
                # Reinitialize client
                from google import genai
                provider.client = genai.Client(api_key=config_update.api_key)
                updated_config["api_key"] = "***" + config_update.api_key[-4:] if len(config_update.api_key) > 4 else "***"
                logger.info(f"Updated API key for {provider_name}")
            
        # Update model if provided
        if config_update.model is not None:
            if hasattr(provider, 'model_name'):
                provider.model_name = config_update.model
                updated_config["model"] = config_update.model
                logger.info(f"Updated model for {provider_name} to {config_update.model}")
        
        # Update enabled status if provided
        if config_update.enabled is not None:
            if hasattr(provider, 'enabled'):
                provider.enabled = config_update.enabled
                updated_config["enabled"] = config_update.enabled
                logger.info(f"Set {provider_name} enabled={config_update.enabled}")
        
        # Update temperature if provided
        if config_update.temperature is not None:
            if hasattr(provider, 'temperature'):
                provider.temperature = config_update.temperature
                updated_config["temperature"] = config_update.temperature
        
        # Update max_tokens if provided
        if config_update.max_tokens is not None:
            if hasattr(provider, 'max_tokens'):
                provider.max_tokens = config_update.max_tokens
                updated_config["max_tokens"] = config_update.max_tokens
        
        # Verify the update with a health check
        try:
            is_healthy = await provider.health_check()
            updated_config["healthy"] = is_healthy
            
            if not is_healthy and config_update.api_key:
                logger.warning(f"Provider {provider_name} health check failed after config update")
        except Exception as e:
            logger.error(f"Health check failed for {provider_name}: {e}")
            updated_config["healthy"] = False
        
        return ProviderConfigResponse(
            success=True,
            message=f"Configuration updated successfully for {provider_name}",
            provider=provider_name,
            config=updated_config,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update provider config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update provider configuration: {str(e)}",
        )


@router.post("/llm/providers/{provider_name}/test")
async def test_provider_with_config(
    provider_name: str,
    model: str | None = None,
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """Test a provider with a specific model."""
    try:
        provider = orchestrator.llm_router.providers.get(provider_name)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider {provider_name} not found",
            )
        
        import time
        start_time = time.time()
        
        # Simple test request
        from ...orchestrator.llm_router.base import LLMRequest
        
        test_request = LLMRequest(
            prompt="Say 'Hello from DevOps Agent'",
            model=model or getattr(provider, 'model_name', None),
            temperature=0.7,
        )
        
        response = await provider.complete(test_request)
        execution_time = time.time() - start_time
        
        return {
            "success": True,
            "provider": provider_name,
            "model": response.model,
            "response": response.content[:200],  # First 200 chars
            "execution_time": execution_time,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Provider test failed: {e}")
        return {
            "success": False,
            "provider": provider_name,
            "error": str(e),
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }


# ========== Agent Testing ==========


class AgentTestRequest(BaseModel):
    """Request model for testing agents."""
    
    task: str
    environment_profile: str | None = None
    agent_type: str = "planner"  # planner, executor, verifier
    auto_approve: bool = False


class AgentTestResponse(BaseModel):
    """Response model for agent testing."""
    
    test_id: str
    status: str
    result: Dict[str, Any] | None = None
    error: str | None = None
    execution_time: float | None = None


@router.post("/test/agent", response_model=AgentTestResponse)
async def test_agent(
    request: AgentTestRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """Test a specific agent with a task."""
    try:
        import time
        import uuid

        test_id = str(uuid.uuid4())
        start_time = time.time()

        # Execute the task through orchestrator
        result = await orchestrator.process_task(
            task=request.task,
            environment_profile=request.environment_profile,
            auto_approve=request.auto_approve,
        )

        execution_time = time.time() - start_time

        return AgentTestResponse(
            test_id=test_id,
            status="success",
            result=result,
            execution_time=execution_time,
        )

    except Exception as e:
        logger.error(f"Agent test failed: {e}")
        return AgentTestResponse(
            test_id=test_id if 'test_id' in locals() else "unknown",
            status="failed",
            error=str(e),
            execution_time=time.time() - start_time if 'start_time' in locals() else None,
        )


# ========== Workflow Logs ==========


@router.get("/logs/workflow/{task_id}")
async def get_workflow_logs(
    task_id: str,
    request: Request,
):
    """Get workflow logs for a specific task."""
    try:
        db_manager = getattr(request.app.state, "db_manager", None)
        if not db_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not available",
            )

        # Get task from database
        from ...database.repositories import TaskRepository
        
        async with db_manager.get_session() as session:
            task_repo = TaskRepository(session)
            task = await task_repo.get_by_id(task_id)
            
            if not task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Task {task_id} not found",
                )

            # Get audit logs for this task
            audit_logs = await task_repo.get_audit_logs(task_id)

            return {
                "task_id": task_id,
                "status": task.status,
                "workflow": task.workflow_data or {},
                "audit_logs": [
                    {
                        "timestamp": log.timestamp.isoformat(),
                        "action": log.action,
                        "details": log.details,
                        "user_id": log.user_id,
                    }
                    for log in audit_logs
                ],
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow logs: {str(e)}",
        )
