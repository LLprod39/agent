"""Unit tests for Command Policy integration."""

import unittest
import asyncio
from typing import Dict, Any

from apps.orchestrator.policies.command_policies import CommandPolicyEngine
from apps.orchestrator.policies.base import PolicyResult
from apps.orchestrator.agents.executor_agent import ExecutorAgent
from apps.orchestrator.agents.base import AgentRequest, TaskStep
from apps.orchestrator.llm_router.local_provider import LocalProvider
from apps.orchestrator.llm_router import LLMRouter


class CommandPolicyEngineTests(unittest.TestCase):
    """Tests for CommandPolicyEngine."""

    def setUp(self):
        """Setup test policy engine."""
        self.policy_config = {
            "blocked_commands": [
                "rm -rf /",
                "shutdown",
                "reboot",
            ],
            "approval_required_commands": [
                "kubectl delete",
                "docker rm",
            ],
            "readonly_commands": [
                "kubectl get",
                "docker ps",
            ],
        }
        self.engine = CommandPolicyEngine(self.policy_config)

    def test_allow_safe_command(self):
        """Test that safe commands are allowed."""
        async def test():
            context = {
                "command": "kubectl get pods",
                "environment": {"id": "dev"},
                "user_id": "test_user",
            }
            result = await self.engine.evaluate(context)
            self.assertEqual(result.result, PolicyResult.ALLOW)
            self.assertEqual(result.risk_level, "low")
            self.assertEqual(len(result.violations), 0)

        asyncio.run(test())

    def test_block_dangerous_command(self):
        """Test that dangerous commands are blocked."""
        async def test():
            context = {
                "command": "rm -rf /",
                "environment": {"id": "prod"},
                "user_id": "test_user",
            }
            result = await self.engine.evaluate(context)
            self.assertEqual(result.result, PolicyResult.DENY)
            self.assertEqual(result.risk_level, "high")
            self.assertGreater(len(result.violations), 0)

        asyncio.run(test())

    def test_require_approval_for_destructive_command(self):
        """Test that destructive commands require approval."""
        async def test():
            context = {
                "command": "kubectl delete pod nginx",
                "environment": {"id": "prod"},
                "user_id": "test_user",
            }
            result = await self.engine.evaluate(context)
            self.assertEqual(result.result, PolicyResult.REQUIRE_APPROVAL)
            self.assertTrue(result.requires_approval)
            self.assertGreater(len(result.violations), 0)

        asyncio.run(test())

    def test_block_dangerous_pattern(self):
        """Test that dangerous patterns are blocked."""
        async def test():
            context = {
                "command": "dd if=/dev/zero of=/dev/sda",
                "environment": {"id": "prod"},
                "user_id": "test_user",
            }
            result = await self.engine.evaluate(context)
            self.assertEqual(result.result, PolicyResult.DENY)
            self.assertEqual(result.risk_level, "high")

        asyncio.run(test())

    def test_empty_command_blocked(self):
        """Test that empty commands are blocked."""
        async def test():
            context = {
                "command": "",
                "environment": {"id": "dev"},
                "user_id": "test_user",
            }
            result = await self.engine.evaluate(context)
            self.assertEqual(result.result, PolicyResult.DENY)

        asyncio.run(test())

    def test_health_check(self):
        """Test policy engine health check."""
        async def test():
            healthy = await self.engine.health_check()
            self.assertTrue(healthy)

        asyncio.run(test())


