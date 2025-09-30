"""Integration tests for orchestrator using the local provider."""

import asyncio
import unittest

from apps.orchestrator import Orchestrator, OrchestrationRequest
from apps.orchestrator.agents.base import TaskStatus
from apps.orchestrator.llm_router import LLMRouter
from config.settings import get_settings


class OrchestratorFlowTests(unittest.TestCase):
    """Validate the end-to-end orchestration loop with the local provider."""

    def setUp(self) -> None:
        settings = get_settings()
        provider_configs = [provider.model_dump() for provider in settings.llm_providers if provider.enabled]
        self.router = LLMRouter(provider_configs)
        self.orchestrator = Orchestrator(settings.orchestrator.model_dump(), self.router)

    def test_simple_task_completes_successfully(self):
        request = OrchestrationRequest(
            task="Check disk usage",
            context={"expected_outcomes": {"stdout_contains": "disk"}},
        )

        response = asyncio.run(self.orchestrator.process_request(request))

        self.assertEqual(response.status, TaskStatus.COMPLETED)
        self.assertEqual(len(response.results), 3)
        planner_result = response.results[0]
        self.assertEqual(planner_result["agent"], "planner")
        executor_result = response.results[1]
        self.assertEqual(executor_result["agent"], "executor")
        verifier_result = response.results[2]
        self.assertEqual(verifier_result["agent"], "verifier")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
