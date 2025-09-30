"""LLM Router for managing multiple providers."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional, Sequence

from .base import LLMProvider, LLMProviderType, LLMRequest, LLMResponse


logger = logging.getLogger(__name__)

# Import metrics tracking (optional)
try:
    from ...api.middleware.prometheus import track_llm_request, track_llm_tokens, track_cache_hit, track_cache_miss
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.debug("Prometheus metrics not available in LLM Router")

# LLMCache is imported dynamically to avoid circular dependencies
LLMCache = None
try:
    from ...cache import LLMCache as _LLMCache
    LLMCache = _LLMCache
except ImportError:
    logger.warning("LLMCache not available - caching will be disabled")


@dataclass
class ProviderConfig:
    """Configuration for a provider."""

    name: str
    provider_type: LLMProviderType
    config: Dict[str, Any]
    priority: int = 0
    enabled: bool = True


class LLMRouter:
    """Router for managing multiple LLM providers with fallback."""

    def __init__(self, providers_config: Sequence[Any], llm_cache=None):
        self.providers: Dict[str, LLMProvider] = {}
        self.provider_configs: List[ProviderConfig] = []
        self.llm_cache = llm_cache
        self.cache_enabled = llm_cache is not None
        normalized = [self._normalize_provider_config(entry) for entry in providers_config]
        self._setup_providers(normalized)
        
        if self.cache_enabled:
            logger.info("LLM caching enabled")
        else:
            logger.info("LLM caching disabled")

    def _normalize_provider_config(self, entry: Any) -> Dict[str, Any]:
        if hasattr(entry, "model_dump"):
            return entry.model_dump()
        if isinstance(entry, dict):
            return entry
        raise TypeError(f"Unsupported provider config type: {type(entry)!r}")

    def _setup_providers(self, providers_config: List[Dict[str, Any]]):
        """Setup providers from configuration."""
        for config in providers_config:
            try:
                provider_type = LLMProviderType(config["type"])
            except ValueError:
                logger.warning("Unsupported provider type in config: %s", config.get("type"))
                continue

            provider_name = config.get("name")
            if not provider_name:
                logger.warning("Skipping provider with missing name: %s", config)
                continue

            if not config.get("enabled", True):
                logger.info("Provider %s disabled via configuration", provider_name)
                continue

            provider_config = config.get("config", {})

            try:
                provider = self._instantiate_provider(provider_type, provider_config)
            except ImportError as exc:
                logger.warning(
                    "Provider %s skipped because required dependency is missing: %s",
                    provider_name,
                    exc,
                )
                continue
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.error(
                    "Failed to initialise provider %s (%s): %s",
                    provider_name,
                    provider_type.value,
                    exc,
                )
                continue

            self.providers[provider_name] = provider
            self.provider_configs.append(
                ProviderConfig(
                    name=provider_name,
                    provider_type=provider_type,
                    config=provider_config,
                    priority=config.get("priority", 0),
                    enabled=config.get("enabled", True),
                )
            )

            logger.info(
                f"Registered provider: {provider_name} ({provider_type.value})"
            )

        if not self.provider_configs:
            logger.error("No LLM providers registered after configuration parsing")

    def _instantiate_provider(
        self, provider_type: LLMProviderType, config: Dict[str, Any]
    ) -> LLMProvider:
        if provider_type == LLMProviderType.GEMINI:
            from .gemini_provider import GeminiProvider
            return GeminiProvider(config)
        if provider_type == LLMProviderType.OLLAMA:
            from .ollama_provider import OllamaProvider
            return OllamaProvider(config)
        if provider_type == LLMProviderType.LOCAL:
            from .local_provider import LocalProvider
            return LocalProvider(config)
        raise ValueError(f"Provider type {provider_type.value} is not supported")

    def _get_available_providers(self) -> List[ProviderConfig]:
        """Get available providers sorted by priority."""
        return sorted(
            [config for config in self.provider_configs if config.enabled],
            key=lambda x: x.priority,
            reverse=True,
        )

    async def complete(
        self, request: LLMRequest, preferred_provider: Optional[str] = None, use_cache: bool = True
    ) -> LLMResponse:
        """Complete a request using the best available provider."""
        start_time = time.time()
        
        # Check cache first if enabled
        if self.cache_enabled and use_cache:
            try:
                cached_response = await self.llm_cache.get(
                    prompt=request.prompt,
                    model=request.model or "default",
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    system_message=request.system_message,
                )
                
                if cached_response:
                    logger.debug("Cache HIT for LLM request")
                    
                    # Track cache hit metric
                    if METRICS_AVAILABLE:
                        track_cache_hit("llm")
                    
                    # Reconstruct LLMResponse from cached data
                    return LLMResponse(
                        content=cached_response["content"],
                        model=cached_response["model"],
                        provider=LLMProviderType(cached_response["provider"]),
                        usage=cached_response.get("usage", {}),
                        metadata={"cached": True, **cached_response.get("metadata", {})}
                    )
                else:
                    # Track cache miss
                    if METRICS_AVAILABLE:
                        track_cache_miss("llm")
            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}")
        
        providers = self._get_available_providers()

        if preferred_provider and preferred_provider in self.providers:
            # Try preferred provider first
            try:
                provider = self.providers[preferred_provider]
                if await provider.health_check():
                    response = await provider.complete(request)
                    await self._cache_response(request, response, use_cache)
                    return response
            except Exception as e:
                logger.warning(f"Preferred provider {preferred_provider} failed: {e}")

        # Try providers in priority order
        for provider_config in providers:
            try:
                provider = self.providers[provider_config.name]
                if await provider.health_check():
                    response = await provider.complete(request)
                    await self._cache_response(request, response, use_cache)
                    
                    # Track metrics
                    duration = time.time() - start_time
                    if METRICS_AVAILABLE:
                        track_llm_request(
                            provider=provider_config.name,
                            model=response.model,
                            status="success",
                            duration=duration
                        )
                        
                        # Track token usage if available
                        if response.usage:
                            if "prompt_tokens" in response.usage:
                                track_llm_tokens(
                                    provider=provider_config.name,
                                    model=response.model,
                                    token_type="prompt",
                                    count=response.usage["prompt_tokens"]
                                )
                            if "completion_tokens" in response.usage:
                                track_llm_tokens(
                                    provider=provider_config.name,
                                    model=response.model,
                                    token_type="completion",
                                    count=response.usage["completion_tokens"]
                                )
                    
                    return response
            except Exception as e:
                logger.warning(f"Provider {provider_config.name} failed: {e}")
                
                # Track failed request
                if METRICS_AVAILABLE:
                    duration = time.time() - start_time
                    track_llm_request(
                        provider=provider_config.name,
                        model=request.model or "unknown",
                        status="failed",
                        duration=duration
                    )
                continue

        raise RuntimeError("No healthy LLM providers available")
    
    async def _cache_response(self, request: LLMRequest, response: LLMResponse, use_cache: bool = True):
        """Cache the response if caching is enabled."""
        if self.cache_enabled and use_cache:
            try:
                await self.llm_cache.set(
                    prompt=request.prompt,
                    model=response.model,
                    response={
                        "content": response.content,
                        "model": response.model,
                        "provider": response.provider.value,
                        "usage": response.usage,
                        "metadata": response.metadata,
                    },
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    system_message=request.system_message,
                )
                logger.debug("Cached LLM response")
            except Exception as e:
                logger.warning(f"Failed to cache response: {e}")

    async def stream_complete(
        self, request: LLMRequest, preferred_provider: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream completion using the best available provider."""
        providers = self._get_available_providers()

        if preferred_provider and preferred_provider in self.providers:
            # Try preferred provider first
            try:
                provider = self.providers[preferred_provider]
                if await provider.health_check():
                    async for chunk in provider.stream_complete(request):
                        yield chunk
                    return
            except Exception as e:
                logger.warning(f"Preferred provider {preferred_provider} failed: {e}")

        # Try providers in priority order
        for provider_config in providers:
            try:
                provider = self.providers[provider_config.name]
                if await provider.health_check():
                    async for chunk in provider.stream_complete(request):
                        yield chunk
                    return
            except Exception as e:
                logger.warning(f"Provider {provider_config.name} failed: {e}")
                continue

        raise RuntimeError("No healthy LLM providers available")

    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all providers."""
        results = {}
        for name, provider in self.providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = False
        return results

    def get_available_models(self) -> Dict[str, List[str]]:
        """Get available models from all providers."""
        models = {}
        for name, provider in self.providers.items():
            try:
                models[name] = provider.get_available_models()
            except Exception as e:
                logger.error(f"Failed to get models for {name}: {e}")
                models[name] = []
        return models
    
    async def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics if caching is enabled."""
        if not self.cache_enabled:
            return None
        
        try:
            return await self.llm_cache.get_stats()
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return None
    
    async def clear_cache(self) -> int:
        """Clear the LLM cache."""
        if not self.cache_enabled:
            return 0
        
        try:
            return await self.llm_cache.clear_all()
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0
