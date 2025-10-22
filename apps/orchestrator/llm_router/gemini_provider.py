"""Google Gemini LLM provider implementation."""

import asyncio
import time
from typing import Any, Dict, List, AsyncGenerator, Optional
from google import genai

from .base import LLMProvider, LLMProviderType, LLMRequest, LLMResponse


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Используем API ключ из конфигурации или ваш ключ по умолчанию
        self.api_key = config.get("api_key") or "AIzaSyBdMFRLoZPNVPyqSZ2CL4SoQQ7_4PnRpW4"
        if not self.api_key:
            raise ValueError("Gemini API key is required")

        # Initialize client with new SDK
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = config.get("model", "gemini-2.5-flash")
        self.safety_settings = self._get_safety_settings(config)
        self.request_timeout = config.get("timeout", 30)
        
        # Health check caching
        self._health_check_cache: Optional[bool] = None
        self._health_check_timestamp: float = 0
        self._health_check_ttl = 60  # Cache health check for 60 seconds

    def _get_provider_type(self) -> LLMProviderType:
        return LLMProviderType.GEMINI

    def _get_safety_settings(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get safety settings for Gemini."""
        # New SDK uses simpler safety settings
        return config.get("safety_settings", {})

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Complete a request using Gemini."""
        try:
            # Prepare the prompt
            if request.system_message:
                contents = f"{request.system_message}\n\n{request.prompt}"
            else:
                contents = request.prompt

            # Generate content using new SDK
            # Prepare config
            generate_kwargs = {
                'model': request.model or self.model_name,
                'contents': contents,
            }
            
            config_params = {}
            if request.temperature is not None:
                config_params['temperature'] = request.temperature
            if request.max_tokens:
                config_params['max_output_tokens'] = request.max_tokens
            
            if config_params:
                generate_kwargs['config'] = config_params
            
            # Execute with timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.models.generate_content,
                    **generate_kwargs
                ),
                timeout=self.request_timeout
            )

            content_text = getattr(response, "text", None)
            if not content_text:
                parts: List[str] = []
                for candidate in getattr(response, "candidates", []) or []:
                    content = getattr(candidate, "content", None)
                    for part in getattr(content, "parts", []) or []:
                        value = getattr(part, "text", None)
                        if value:
                            parts.append(value)
                content_text = "\n".join(parts).strip()

            if not content_text:
                content_text = ""

            prompt_tokens = len(contents.split()) if contents else 0
            completion_tokens = len(content_text.split()) if content_text else 0

            return LLMResponse(
                content=content_text,
                model=request.model or self.model_name,
                provider=self.provider_type,
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                },
                metadata={
                    "finish_reason": getattr(response, "finish_reason", None),
                },
            )
        except asyncio.TimeoutError:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Gemini API request timed out after {self.request_timeout}s")
            # Invalidate health check cache on timeout
            self._health_check_cache = False
            self._health_check_timestamp = time.time()
            raise RuntimeError(f"Gemini API request timed out after {self.request_timeout}s")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Gemini API detailed error: {e}")
            logger.error(f"Request model: {request.model or self.model_name}")
            logger.error(f"Request prompt length: {len(request.prompt)}")
            if hasattr(e, 'response'):
                logger.error(f"Response status: {getattr(e.response, 'status_code', 'N/A')}")
                logger.error(f"Response body: {getattr(e.response, 'text', 'N/A')}")
            # Invalidate health check cache on error
            self._health_check_cache = False
            self._health_check_timestamp = time.time()
            raise RuntimeError(f"Gemini API error: {str(e)}")

    async def stream_complete(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream completion using Gemini."""
        try:
            # Prepare the prompt
            if request.system_message:
                contents = f"{request.system_message}\n\n{request.prompt}"
            else:
                contents = request.prompt

            # Generate content with streaming using new SDK
            # Note: Streaming may need different API in new SDK
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=request.model or self.model_name,
                contents=contents,
            )

            # For now, yield the complete response
            # TODO: Implement true streaming when SDK supports it
            if response.text:
                yield response.text

        except Exception as e:
            raise RuntimeError(f"Gemini streaming error: {str(e)}")

    async def health_check(self) -> bool:
        """Check if Gemini API is accessible with caching."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Check cached result
        now = time.time()
        if self._health_check_cache is not None and (now - self._health_check_timestamp) < self._health_check_ttl:
            logger.debug(f"Using cached health check result: {self._health_check_cache}")
            return self._health_check_cache
        
        try:
            # Check if API key is set
            if not self.api_key or self.api_key.startswith("${"):
                logger.warning("Gemini API key not configured properly")
                self._health_check_cache = False
                self._health_check_timestamp = now
                return False
            
            # Simple test request with timeout
            try:
                test_response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.models.generate_content,
                        model=self.model_name,
                        contents="test",
                    ),
                    timeout=10.0  # 10 second timeout for health check
                )
                
                if test_response.text:
                    logger.info(f"Gemini health check passed with model {self.model_name}")
                    self._health_check_cache = True
                    self._health_check_timestamp = now
                    return True
                
                self._health_check_cache = False
                self._health_check_timestamp = now
                return False
                
            except asyncio.TimeoutError:
                logger.error("Gemini health check timed out")
                self._health_check_cache = False
                self._health_check_timestamp = now
                return False
                
        except Exception as e:
            logger.error(f"Gemini health check failed: {str(e)}")
            self._health_check_cache = False
            self._health_check_timestamp = now
            return False

    def get_available_models(self) -> List[str]:
        """Get list of available Gemini models."""
        return [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash-exp",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
