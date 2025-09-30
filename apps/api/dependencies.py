"""Dependencies for the API."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config.settings import Settings, get_settings as load_settings
from packages.shared.env_schema import ValidationError
from ..orchestrator import Orchestrator
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
