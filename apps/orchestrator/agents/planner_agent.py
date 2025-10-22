"""Planner Agent for breaking down tasks into steps."""

import json
import uuid
from typing import Any, Dict, List

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
        return """You are a DevOps planning agent. Your role is to break down user requests into concrete, executable steps for the DevOps execution agent.

Guidelines:
1. Analyze the request and understand the goal
2. Break down the task into logical, sequential steps (at least planning + execution; include verification when useful)
3. Identify the tools and exact commands needed for each step
4. Assess risk levels (low, medium, high) for each step
5. Determine if approval is required for high-risk operations
6. Consider the environment profile and constraints
7. Prefer automation over manual description – every execution step should have an explicit command
8. When the task requires work on a remote server and SSH details exist, include a step with tool \"ssh\" and the precise command (e.g., `uptime`, `top -b -n1`, etc.)
9. Capture clarifying questions as dedicated steps only when critical information is missing; otherwise produce actionable steps.

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
- Environment-specific considerations
- Concrete commands that can be executed without further interpretation"""

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

            try:
                plan_data = json.loads(response.content)
            except json.JSONDecodeError:
                plan_data = self._build_default_plan(request)

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

        env_profile = request.environment_profile if isinstance(request.environment_profile, dict) else {}
        ssh_config = env_profile.get("ssh") if isinstance(env_profile, dict) else None

        raw_steps = plan_data.get("steps") or []
        normalized_steps: List[TaskStep] = []

        for idx, step_data in enumerate(raw_steps, start=1):
            if not isinstance(step_data, dict):
                continue

            step_id = step_data.get("id") or f"step_{idx}"
            description = step_data.get("description") or request.task
            command = step_data.get("command")
            tool = step_data.get("tool")

            if tool == "ssh" and not command:
                command = "uptime"
                step_data["command"] = command

            normalized_steps.append(
                TaskStep(
                    id=step_id,
                    description=description,
                    command=command,
                    tool=tool,
                    parameters=step_data.get("parameters", {}),
                    risk_level=step_data.get("risk_level", "low"),
                    requires_approval=step_data.get("requires_approval", False),
                    dependencies=step_data.get("dependencies", []),
                )
            )

        steps = normalized_steps

        if ssh_config:
            needs_ssh_steps = not steps or not any((step.tool or "").lower() == "ssh" for step in steps if isinstance(step, TaskStep))
            if needs_ssh_steps:
                metric_step_dicts = self._build_metric_steps(request.task)

                if isinstance(plan_data, dict):
                    existing_steps = plan_data.get("steps")
                    if isinstance(existing_steps, list):
                        existing_steps.extend(metric_step_dicts)
                    else:
                        plan_data["steps"] = metric_step_dicts

                metric_task_steps = [
                    TaskStep(
                        id=step_dict["id"],
                        description=step_dict["description"],
                        command=step_dict["command"],
                        tool=step_dict["tool"],
                        parameters=step_dict.get("parameters", {}),
                        risk_level=step_dict.get("risk_level", "low"),
                        requires_approval=step_dict.get("requires_approval", False),
                        dependencies=step_dict.get("dependencies", []),
                    )
                    for step_dict in metric_step_dicts
                ]

                if steps:
                    steps.extend(metric_task_steps)
                else:
                    steps = metric_task_steps

        if not steps:
            clarification_step = TaskStep(
                id="step_clarify_environment",
                description="Request SSH connection details (host, username, key) to proceed",
                command=None,
                tool="clarify",
                parameters={"missing": "ssh_configuration"},
                risk_level="low",
                requires_approval=False,
                dependencies=[],
            )
            plan_data["steps"] = [
                {
                    "id": clarification_step.id,
                    "description": clarification_step.description,
                    "tool": clarification_step.tool,
                    "parameters": clarification_step.parameters,
                    "risk_level": clarification_step.risk_level,
                    "requires_approval": clarification_step.requires_approval,
                    "dependencies": [],
                }
            ]
            steps = [clarification_step]

        return TaskPlan(
            task_id=task_id,
            description=plan_data.get("description", request.task),
            steps=steps,
            estimated_duration=plan_data.get("estimated_duration"),
            risk_level=plan_data.get("risk_level", "low"),
            requires_approval=plan_data.get("requires_approval", False),
        )

    def _build_metric_steps(self, task_text: str) -> List[Dict[str, Any]]:
        """Build default SSH metric collection steps for a task."""
        text = (task_text or '').lower()
        steps: List[Dict[str, Any]] = []

        cpu_keywords = ("cpu", "load", "uptime")
        memory_keywords = ("memory", "ram", "usage", "mem")

        if any(keyword in text for keyword in cpu_keywords):
            steps.append({
                "id": "step_collect_cpu",
                "description": "Collect CPU utilisation via uptime",
                "command": "uptime",
                "tool": "ssh",
                "parameters": {"metric": "cpu"},
                "risk_level": "low",
                "requires_approval": False,
            })

        if any(keyword in text for keyword in memory_keywords):
            steps.append({
                "id": "step_collect_memory",
                "description": "Collect memory usage statistics",
                "command": "free -m",
                "tool": "ssh",
                "parameters": {"metric": "memory"},
                "risk_level": "low",
                "requires_approval": False,
            })

        if not steps:
            steps.append({
                "id": "step_collect_system_metrics",
                "description": "Collect CPU and memory statistics",
                "command": "uptime && free -m",
                "tool": "ssh",
                "parameters": {"metric": "system"},
                "risk_level": "low",
                "requires_approval": False,
            })

        return steps

    def _build_default_plan(self, request: AgentRequest) -> Dict[str, Any]:
        """Fallback deterministic plan when LLM response is not usable."""
        env_profile = request.environment_profile or {}
        ssh_config = env_profile.get("ssh") if isinstance(env_profile, dict) else None
        task_lower = request.task.lower()

        plan: Dict[str, Any] = {
            "description": request.task,
            "estimated_duration": 120,
            "risk_level": "low",
            "requires_approval": False,
            "steps": [],
        }

        if ssh_config:
            plan["steps"] = self._build_metric_steps(request.task)
        else:
            plan["steps"] = [
                {
                    "id": "step_clarify_environment",
                    "description": "Request SSH connection details (host, username, key) to proceed",
                    "tool": "clarify",
                    "parameters": {"missing": "ssh_configuration"},
                    "risk_level": "low",
                    "requires_approval": False,
                }
            ]
        return plan

    async def health_check(self) -> bool:
        """Check if planner agent is healthy."""
        try:
            # Test with a simple planning request
            test_request = AgentRequest(task="Test planning", context={"test": True})

            response = await self.process(test_request)
            return response.status == TaskStatus.COMPLETED
        except Exception:
            return False
