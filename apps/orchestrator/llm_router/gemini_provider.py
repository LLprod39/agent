"""Google Gemini LLM provider implementation."""

import asyncio
from typing import Any, Dict, List, AsyncGenerator
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .base import LLMProvider, LLMProviderType, LLMRequest, LLMResponse


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("Gemini API key is required")

        genai.configure(api_key=self.api_key)
        self.model_name = config.get("model", "gemini-1.5-flash")
        self.safety_settings = self._get_safety_settings(config)

    def _get_provider_type(self) -> LLMProviderType:
        return LLMProviderType.GEMINI

    def _get_safety_settings(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get safety settings for Gemini."""
        return [
            {
                "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            },
        ]

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Complete a request using Gemini."""
        try:
            model = genai.GenerativeModel(
                model_name=request.model or self.model_name,
                safety_settings=self.safety_settings,
            )

            # Prepare the prompt
            if request.system_message:
                prompt = f"{request.system_message}\n\n{request.prompt}"
            else:
                prompt = request.prompt

            # Generate content
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=request.temperature,
                    max_output_tokens=request.max_tokens,
                ),
            )

            return LLMResponse(
                content=response.text,
                model=request.model or self.model_name,
                provider=self.provider_type,
                usage={
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(response.text.split()),
                },
                metadata={
                    "safety_ratings": [
                        {
                            "category": rating.category.name,
                            "probability": rating.probability.name,
                        }
                        for rating in response.candidates[0].safety_ratings
                    ]
                    if response.candidates
                    else []
                },
            )
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {str(e)}")

    async def stream_complete(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream completion using Gemini."""
        try:
            model = genai.GenerativeModel(
                model_name=request.model or self.model_name,
                safety_settings=self.safety_settings,
            )

            # Prepare the prompt
            if request.system_message:
                prompt = f"{request.system_message}\n\n{request.prompt}"
            else:
                prompt = request.prompt

            # Generate content with streaming
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=request.temperature,
                    max_output_tokens=request.max_tokens,
                ),
                stream=True,
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            raise RuntimeError(f"Gemini streaming error: {str(e)}")

    async def health_check(self) -> bool:
        """Check if Gemini API is accessible."""
        try:
            model = genai.GenerativeModel(model_name=self.model_name)
            test_response = await asyncio.to_thread(
                model.generate_content,
                "Hello",
                generation_config=genai.types.GenerationConfig(max_output_tokens=1),
            )
            return bool(test_response.text)
        except Exception:
            return False

    def get_available_models(self) -> List[str]:
        """Get list of available Gemini models."""
        return [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-1.0-pro",
        ]
