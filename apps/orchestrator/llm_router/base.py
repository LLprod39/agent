"""Base classes for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, AsyncGenerator
from enum import Enum


class LLMProviderType(Enum):
    """Types of LLM providers."""

    GEMINI = "gemini"
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    content: str
    model: str
    provider: LLMProviderType
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMRequest:
    """Request to LLM provider."""

    prompt: str
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    system_message: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider_type = self._get_provider_type()

    @abstractmethod
    def _get_provider_type(self) -> LLMProviderType:
        """Get the provider type."""
        pass

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Complete a request and return response."""
        pass

    @abstractmethod
    async def stream_complete(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream completion response."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is healthy."""
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        pass
