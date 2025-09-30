"""Deterministic local LLM provider used for development and tests."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List

from .base import LLMProvider, LLMProviderType, LLMRequest, LLMResponse


class LocalProvider(LLMProvider):
    """A simple provider that returns deterministic JSON payloads."""

    def _get_provider_type(self) -> LLMProviderType:
        return LLMProviderType.LOCAL

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Return a deterministic response based on the system prompt."""
        content = self._render_response(request)
        content_str = json.dumps(content)
        metadata = {"mode": self.config.get("mode", "deterministic")}

        return LLMResponse(
            content=content_str,
            model=self.config.get("model", "local-simulator"),
            provider=self.provider_type,
            usage={"prompt_tokens": 0, "completion_tokens": len(content_str.split())},
            metadata=metadata,
        )

    async def stream_complete(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream the deterministic response."""
        response = await self.complete(request)
        yield response.content

    async def health_check(self) -> bool:
        """The local provider is always considered healthy."""
        return True

    def get_available_models(self) -> List[str]:
        """Return the available pseudo-models."""
        return [self.config.get("model", "local-simulator")]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _render_response(self, request: LLMRequest) -> Dict[str, Any]:
        system_message = (request.system_message or "").lower()

        if "planning agent" in system_message:
            return self._build_plan(request)
        if "verification agent" in system_message:
            return self._build_verification(request)

        return {"message": "Local provider response"}

    def _build_plan(self, request: LLMRequest) -> Dict[str, Any]:
        task_line = next((line for line in request.prompt.splitlines() if line.startswith("Task:")), request.prompt)
        task_description = task_line.replace("Task:", "").strip() or "Execute the requested task"

        step_id_prefix = self.config.get("step_prefix", "step")

        return {
            "description": task_description,
            "steps": [
                {
                    "id": f"{step_id_prefix}-1",
                    "description": f"Analyse and address: {task_description}",
                    "command": None,
                    "tool": "generic",
                    "parameters": {},
                    "risk_level": "low",
                    "requires_approval": False,
                    "dependencies": [],
                }
            ],
            "estimated_duration": self.config.get("estimated_duration", 60),
            "risk_level": "low",
            "requires_approval": False,
        }

    def _build_verification(self, request: LLMRequest) -> Dict[str, Any]:
        return {
            "verification_status": "success",
            "verification_passed": True,
            "summary": "Execution results look healthy based on local provider heuristics.",
            "details": {
                "execution_check": "passed",
                "output_validation": "passed",
                "state_verification": "passed",
                "error_analysis": "passed",
            },
            "issues": [],
            "recommendations": ["Review logs if additional validation is required."],
            "confidence": 0.9,
        }

