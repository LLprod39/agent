"""Planner Agent for breaking down tasks into steps."""

import json
import uuid
from typing import Any, Dict

from .base import (
    BaseAgent,
    AgentType,
    AgentRequest,
    AgentResponse,
    TaskStatus,
    TaskStep,
    TaskPlan,
)
from ..llm_router import LLMRouter, LLMRequest


class PlannerAgent(BaseAgent):
    """Agent responsible for planning and breaking down tasks."""

    def __init__(self, config: Dict[str, Any], llm_router: LLMRouter):
        super().__init__(AgentType.PLANNER, config)
        self.llm_router = llm_router
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the planner."""
        return """You are a DevOps planning agent. Your role is to break down user requests into actionable steps.

Guidelines:
1. Analyze the request and understand the goal
2. Break down the task into logical, sequential steps
3. Identify the tools and commands needed for each step
4. Assess risk levels (low, medium, high) for each step
5. Determine if approval is required for high-risk operations
6. Consider the environment profile and constraints

Output format (JSON):
{
    "description": "Brief description of the overall task",
    "steps": [
        {
            "id": "step_1",
            "description": "What this step does",
            "command": "actual command to execute (if applicable)",
            "tool": "tool name (ssh, kubectl, docker, etc.)",
            "parameters": {"key": "value"},
            "risk_level": "low|medium|high",
            "requires_approval": true/false,
            "dependencies": ["step_id"]
        }
    ],
    "estimated_duration": 300,
    "risk_level": "overall risk level",
    "requires_approval": true/false
}

Focus on:
- Safety and best practices
- Clear, executable steps
- Proper sequencing and dependencies
- Risk assessment and approval requirements
- Environment-specific considerations"""

    async def process(self, request: AgentRequest) -> AgentResponse:
        """Process a planning request."""
        try:
            # Build the prompt with context
            prompt = self._build_planning_prompt(request)

            # Get LLM response
            llm_request = LLMRequest(
                prompt=prompt,
                system_message=self.system_prompt,
                temperature=0.3,  # Lower temperature for more consistent planning
                max_tokens=2000,
            )

            response = await self.llm_router.complete(llm_request)

            # Parse the response
            try:
                plan_data = json.loads(response.content)
                task_plan = self._parse_plan(plan_data, request)

                return self._create_response(
                    content=f"Created plan with {len(task_plan.steps)} steps",
                    status=TaskStatus.COMPLETED,
                    task_id=task_plan.task_id,
                    next_steps=[
                        f"Execute step: {step.description}" for step in task_plan.steps
                    ],
                    requires_approval=task_plan.requires_approval,
                    risk_level=task_plan.risk_level,
                    metadata={"plan": plan_data},
                )

            except json.JSONDecodeError as e:
                return self._create_response(
                    content="Failed to parse planning response",
                    status=TaskStatus.FAILED,
                    error=f"JSON parsing error: {str(e)}",
                )

        except Exception as e:
            return self._create_response(
                content="Planning failed", status=TaskStatus.FAILED, error=str(e)
            )

    def _build_planning_prompt(self, request: AgentRequest) -> str:
        """Build the planning prompt with context."""
        prompt_parts = [
            f"Task: {request.task}",
            "",
            "Context:",
            json.dumps(request.context, indent=2),
        ]

        if request.environment_profile:
            prompt_parts.extend(
                [
                    "",
                    "Environment Profile:",
                    json.dumps(request.environment_profile, indent=2),
                ]
            )

        if request.metadata:
            prompt_parts.extend(
                ["", "Additional Metadata:", json.dumps(request.metadata, indent=2)]
            )

        prompt_parts.extend(
            ["", "Please create a detailed execution plan for this task."]
        )

        return "\n".join(prompt_parts)

    def _parse_plan(self, plan_data: Dict[str, Any], request: AgentRequest) -> TaskPlan:
        """Parse plan data into TaskPlan object."""
        task_id = str(uuid.uuid4())

        steps = []
        for step_data in plan_data.get("steps", []):
            step = TaskStep(
                id=step_data.get("id", f"step_{len(steps) + 1}"),
                description=step_data.get("description", ""),
                command=step_data.get("command"),
                tool=step_data.get("tool"),
                parameters=step_data.get("parameters", {}),
                risk_level=step_data.get("risk_level", "low"),
                requires_approval=step_data.get("requires_approval", False),
                dependencies=step_data.get("dependencies", []),
            )
            steps.append(step)

        return TaskPlan(
            task_id=task_id,
            description=plan_data.get("description", request.task),
            steps=steps,
            estimated_duration=plan_data.get("estimated_duration"),
            risk_level=plan_data.get("risk_level", "low"),
            requires_approval=plan_data.get("requires_approval", False),
        )

    async def health_check(self) -> bool:
        """Check if planner agent is healthy."""
        try:
            # Test with a simple planning request
            test_request = AgentRequest(task="Test planning", context={"test": True})

            response = await self.process(test_request)
            return response.status == TaskStatus.COMPLETED
        except Exception:
            return False
