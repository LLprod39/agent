#!/usr/bin/env python
"""Test agent workflow from task to result."""

import asyncio
import logging
import sys
import json
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import get_settings
from apps.orchestrator.llm_router import LLMRouter, LLMRequest
from apps.orchestrator.agents import PlannerAgent, AgentRequest


async def test_gemini_connection():
    """Test direct Gemini connection."""
    logger.info("=" * 80)
    logger.info("TEST 1: Gemini API Connection")
    logger.info("=" * 80)

    try:
        settings = get_settings()
        logger.info(f"Loaded settings. Gemini enabled: {settings.enable_gemini_provider}")

        # Initialize LLM Router
        llm_router = LLMRouter(settings.llm_providers)

        logger.info(f"Available providers: {list(llm_router.providers.keys())}")

        # Check Gemini health
        gemini = llm_router.providers.get("gemini")
        if not gemini:
            logger.error("Gemini provider not found!")
            return False

        logger.info("Checking Gemini health...")
        is_healthy = await gemini.health_check()

        if not is_healthy:
            logger.error("Gemini health check FAILED")
            return False

        logger.info("✅ Gemini health check PASSED")

        # Test simple completion
        logger.info("\nTesting simple completion...")
        test_request = LLMRequest(
            prompt="Say 'Hello from Gemini!' and nothing else.",
            temperature=0.1,
            max_tokens=100
        )

        response = await llm_router.complete(test_request, preferred_provider="gemini")
        logger.info(f"✅ Gemini response: {response.content}")
        logger.info(f"   Model: {response.model}")
        logger.info(f"   Provider: {response.provider}")

        return True

    except Exception as e:
        logger.error(f"❌ Gemini test failed: {e}", exc_info=True)
        return False


async def test_planner_agent():
    """Test Planner Agent."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Planner Agent")
    logger.info("=" * 80)

    try:
        settings = get_settings()

        # Initialize LLM Router
        llm_router = LLMRouter(settings.llm_providers)

        # Initialize Planner Agent
        planner_config = {
            "name": "planner",
            "max_steps": 10,
            "temperature": 0.3
        }
        planner = PlannerAgent(planner_config, llm_router)

        logger.info("Planner agent initialized")

        # Create test request
        test_request = AgentRequest(
            task="Собери метрики CPU и использования памяти на сервере",
            context={
                "environment": "development",
                "server": "dev-vm-01"
            },
            environment_profile={
                "id": "dev-vm",
                "type": "vm",
                "policies": {
                    "risk_level": "low",
                    "require_approval": False
                }
            }
        )

        logger.info(f"\nSending request: {test_request.task}")

        # Process request
        response = await planner.process(test_request)

        logger.info(f"\n📋 Plan Status: {response.status}")
        logger.info(f"📋 Message: {response.content}")
        logger.info(f"📋 Requires Approval: {response.requires_approval}")
        logger.info(f"📋 Risk Level: {response.risk_level}")

        if response.metadata and "plan" in response.metadata:
            plan = response.metadata["plan"]
            logger.info(f"\n📝 Generated Plan:")
            logger.info(json.dumps(plan, indent=2, ensure_ascii=False))

            steps = plan.get("steps", [])
            logger.info(f"\n✅ Created plan with {len(steps)} steps:")
            for i, step in enumerate(steps, 1):
                logger.info(f"  {i}. {step.get('description')}")
                if step.get('command'):
                    logger.info(f"     Command: {step.get('command')}")
                logger.info(f"     Tool: {step.get('tool', 'N/A')}")
                logger.info(f"     Risk: {step.get('risk_level', 'N/A')}")

        if response.status.value == "completed":
            logger.info("\n✅ Planner test PASSED")
            return True
        else:
            logger.error(f"\n❌ Planner test FAILED: {response.error}")
            return False

    except Exception as e:
        logger.error(f"❌ Planner test failed: {e}", exc_info=True)
        return False


async def test_full_orchestration():
    """Test full orchestration workflow (simplified version without SSH)."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Full Orchestration (Planning Only)")
    logger.info("=" * 80)

    try:
        settings = get_settings()

        # Initialize components
        llm_router = LLMRouter(settings.llm_providers)

        planner_config = {"name": "planner"}
        planner = PlannerAgent(planner_config, llm_router)

        # Test different types of requests
        test_cases = [
            {
                "name": "Simple Metrics Collection",
                "task": "Проверь использование CPU и памяти",
                "context": {"environment": "dev"}
            },
            {
                "name": "Disk Space Check",
                "task": "Проверь свободное место на диске",
                "context": {"environment": "dev", "threshold": "80%"}
            },
            {
                "name": "Service Status",
                "task": "Проверь статус nginx сервиса",
                "context": {"environment": "dev", "service": "nginx"}
            }
        ]

        results = []

        for test_case in test_cases:
            logger.info(f"\n{'─' * 60}")
            logger.info(f"Test Case: {test_case['name']}")
            logger.info(f"Task: {test_case['task']}")

            request = AgentRequest(
                task=test_case["task"],
                context=test_case["context"]
            )

            response = await planner.process(request)

            success = response.status.value == "completed"
            results.append({
                "test": test_case["name"],
                "success": success,
                "status": response.status.value
            })

            if success:
                logger.info(f"✅ {test_case['name']}: PASSED")
                if response.metadata and "plan" in response.metadata:
                    steps_count = len(response.metadata["plan"].get("steps", []))
                    logger.info(f"   Generated {steps_count} steps")
            else:
                logger.error(f"❌ {test_case['name']}: FAILED - {response.error}")

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)

        passed = sum(1 for r in results if r["success"])
        total = len(results)

        for result in results:
            status_icon = "✅" if result["success"] else "❌"
            logger.info(f"{status_icon} {result['test']}: {result['status']}")

        logger.info(f"\nTotal: {passed}/{total} passed")

        return passed == total

    except Exception as e:
        logger.error(f"❌ Orchestration test failed: {e}", exc_info=True)
        return False


async def main():
    """Run all tests."""
    logger.info("🚀 Starting Agent Workflow Tests")
    logger.info("=" * 80)

    results = {}

    # Test 1: Gemini Connection
    results["gemini"] = await test_gemini_connection()

    if not results["gemini"]:
        logger.error("\n⚠️  Gemini connection failed. Skipping other tests.")
        logger.error("   Please check:")
        logger.error("   1. GEMINI_API_KEY in .env file")
        logger.error("   2. Internet connection")
        logger.error("   3. Gemini API quota")
        return

    # Test 2: Planner
    results["planner"] = await test_planner_agent()

    # Test 3: Full Orchestration
    results["orchestration"] = await test_full_orchestration()

    # Final Summary
    logger.info("\n" + "=" * 80)
    logger.info("FINAL RESULTS")
    logger.info("=" * 80)

    for test_name, success in results.items():
        status_icon = "✅" if success else "❌"
        logger.info(f"{status_icon} {test_name.upper()}: {'PASSED' if success else 'FAILED'}")

    all_passed = all(results.values())

    if all_passed:
        logger.info("\n🎉 ALL TESTS PASSED!")
        logger.info("\nNext steps:")
        logger.info("1. Test with real SSH connection to a server")
        logger.info("2. Test executor agent with actual command execution")
        logger.info("3. Test verifier agent with result validation")
    else:
        logger.error("\n❌ SOME TESTS FAILED")
        logger.error("Please check the logs above for details")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
    except Exception as e:
        logger.error(f"\n\nUnexpected error: {e}", exc_info=True)
