"""Verifier Agent for verifying execution results."""

import json
from typing import Any, Dict

from .base import BaseAgent, AgentType, AgentRequest, AgentResponse, TaskStatus
from ..llm_router import LLMRouter, LLMRequest


class VerifierAgent(BaseAgent):
    """Agent responsible for verifying execution results."""

    def __init__(self, config: Dict[str, Any], llm_router: LLMRouter):
        super().__init__(AgentType.VERIFIER, config)
        self.llm_router = llm_router
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the verifier."""
        return """You are a DevOps verification agent. Your role is to verify that executed steps have achieved their intended results.

Guidelines:
1. Analyze execution results and compare with expected outcomes
2. Check for error patterns and anomalies
3. Validate system state changes
4. Identify potential issues or risks
5. Provide clear verification status and recommendations
6. Suggest remediation steps if verification fails

Verification criteria:
- Command execution success/failure
- Expected output patterns
- System state changes
- Error logs and warnings
- Performance metrics
- Security implications

Output format (JSON):
{
    "verification_status": "success|failure|warning",
    "summary": "Brief summary of verification results",
    "details": {
        "execution_check": "passed|failed|warning",
        "output_validation": "passed|failed|warning", 
        "state_verification": "passed|failed|warning",
        "error_analysis": "passed|failed|warning"
    },
    "issues": [
        {
            "type": "error|warning|info",
            "message": "Description of the issue",
            "severity": "low|medium|high",
            "recommendation": "Suggested action"
        }
    ],
    "recommendations": [
        "Next steps or actions to take"
    ],
    "confidence": 0.95
}"""

    async def process(self, request: AgentRequest) -> AgentResponse:
        """Process a verification request."""
        try:
            # Extract execution results
            execution_results = request.context.get("execution_results", {})
            expected_outcomes = request.context.get("expected_outcomes", {})

            if not execution_results:
                return self._create_response(
                    content="No execution results provided for verification",
                    status=TaskStatus.FAILED,
                    error="Missing execution results in request context",
                )

            # Build verification prompt
            prompt = self._build_verification_prompt(
                execution_results, expected_outcomes, request
            )

            # Get LLM response
            llm_request = LLMRequest(
                prompt=prompt,
                system_message=self.system_prompt,
                temperature=0.2,  # Low temperature for consistent verification
                max_tokens=1500,
            )

            response = await self.llm_router.complete(llm_request)

            # Parse the response
            try:
                verification_data = json.loads(response.content)

                # Determine overall status
                status = self._determine_status(verification_data)

                return self._create_response(
                    content=verification_data.get("summary", "Verification completed"),
                    status=status,
                    metadata={
                        "verification": verification_data,
                        "confidence": verification_data.get("confidence", 0.0),
                    },
                )

            except json.JSONDecodeError as e:
                return self._create_response(
                    content="Failed to parse verification response",
                    status=TaskStatus.FAILED,
                    error=f"JSON parsing error: {str(e)}",
                )

        except Exception as e:
            return self._create_response(
                content="Verification failed", status=TaskStatus.FAILED, error=str(e)
            )

    def _build_verification_prompt(
        self,
        execution_results: Dict[str, Any],
        expected_outcomes: Dict[str, Any],
        request: AgentRequest,
    ) -> str:
        """Build the verification prompt with context."""
        # Helper function to safely serialize objects
        def safe_json_dumps(obj):
            try:
                return json.dumps(obj, indent=2, default=str)
            except:
                return str(obj)
        
        prompt_parts = [
            "Please verify the following execution results:",
            "",
            "Execution Results:",
            safe_json_dumps(execution_results),
        ]

        if expected_outcomes:
            prompt_parts.extend(
                ["", "Expected Outcomes:", safe_json_dumps(expected_outcomes)]
            )

        if request.environment_profile:
            prompt_parts.extend(
                [
                    "",
                    "Environment Profile:",
                    safe_json_dumps(request.environment_profile),
                ]
            )

        prompt_parts.extend(
            ["", "Please analyze these results and provide verification status."]
        )

        return "\n".join(prompt_parts)

    def _determine_status(self, verification_data: Dict[str, Any]) -> TaskStatus:
        """Determine overall status from verification data."""
        # Check for verification_passed field first
        verification_passed = verification_data.get("verification_passed", False)
        if verification_passed:
            return TaskStatus.COMPLETED
            
        # Fallback to verification_status field
        verification_status = verification_data.get("verification_status", "failure")

        if verification_status == "success":
            return TaskStatus.COMPLETED
        elif verification_status == "warning":
            return TaskStatus.COMPLETED  # Warnings don't fail the task
        else:
            return TaskStatus.FAILED

    async def health_check(self) -> bool:
        """Check if verifier agent is healthy."""
        try:
            # Test with a simple verification request
            test_request = AgentRequest(
                task="Test verification",
                context={
                    "execution_results": {
                        "command": "echo 'test'",
                        "exit_code": 0,
                        "output": "test",
                        "success": True,
                    },
                    "expected_outcomes": {"exit_code": 0, "output_contains": "test"},
                },
            )

            response = await self.process(test_request)
            return response.status == TaskStatus.COMPLETED
        except Exception:
            return False
