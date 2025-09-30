"""Ollama LLM provider implementation."""

import json
from typing import Any, Dict, List, AsyncGenerator
import httpx

from .base import LLMProvider, LLMProviderType, LLMRequest, LLMResponse


class OllamaProvider(LLMProvider):
    """Ollama LLM provider for local models."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.default_model = config.get("model", "llama3")
        self.timeout = config.get("timeout", 30.0)

    def _get_provider_type(self) -> LLMProviderType:
        return LLMProviderType.OLLAMA

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Complete a request using Ollama."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": request.model or self.default_model,
                    "prompt": request.prompt,
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens,
                    },
                }

                if request.system_message:
                    payload["system"] = request.system_message

                response = await client.post(
                    f"{self.base_url}/api/generate", json=payload
                )
                response.raise_for_status()

                result = response.json()

                return LLMResponse(
                    content=result["response"],
                    model=request.model or self.default_model,
                    provider=self.provider_type,
                    usage={
                        "prompt_tokens": result.get("prompt_eval_count", 0),
                        "completion_tokens": result.get("eval_count", 0),
                    },
                    metadata={
                        "total_duration": result.get("total_duration"),
                        "load_duration": result.get("load_duration"),
                        "prompt_eval_duration": result.get("prompt_eval_duration"),
                        "eval_duration": result.get("eval_duration"),
                    },
                )
        except Exception as e:
            raise RuntimeError(f"Ollama API error: {str(e)}")

    async def stream_complete(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream completion using Ollama."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": request.model or self.default_model,
                    "prompt": request.prompt,
                    "stream": True,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens,
                    },
                }

                if request.system_message:
                    payload["system"] = request.system_message

                async with client.stream(
                    "POST", f"{self.base_url}/api/generate", json=payload
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            raise RuntimeError(f"Ollama streaming error: {str(e)}")

    async def health_check(self) -> bool:
        """Check if Ollama is accessible."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models."""
        # This would typically fetch from Ollama API, but for now return common models
        return [
            "llama3",
            "llama3:8b",
            "llama3:70b",
            "mixtral",
            "codellama",
            "mistral",
        ]