class ExecutorAgentPolicyIntegrationTests(unittest.TestCase):
    """Tests for ExecutorAgent policy integration."""

    def setUp(self):
        """Setup test executor agent with policies."""
        # Create LLM router with local provider
        local_provider_config = {
            "name": "local",
            "type": "local",
            "priority": 100,
            "enabled": True,
            "config": {},
        }
        llm_router = LLMRouter([local_provider_config])

        # Create policy engine
        policy_config = {
            "blocked_commands": ["rm -rf /", "shutdown"],
            "approval_required_commands": ["kubectl delete"],
        }
        policy_engine = CommandPolicyEngine(policy_config)

        # Create executor agent with policy enforcement
        executor_config = {
            "enforce_policies": True,
            "policy": policy_config,
        }
        self.executor = ExecutorAgent(
            config=executor_config,
            llm_router=llm_router,
            policy_engine=policy_engine,
        )

    def test_executor_allows_safe_command(self):
        """Test that executor allows safe commands."""
        async def test():
            step = TaskStep(
                id="test_step",
                description="Get pods",
                command="kubectl get pods",
                tool="generic",  # Use generic tool for simulation
            )

            request = AgentRequest(
                task="Get pods",
                context={
                    "step": step.__dict__,
                    "approved": False,
                },
                environment_profile={"id": "dev"},
            )

            result = await self.executor._execute_step(step, request)
            self.assertTrue(result["success"])

        asyncio.run(test())

    def test_executor_blocks_dangerous_command(self):
        """Test that executor blocks dangerous commands."""
        async def test():
            step = TaskStep(
                id="test_step",
                description="Remove root",
                command="rm -rf /",
                tool="ssh",
            )

            request = AgentRequest(
                task="Remove root",
                context={
                    "step": step.__dict__,
                    "approved": False,
                },
                environment_profile={"id": "prod"},
            )

            result = await self.executor._execute_step(step, request)
            self.assertFalse(result["success"])
            self.assertTrue(result.get("policy_violation", False))
            self.assertIn("blocked", result["error"].lower())

        asyncio.run(test())

    def test_executor_requires_approval(self):
        """Test that executor requires approval for destructive commands."""
        async def test():
            step = TaskStep(
                id="test_step",
                description="Delete pod",
                command="kubectl delete pod nginx",
                tool="kubectl",
            )

            # Without approval
            request = AgentRequest(
                task="Delete pod",
                context={
                    "step": step.__dict__,
                    "approved": False,
                },
                environment_profile={"id": "prod"},
            )

            result = await self.executor._execute_step(step, request)
            self.assertFalse(result["success"])
            self.assertTrue(result.get("requires_approval", False))
            self.assertIn("approval", result["error"].lower())

        asyncio.run(test())

    def test_executor_allows_with_approval(self):
        """Test that executor allows commands with approval."""
        async def test():
            step = TaskStep(
                id="test_step",
                description="Delete pod",
                command="kubectl delete pod nginx",
                tool="generic",  # Use generic tool for simulation
            )

            # With approval
            request = AgentRequest(
                task="Delete pod",
                context={
                    "step": step.__dict__,
                    "approved": True,
                },
                environment_profile={"id": "prod"},
            )

            result = await self.executor._execute_step(step, request)
            # Should succeed (simulated execution)
            self.assertTrue(result["success"])

        asyncio.run(test())

    def test_executor_policy_disabled(self):
        """Test that policies can be disabled."""
        async def test():
            # Create executor with policies disabled
            executor_config = {
                "enforce_policies": False,
            }
            llm_router = LLMRouter(
                [
                    {
                        "name": "local",
                        "type": "local",
                        "priority": 100,
                        "enabled": True,
                        "config": {},
                    }
                ]
            )
            executor = ExecutorAgent(config=executor_config, llm_router=llm_router)

            step = TaskStep(
                id="test_step",
                description="Dangerous command",
                command="rm -rf /",
                tool="generic",  # Use generic tool for simulation
            )

            request = AgentRequest(
                task="Dangerous",
                context={
                    "step": step.__dict__,
                },
                environment_profile={"id": "dev"},
            )

            result = await executor._execute_step(step, request)
            # Should succeed because policies are disabled (simulated)
            self.assertTrue(result["success"])

        asyncio.run(test())


if __name__ == "__main__":
    unittest.main()
