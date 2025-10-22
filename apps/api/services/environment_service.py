"""Environment profile management service."""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import yaml

from packages.shared.env_schema import (
    ValidationError,
    validate_environment_profile,
    validate_environment_profile_file,
)

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentProfile:
    """Environment profile data structure."""

    id: str
    type: str
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
    last_updated: Optional[datetime] = None
    file_path: Optional[Path] = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnvironmentValidationResult:
    """Result of environment profile validation."""
    
    valid: bool
    errors: List[str]
    warnings: List[str]
    profile: Optional[EnvironmentProfile] = None


class EnvironmentService:
    """Service for managing environment profiles."""
    
    def __init__(self, profiles_dir: Path, cache_ttl: int = 300, redis_manager=None):
        """
        Initialize environment service.
        
        Args:
            profiles_dir: Directory containing environment profile files
            cache_ttl: Cache TTL in seconds
            redis_manager: Optional Redis manager for distributed caching
        """
        self.profiles_dir = Path(profiles_dir)
        self.cache_ttl = cache_ttl
        self.redis_manager = redis_manager
        self._cache: Dict[str, Tuple[EnvironmentProfile, datetime]] = {}
        self._lock = asyncio.Lock()
        self._redis_prefix = "env:profile:"
        
        # Ensure profiles directory exists
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        cache_type = "Redis" if redis_manager else "in-memory"
        logger.info(f"Environment service initialized with profiles dir: {self.profiles_dir}, cache: {cache_type}")
    
    async def list_profiles(self) -> List[EnvironmentProfile]:
        """
        List all available environment profiles.
        
        Returns:
            List of environment profiles
        """
        profiles = []
        
        # Scan for profile files
        for file_path in self.profiles_dir.glob("*.yaml"):
            if file_path.name.endswith(".example.yaml"):
                continue
                
            try:
                profile = await self._load_profile(file_path)
                if profile:
                    profiles.append(profile)
            except Exception as e:
                logger.warning(f"Failed to load profile {file_path}: {e}")
                continue
        
        for file_path in self.profiles_dir.glob("*.yml"):
            if file_path.name.endswith(".example.yml"):
                continue
                
            try:
                profile = await self._load_profile(file_path)
                if profile:
                    profiles.append(profile)
            except Exception as e:
                logger.warning(f"Failed to load profile {file_path}: {e}")
                continue
        
        # Sort by display name or ID
        profiles.sort(key=lambda p: p.display_name or p.id)
        
        logger.info(f"Loaded {len(profiles)} environment profiles")
        return profiles
    
    async def get_profile(self, profile_id: str) -> Optional[EnvironmentProfile]:
        """
        Get a specific environment profile by ID.
        
        Args:
            profile_id: Profile identifier
            
        Returns:
            Environment profile or None if not found
        """
        # Check Redis cache first if available
        if self.redis_manager:
            try:
                cached_data = await self._get_from_redis_cache(profile_id)
                if cached_data:
                    return self._dict_to_profile(cached_data, None)
            except Exception as e:
                logger.warning(f"Redis cache error, falling back to in-memory: {e}")
        
        # Check in-memory cache
        if profile_id in self._cache:
            profile, timestamp = self._cache[profile_id]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return profile
        
        # Find profile file
        profile_file = None
        for pattern in [f"{profile_id}.yaml", f"{profile_id}.yml"]:
            candidate = self.profiles_dir / pattern
            if candidate.exists():
                profile_file = candidate
                break
        
        if not profile_file:
            logger.warning(f"Profile {profile_id} not found")
            return None
        
        try:
            profile = await self._load_profile(profile_file)
            return profile
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to load profile {profile_id}: {e}")
            return None
    
    async def validate_profile(self, profile_id: str) -> EnvironmentValidationResult:
        """
        Validate an environment profile.
        
        Args:
            profile_id: Profile identifier
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        try:
            # Find profile file
            profile_file = None
            for pattern in [f"{profile_id}.yaml", f"{profile_id}.yml"]:
                candidate = self.profiles_dir / pattern
                if candidate.exists():
                    profile_file = candidate
                    break
            
            if not profile_file:
                errors.append(f"Profile file not found: {profile_id}")
                return EnvironmentValidationResult(
                    valid=False,
                    errors=errors,
                    warnings=warnings
                )
            
            # Validate using schema
            try:
                profile_data = validate_environment_profile_file(profile_file)
                profile = self._dict_to_profile(profile_data, profile_file)
                
                # Additional validation checks
                await self._validate_profile_content(profile, errors, warnings)
                
                return EnvironmentValidationResult(
                    valid=len(errors) == 0,
                    errors=errors,
                    warnings=warnings,
                    profile=profile
                )
                
            except ValidationError as e:
                errors.append(f"Schema validation failed: {e.message}")
                return EnvironmentValidationResult(
                    valid=False,
                    errors=errors,
                    warnings=warnings
                )
                
        except Exception as e:
            errors.append(f"Validation failed: {str(e)}")
            return EnvironmentValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings
            )
    
    async def create_profile(self, profile_data: Dict[str, Any]) -> EnvironmentValidationResult:
        """
        Create a new environment profile.
        
        Args:
            profile_data: Profile data
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        try:
            networking = profile_data.setdefault("networking", {})
            if not isinstance(networking, dict):
                networking = {}
                profile_data["networking"] = networking
            proxy_cfg = networking.get("proxy")
            if not isinstance(proxy_cfg, dict):
                networking["proxy"] = {}

            # Validate profile data
            validate_environment_profile(profile_data)
            
            # Check if profile already exists
            profile_id = profile_data["id"]
            existing = await self.get_profile(profile_id)
            if existing:
                errors.append(f"Profile {profile_id} already exists")
                return EnvironmentValidationResult(
                    valid=False,
                    errors=errors,
                    warnings=warnings
                )
            
            # Create profile file
            profile_file = self.profiles_dir / f"{profile_id}.yaml"
            
            # Convert to YAML and save
            import yaml
            with open(profile_file, 'w', encoding='utf-8') as f:
                yaml.dump(profile_data, f, default_flow_style=False, sort_keys=False)
            
            # Clear cache
            await self._invalidate_cache(profile_id)
            
            # Load and validate the created profile
            profile = self._dict_to_profile(profile_data, profile_file)
            await self._validate_profile_content(profile, errors, warnings)
            
            logger.info(f"Created environment profile: {profile_id}")
            
            return EnvironmentValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                profile=profile
            )
            
        except ValidationError as e:
            errors.append(f"Schema validation failed: {e.message}")
            return EnvironmentValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings
            )
        except Exception as e:
            errors.append(f"Failed to create profile: {str(e)}")
            return EnvironmentValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings
            )
    
    async def update_profile(self, profile_id: str, profile_data: Dict[str, Any]) -> EnvironmentValidationResult:
        """
        Update an existing environment profile.
        
        Args:
            profile_id: Profile identifier
            profile_data: Updated profile data
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        try:
            networking = profile_data.setdefault("networking", {})
            if not isinstance(networking, dict):
                networking = {}
                profile_data["networking"] = networking
            proxy_cfg = networking.get("proxy")
            if not isinstance(proxy_cfg, dict):
                networking["proxy"] = {}

            # Validate profile data
            validate_environment_profile(profile_data)
            
            # Check if profile exists
            existing = await self.get_profile(profile_id)
            if not existing:
                errors.append(f"Profile {profile_id} not found")
                return EnvironmentValidationResult(
                    valid=False,
                    errors=errors,
                    warnings=warnings
                )
            
            # Find profile file
            profile_file = None
            for pattern in [f"{profile_id}.yaml", f"{profile_id}.yml"]:
                candidate = self.profiles_dir / pattern
                if candidate.exists():
                    profile_file = candidate
                    break
            
            if not profile_file:
                errors.append(f"Profile file not found: {profile_id}")
                return EnvironmentValidationResult(
                    valid=False,
                    errors=errors,
                    warnings=warnings
                )
            
            # Update profile file
            import yaml
            with open(profile_file, 'w', encoding='utf-8') as f:
                yaml.dump(profile_data, f, default_flow_style=False, sort_keys=False)
            
            # Clear cache
            await self._invalidate_cache(profile_id)
            
            # Load and validate the updated profile
            profile = self._dict_to_profile(profile_data, profile_file)
            await self._validate_profile_content(profile, errors, warnings)
            
            logger.info(f"Updated environment profile: {profile_id}")
            
            return EnvironmentValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                profile=profile
            )
            
        except ValidationError as e:
            errors.append(f"Schema validation failed: {e.message}")
            return EnvironmentValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings
            )
        except Exception as e:
            errors.append(f"Failed to update profile: {str(e)}")
            return EnvironmentValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings
            )
    
    async def delete_profile(self, profile_id: str) -> bool:
        """
        Delete an environment profile.
        
        Args:
            profile_id: Profile identifier
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Find profile file
            profile_file = None
            for pattern in [f"{profile_id}.yaml", f"{profile_id}.yml"]:
                candidate = self.profiles_dir / pattern
                if candidate.exists():
                    profile_file = candidate
                    break
            
            if not profile_file:
                logger.warning(f"Profile file not found: {profile_id}")
                return False
            
            # Delete profile file
            profile_file.unlink()
            
            # Clear cache
            await self._invalidate_cache(profile_id)
            
            logger.info(f"Deleted environment profile: {profile_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete profile {profile_id}: {e}")
            return False
    
    async def _load_profile(self, file_path: Path) -> Optional[EnvironmentProfile]:
        """Load a profile from file."""
        try:
            async with self._lock:
                # Check cache first
                profile_id = file_path.stem
                
                # Check Redis cache
                if self.redis_manager:
                    try:
                        cached_data = await self._get_from_redis_cache(profile_id)
                        if cached_data:
                            return self._dict_to_profile(cached_data, file_path)
                    except Exception as e:
                        logger.warning(f"Redis cache error: {e}")
                
                # Check in-memory cache
                if profile_id in self._cache:
                    profile, timestamp = self._cache[profile_id]
                    if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                        return profile

                # Load and validate profile
                try:
                    profile_data = validate_environment_profile_file(file_path)
                except ValidationError as exc:
                    raw_text = file_path.read_text(encoding="utf-8")
                    raw_data = yaml.safe_load(raw_text) or {}
                    if not isinstance(raw_data, dict):
                        raise exc

                    networking = raw_data.setdefault("networking", {})
                    if not isinstance(networking, dict):
                        networking = {}
                        raw_data["networking"] = networking
                    proxy_cfg = networking.get("proxy")
                    if not isinstance(proxy_cfg, dict):
                        networking["proxy"] = {}

                    try:
                        validate_environment_profile(raw_data)
                    except ValidationError:
                        raise exc

                    with open(file_path, "w", encoding="utf-8") as f:
                        yaml.safe_dump(raw_data, f, default_flow_style=False, sort_keys=False)

                    logger.info(
                        "Auto-corrected networking.proxy definition for profile %s", profile_id
                    )
                    profile_data = raw_data

                profile = self._dict_to_profile(profile_data, file_path)

                # Cache the profile in memory
                self._cache[profile_id] = (profile, datetime.now())
                
                # Cache in Redis if available
                if self.redis_manager:
                    try:
                        await self._set_to_redis_cache(profile_id, profile_data)
                    except Exception as e:
                        logger.warning(f"Failed to cache in Redis: {e}")

                return profile

        except ValidationError as exc:
            logger.error(f"Schema validation failed for profile {file_path.stem}: {exc}")
            raise
        except Exception as e:
            logger.error(f"Failed to load profile from {file_path}: {e}")
            return None
    
    def _dict_to_profile(self, data: Dict[str, Any], file_path: Path) -> EnvironmentProfile:
        """Convert dictionary to EnvironmentProfile."""
        return EnvironmentProfile(
            id=data["id"],
            type=data["type"],
            display_name=data.get("display_name"),
            description=data.get("description"),
            networking=data.get("networking"),
            auth=data.get("auth"),
            policies=data.get("policies"),
            cluster=data.get("cluster"),
            defaults=data.get("defaults"),
            runbooks=data.get("runbooks"),
            notes=data.get("notes"),
            metadata=data.get("metadata"),
            ssh=data.get("ssh"),
            extensions=data.get("extensions"),
            last_updated=datetime.now(),
            file_path=file_path,
            data=data,
        )
    
    async def _validate_profile_content(self, profile: EnvironmentProfile, errors: List[str], warnings: List[str]):
        """Perform additional content validation."""
        # Check if runbooks exist
        if profile.runbooks:
            base_dir = profile.file_path.parent if profile.file_path else self.profiles_dir
            repo_root = base_dir.parent if base_dir.parent else base_dir
            for runbook in profile.runbooks:
                runbook_path = repo_root / runbook
                if not runbook_path.exists():
                    warnings.append(f"Runbook not found: {runbook}")
        
        # Check networking configuration
        if profile.networking and profile.networking.get("proxy"):
            proxy = profile.networking["proxy"]
            if proxy.get("http") and not proxy["http"].startswith(("http://", "https://")):
                errors.append("Proxy HTTP URL must start with http:// or https://")
            if proxy.get("https") and not proxy["https"].startswith(("http://", "https://")):
                errors.append("Proxy HTTPS URL must start with http:// or https://")
        
        # Check auth configuration
        if profile.auth:
            if not any(key in profile.auth for key in ["vault_role", "ssh_cert_role", "service_account"]):
                warnings.append("No authentication method specified")
        
        # Check policies
        if profile.policies:
            if profile.policies.get("risk_level") == "high" and not profile.policies.get("require_approval"):
                warnings.append("High risk level should require approval")
        
        # Check cluster configuration for k8s type
        if profile.type == "k8s" and not profile.cluster:
            warnings.append("Kubernetes environment should specify cluster configuration")
    
    async def health_check(self) -> bool:
        """Check if the environment service is healthy."""
        try:
            # Test profile directory access
            if not self.profiles_dir.exists():
                return False
            
            # Test Redis if available
            if self.redis_manager:
                if not await self.redis_manager.health_check():
                    logger.warning("Redis cache unavailable, using in-memory fallback")
            
            # Test loading profiles
            profiles = await self.list_profiles()
            return len(profiles) >= 0  # At least should not crash
            
        except Exception as e:
            logger.error(f"Environment service health check failed: {e}")
            return False
    
    async def _get_from_redis_cache(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get profile from Redis cache."""
        if not self.redis_manager:
            return None
        
        key = f"{self._redis_prefix}{profile_id}"
        cached = await self.redis_manager.get_json(key)
        if cached:
            logger.debug(f"Redis cache HIT for profile: {profile_id}")
        return cached
    
    async def _set_to_redis_cache(self, profile_id: str, profile_data: Dict[str, Any]) -> bool:
        """Set profile to Redis cache."""
        if not self.redis_manager:
            return False
        
        key = f"{self._redis_prefix}{profile_id}"
        success = await self.redis_manager.set_json(key, profile_data, expire=self.cache_ttl)
        if success:
            logger.debug(f"Cached profile in Redis: {profile_id}")
        return success
    
    async def _invalidate_cache(self, profile_id: str):
        """Invalidate both in-memory and Redis cache for a profile."""
        # Clear in-memory cache
        if profile_id in self._cache:
            del self._cache[profile_id]
        
        # Clear Redis cache
        if self.redis_manager:
            try:
                key = f"{self._redis_prefix}{profile_id}"
                await self.redis_manager.delete(key)
                logger.debug(f"Invalidated cache for profile: {profile_id}")
            except Exception as e:
                logger.warning(f"Failed to invalidate Redis cache: {e}")
