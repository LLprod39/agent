"""LLM Router module for managing different LLM providers."""

from .base import LLMProvider, LLMRequest, LLMResponse
from .router import LLMRouter

# Lazy imports to avoid dependency issues
def get_gemini_provider():
    """Get Gemini provider with lazy import."""
    from .gemini_provider import GeminiProvider
    return GeminiProvider

def get_ollama_provider():
    """Get Ollama provider with lazy import."""
    from .ollama_provider import OllamaProvider
    return OllamaProvider

def get_local_provider():
    """Get the local development provider."""
    from .local_provider import LocalProvider
    return LocalProvider

__all__ = [
    "LLMProvider",
    "LLMResponse", 
    "LLMRequest",
    "LLMRouter",
    "get_gemini_provider",
    "get_ollama_provider",
    "get_local_provider",
]
