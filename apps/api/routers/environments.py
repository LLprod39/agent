"""Environment profile API endpoints."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from packages.shared.env_schema import ValidationError

from ..dependencies import get_environment_service
from ..models import EnvironmentListResponse, EnvironmentProfile, EnvironmentResponse
from ..services.environment_service import EnvironmentProfile as ServiceEnvironmentProfile
from ..services.environment_service import EnvironmentService

logger = logging.getLogger(__name__)

router = APIRouter()


class EnvironmentCreateRequest(BaseModel):
    """Request model for creating environment profiles."""
    
    id: str
    type: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    networking: Dict[str, Any]
    auth: Dict[str, Any]
    policies: Dict[str, Any]
    cluster: Optional[Dict[str, Any]] = None
    defaults: Optional[Dict[str, Any]] = None
    runbooks: Optional[List[str]] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    ssh: Optional[Dict[str, Any]] = None
    extensions: Optional[Dict[str, Any]] = None


class EnvironmentUpdateRequest(BaseModel):
    """Request model for updating environment profiles."""
    
    type: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    networking: Optional[Dict[str, Any]] = None
    auth: Optional[Dict[str, Any]] = None
    policies: Optional[Dict[str, Any]] = None
    cluster: Optional[Dict[str, Any]] = None
    defaults: Optional[Dict[str, Any]] = None
    runbooks: Optional[List[str]] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    ssh: Optional[Dict[str, Any]] = None
    extensions: Optional[Dict[str, Any]] = None


@router.get("/", response_model=EnvironmentListResponse)
async def list_environments(service: EnvironmentService = Depends(get_environment_service)):
    """List available environment profiles."""
    try:
        profiles = await service.list_profiles()

        environments = [
            _to_api_model(profile)
            for profile in profiles
        ]

        return EnvironmentListResponse(
            environments=environments,
            message=f"Found {len(environments)} environment profiles",
        )

    except Exception as e:
        logger.error(f"List environments error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list environments: {str(e)}",
        )


@router.get("/{environment_id}", response_model=EnvironmentResponse)
async def get_environment(
    environment_id: str, 
    service: EnvironmentService = Depends(get_environment_service)
):
    """Get a specific environment profile."""
    try:
        profile = await service.get_profile(environment_id)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Environment profile '{environment_id}' is invalid: {exc.message}",
        ) from exc
    except Exception as exc:
        logger.error("Get environment error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get environment",
        ) from exc

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment profile '{environment_id}' not found",
        )

    return EnvironmentResponse(
        environment=_to_api_model(profile),
        message=f"Environment profile '{environment_id}' loaded successfully",
    )


@router.post("/{environment_id}/validate")
async def validate_environment(
    environment_id: str, 
    service: EnvironmentService = Depends(get_environment_service)
):
    """Validate an environment profile."""
    try:
        result = await service.validate_profile(environment_id)

        if result.valid:
            return {
                "environment_id": environment_id,
                "validation": {
                    "valid": True,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "profile": _to_api_model(result.profile).model_dump() if result.profile else None
                },
                "message": "Validation completed successfully",
            }
        else:
            return {
                "environment_id": environment_id,
                "validation": {
                    "valid": False,
                    "errors": result.errors,
                    "warnings": result.warnings,
                },
                "message": "Validation completed with errors",
            }
        
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Environment profile '{environment_id}' is invalid: {exc.message}",
        ) from exc
    except Exception as e:
        logger.error(f"Validate environment error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate environment: {str(e)}",
        )


@router.post("/", response_model=EnvironmentProfile)
async def create_environment(
    request: EnvironmentCreateRequest,
    service: EnvironmentService = Depends(get_environment_service)
):
    """Create a new environment profile."""
    try:
        # Convert request to dict
        profile_data = request.model_dump(exclude_none=True)
        
        result = await service.create_profile(profile_data)

        if not result.valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Profile validation failed",
                    "errors": result.errors,
                    "warnings": result.warnings
                }
            )
        
        return _to_api_model(result.profile)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create environment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create environment: {str(e)}"
        )


@router.put("/{environment_id}", response_model=EnvironmentProfile)
async def update_environment(
    environment_id: str,
    request: EnvironmentUpdateRequest,
    service: EnvironmentService = Depends(get_environment_service)
):
    """Update an existing environment profile."""
    try:
        # Get existing profile
        try:
            existing = await service.get_profile(environment_id)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Environment profile '{environment_id}' is invalid: {exc.message}",
            ) from exc

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Environment profile '{environment_id}' not found"
            )
        
        # Merge with existing data
        profile_data = {
            "id": environment_id,
            "type": existing.type,
            "display_name": existing.display_name,
            "description": existing.description,
            "networking": existing.networking,
            "auth": existing.auth,
            "policies": existing.policies,
            "cluster": existing.cluster,
            "defaults": existing.defaults,
        "runbooks": existing.runbooks,
        "notes": existing.notes,
        "metadata": existing.metadata,
        "ssh": existing.ssh,
        "extensions": existing.extensions,
    }
        
        # Update with request data
        request_data = request.model_dump(exclude_unset=True)
        profile_data.update(request_data)
        
        result = await service.update_profile(environment_id, profile_data)
        
        if not result.valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Profile validation failed",
                    "errors": result.errors,
                    "warnings": result.warnings
                }
            )
        
        return _to_api_model(result.profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update environment {environment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update environment: {str(e)}"
        )


@router.delete("/{environment_id}")
async def delete_environment(
    environment_id: str,
    service: EnvironmentService = Depends(get_environment_service)
):
    """Delete an environment profile."""
    try:
        success = await service.delete_profile(environment_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Environment profile '{environment_id}' not found"
            )
        
        return {"message": f"Environment profile '{environment_id}' deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete environment {environment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete environment: {str(e)}"
        )


@router.get("/{environment_id}/runbooks")
async def get_environment_runbooks(
    environment_id: str, 
    service: EnvironmentService = Depends(get_environment_service)
):
    """Get runbooks for an environment profile."""
    try:
        # Get the environment profile
        try:
            profile = await service.get_profile(environment_id)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Environment profile '{environment_id}' is invalid: {exc.message}",
            ) from exc

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Environment profile '{environment_id}' not found"
            )

        runbooks = []

        if profile.runbooks:
            repo_root = service.profiles_dir.parent
            for runbook_path in profile.runbooks:
                try:
                    runbook_file = repo_root / runbook_path
                    if runbook_file.exists():
                        content = runbook_file.read_text(encoding="utf-8")
                        runbooks.append(
                            {
                                "path": runbook_path,
                                "name": runbook_file.name,
                                "content": content,
                                "size": len(content),
                            }
                        )
                    else:
                        runbooks.append(
                            {
                                "path": runbook_path,
                                "name": runbook_file.name,
                                "error": "File not found",
                            }
                        )

                except Exception as e:
                    runbooks.append({"path": runbook_path, "error": str(e)})

        return {
            "environment_id": environment_id,
            "runbooks": runbooks,
            "total": len(runbooks),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get environment runbooks error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get environment runbooks: {str(e)}",
        )


def _to_api_model(profile: ServiceEnvironmentProfile) -> EnvironmentProfile:
    """Convert service profile dataclass into API model."""
    if not profile:
        raise ValueError("Profile is required")

    payload = dict(profile.data) if profile.data else {
        "id": profile.id,
        "type": profile.type,
        "display_name": profile.display_name,
        "description": profile.description,
        "networking": profile.networking,
        "auth": profile.auth,
        "policies": profile.policies,
        "cluster": profile.cluster,
        "defaults": profile.defaults,
        "runbooks": profile.runbooks,
        "notes": profile.notes,
        "metadata": profile.metadata,
        "ssh": profile.ssh,
        "extensions": profile.extensions,
    }

    return EnvironmentProfile(**payload)
