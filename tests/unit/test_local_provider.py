"""Unit tests for the LocalProvider implementation."""

import asyncio
import json
import unittest

from apps.orchestrator.llm_router.base import LLMRequest
from apps.orchestrator.llm_router.local_provider import LocalProvider


class LocalProviderTests(unittest.TestCase):
    """Ensure deterministic responses from the local provider."""

    def setUp(self) -> None:
        self.provider = LocalProvider({"model": "local-test"})

    def test_planner_response_contains_generic_step(self):
        request = LLMRequest(
            prompt="Task: verify deployment", system_message="You are a DevOps planning agent."
        )
        response = asyncio.run(self.provider.complete(request))
        payload = json.loads(response.content)

        self.assertEqual(response.model, "local-test")
        self.assertIn("steps", payload)
        self.assertEqual(len(payload["steps"]), 1)
        step = payload["steps"][0]
        self.assertEqual(step["tool"], "generic")
        self.assertFalse(step["requires_approval"])

    def test_verifier_response_declares_success(self):
        request = LLMRequest(
            prompt="Verify results", system_message="You are a DevOps verification agent."
        )
        response = asyncio.run(self.provider.complete(request))
        payload = json.loads(response.content)

        self.assertTrue(payload.get("verification_passed"))
        self.assertEqual(payload.get("verification_status"), "success")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
