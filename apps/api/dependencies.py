"""Dependencies for the API."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings, get_settings as load_settings
from packages.shared.env_schema import ValidationError
from ..orchestrator import Orchestrator
from ..database.connection import DatabaseManager
from ..database import repositories
from ..cache import RedisManager, SessionManager, LLMCache, RateLimiter
from .services.environment_service import EnvironmentProfile, EnvironmentService

# Security scheme
security = HTTPBearer(auto_error=False)


def get_settings() -> Settings:
    """Return cached application settings."""
    return load_settings()


@lru_cache(maxsize=1)
def _build_environment_service(profiles_dir: str, cache_ttl: int) -> EnvironmentService:
    return EnvironmentService(Path(profiles_dir), cache_ttl=cache_ttl)


def get_environment_service(settings: Settings = Depends(get_settings)) -> EnvironmentService:
    """Return a cached EnvironmentService instance."""
    return _build_environment_service(str(settings.environment_profiles_dir), settings.environment_cache_ttl)


def get_orchestrator(request: Request) -> Orchestrator:
    """Get the orchestrator instance from the FastAPI application state."""
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator not available",
        )
    return orchestrator


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Get current user from authorization header."""
    if not credentials:
        return "anonymous"

    # TODO: Implement proper authentication
    return "user"


async def get_environment_profile(
    profile_id: str | None = None,
    service: EnvironmentService = Depends(get_environment_service),
) -> Dict:
    """Load an environment profile by ID if it exists."""
    if not profile_id:
        return {}

    try:
        profile = await service.get_profile(profile_id)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Environment profile '{profile_id}' is invalid: {exc.message}",
        ) from exc
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment profile '{profile_id}' not found",
        )

    return _environment_profile_to_dict(profile)


async def validate_environment_profile(
    profile_id: str,
    service: EnvironmentService = Depends(get_environment_service),
) -> Dict:
    """Validate that a profile exists and return its contents."""
    if not profile_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Environment profile ID is required",
        )

    try:
        profile = await service.get_profile(profile_id)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Environment profile '{profile_id}' is invalid: {exc.message}",
        ) from exc
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment profile '{profile_id}' not found",
        )

    return _environment_profile_to_dict(profile)


def get_session_id() -> str:
    """Generate or get session ID."""
    import uuid

    return str(uuid.uuid4())


def get_user_id() -> str:
    """Get user ID from request context."""
    # TODO: Extract from JWT token or session
    return "default_user"


def get_request_context() -> Dict[str, str]:
    """Get request context."""
    return {
        "user_id": get_user_id(),
        "session_id": get_session_id(),
        "timestamp": datetime.utcnow().isoformat(),
    }


def _environment_profile_to_dict(profile: EnvironmentProfile) -> Dict:
    """Convert an EnvironmentProfile dataclass into a serializable dict."""
    data = dict(profile.data) if getattr(profile, "data", None) else asdict(profile)
    # Remove internal service fields when falling back to dataclass conversion
    data.pop("file_path", None)
    data.pop("data", None)
    return data


def get_db_manager(request: Request) -> DatabaseManager:
    """Get the database manager instance from the FastAPI application state."""
    db_manager = getattr(request.app.state, "db_manager", None)
    if not db_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available",
        )
    return db_manager


async def get_db(request: Request):
    """Get database session for dependency injection."""
    db_manager = get_db_manager(request)
    async for session in db_manager.get_session():
        yield session


# Repository dependencies
def get_user_repository(db: AsyncSession = Depends(get_db)) -> repositories.UserRepository:
    """Get user repository."""
    return repositories.UserRepository(db)


def get_session_repository(db: AsyncSession = Depends(get_db)) -> repositories.SessionRepository:
    """Get session repository."""
    return repositories.SessionRepository(db)


def get_message_repository(db: AsyncSession = Depends(get_db)) -> repositories.MessageRepository:
    """Get message repository."""
    return repositories.MessageRepository(db)


def get_task_repository(db: AsyncSession = Depends(get_db)) -> repositories.TaskRepository:
    """Get task repository."""
    return repositories.TaskRepository(db)


def get_task_step_repository(db: AsyncSession = Depends(get_db)) -> repositories.TaskStepRepository:
    """Get task step repository."""
    return repositories.TaskStepRepository(db)


def get_audit_log_repository(db: AsyncSession = Depends(get_db)) -> repositories.AuditLogRepository:
    """Get audit log repository."""
    return repositories.AuditLogRepository(db)


def get_llm_usage_repository(db: AsyncSession = Depends(get_db)) -> repositories.LLMUsageRepository:
    """Get LLM usage repository."""
    return repositories.LLMUsageRepository(db)


# Redis dependencies
def get_redis_manager(request: Request) -> RedisManager:
    """Get the Redis manager instance from the FastAPI application state."""
    redis_manager = getattr(request.app.state, "redis_manager", None)
    if not redis_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not available",
        )
    return redis_manager


def get_session_manager(request: Request) -> SessionManager:
    """Get the session manager instance from the FastAPI application state."""
    session_manager = getattr(request.app.state, "session_manager", None)
    if not session_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session manager not available",
        )
    return session_manager


def get_llm_cache(request: Request) -> LLMCache:
    """Get the LLM cache instance from the FastAPI application state."""
    llm_cache = getattr(request.app.state, "llm_cache", None)
    if not llm_cache:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM cache not available",
        )
    return llm_cache


def get_rate_limiter(request: Request) -> RateLimiter:
    """Get the rate limiter instance from the FastAPI application state."""
    rate_limiter = getattr(request.app.state, "rate_limiter", None)
    if not rate_limiter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiter not available",
        )
    return rate_limiter
