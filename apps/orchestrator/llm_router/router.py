"""LLM Router for managing multiple providers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional, Sequence

from .base import LLMProvider, LLMProviderType, LLMRequest, LLMResponse


logger = logging.getLogger(__name__)


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

    def __init__(self, providers_config: Sequence[Any]):
        self.providers: Dict[str, LLMProvider] = {}
        self.provider_configs: List[ProviderConfig] = []
        normalized = [self._normalize_provider_config(entry) for entry in providers_config]
        self._setup_providers(normalized)

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
        self, request: LLMRequest, preferred_provider: Optional[str] = None
    ) -> LLMResponse:
        """Complete a request using the best available provider."""
        providers = self._get_available_providers()

        if preferred_provider and preferred_provider in self.providers:
            # Try preferred provider first
            try:
                provider = self.providers[preferred_provider]
                if await provider.health_check():
                    return await provider.complete(request)
            except Exception as e:
                logger.warning(f"Preferred provider {preferred_provider} failed: {e}")

        # Try providers in priority order
        for provider_config in providers:
            try:
                provider = self.providers[provider_config.name]
                if await provider.health_check():
                    return await provider.complete(request)
            except Exception as e:
                logger.warning(f"Provider {provider_config.name} failed: {e}")
                continue

        raise RuntimeError("No healthy LLM providers available")

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
