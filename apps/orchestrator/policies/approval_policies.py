"""Approval policies for managing task approvals."""

from typing import Any, Dict, List
from datetime import datetime, timedelta
from .base import PolicyEngine, PolicyResult, PolicyViolationType, PolicyEvaluation


class ApprovalPolicyEngine(PolicyEngine):
    """Engine for managing approval policies and workflows."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Approval requirements by risk level
        self.approval_requirements = {
            "high": {
                "required_approvers": 2,
                "required_roles": ["admin", "senior_engineer"],
                "timeout_hours": 24,
                "escalation_hours": 4,
            },
            "medium": {
                "required_approvers": 1,
                "required_roles": ["admin", "engineer", "senior_engineer"],
                "timeout_hours": 48,
                "escalation_hours": 8,
            },
            "low": {
                "required_approvers": 1,
                "required_roles": ["admin", "engineer", "senior_engineer", "developer"],
                "timeout_hours": 72,
                "escalation_hours": 12,
            },
        }

        # Environment-specific approval requirements
        self.environment_approval = {
            "prod": {
                "always_require_approval": True,
                "required_approvers": 2,
                "required_roles": ["admin", "senior_engineer"],
                "business_hours_only": True,
            },
            "staging": {
                "always_require_approval": False,
                "required_approvers": 1,
                "required_roles": ["admin", "engineer", "senior_engineer"],
                "business_hours_only": False,
            },
            "dev": {
                "always_require_approval": False,
                "required_approvers": 1,
                "required_roles": ["admin", "engineer", "senior_engineer", "developer"],
                "business_hours_only": False,
            },
        }

        # Business hours (24-hour format)
        self.business_hours = {"start": 9, "end": 17, "timezone": "UTC"}

        # Emergency override conditions
        self.emergency_override = {
            "enabled": True,
            "required_roles": ["admin", "senior_engineer"],
            "max_frequency_per_day": 3,
            "cooldown_hours": 1,
        }

        # Approval history tracking
        self.approval_history: Dict[str, List[Dict[str, Any]]] = {}

    async def evaluate(self, context: Dict[str, Any]) -> PolicyEvaluation:
        """Evaluate approval requirements for the task."""
        violations = []

        # Extract context information
        task_id = context.get("task_id", "unknown")
        command = context.get("command", "")
        environment = context.get("environment", {})
        user_id = context.get("user_id", "unknown")
        user_role = context.get("user_role", "developer")
        risk_level = context.get("risk_level", "low")
        time_of_day = context.get("time_of_day", 12)

        # Check if approval is required
        requires_approval = self._requires_approval(
            command, environment, risk_level, user_role
        )

        if not requires_approval:
            return self._create_evaluation(
                PolicyResult.ALLOW,
                violations,
                risk_level=risk_level,
                requires_approval=False,
                metadata={
                    "approval_required": False,
                    "reason": "No approval required for this task",
                },
            )

        # Check business hours restrictions
        if self._is_business_hours_restricted(environment, time_of_day):
            violations.append(
                self._create_violation(
                    PolicyViolationType.APPROVAL_REQUIRED,
                    "Task requires approval and can only be executed during business hours",
                    severity="medium",
                )
            )

        # Check user permissions for approval
        if not self._user_can_approve(user_role, risk_level, environment):
            violations.append(
                self._create_violation(
                    PolicyViolationType.PERMISSION_DENIED,
                    f"User role '{user_role}' cannot approve tasks of risk level '{risk_level}'",
                    severity="high",
                )
            )

        # Check emergency override availability
        emergency_available = self._is_emergency_override_available(user_id, user_role)

        # Determine approval requirements
        approval_requirements = self._get_approval_requirements(risk_level, environment)

        return self._create_evaluation(
            PolicyResult.REQUIRE_APPROVAL,
            violations,
            risk_level=risk_level,
            requires_approval=True,
            metadata={
                "approval_required": True,
                "approval_requirements": approval_requirements,
                "emergency_override_available": emergency_available,
                "business_hours_restricted": self._is_business_hours_restricted(
                    environment, time_of_day
                ),
                "task_id": task_id,
                "user_id": user_id,
                "user_role": user_role,
            },
        )

    def _requires_approval(
        self, command: str, environment: Dict[str, Any], risk_level: str, user_role: str
    ) -> bool:
        """Determine if approval is required for the task."""
        env_id = environment.get("id", "").lower()

        # Check environment-specific requirements
        if env_id in self.environment_approval:
            env_config = self.environment_approval[env_id]
            if env_config.get("always_require_approval", False):
                return True

        # Check risk level requirements
        if risk_level in ["high", "medium"]:
            return True

        # Check command-specific requirements
        if self._is_high_risk_command(command):
            return True

        # Check user role requirements
        if user_role in ["viewer", "readonly"]:
            return True

        return False

    def _is_business_hours_restricted(
        self, environment: Dict[str, Any], hour: int
    ) -> bool:
        """Check if task is restricted to business hours."""
        env_id = environment.get("id", "").lower()

        if env_id in self.environment_approval:
            env_config = self.environment_approval[env_id]
            if env_config.get("business_hours_only", False):
                return not (
                    self.business_hours["start"] <= hour <= self.business_hours["end"]
                )

        return False

    def _user_can_approve(
        self, user_role: str, risk_level: str, environment: Dict[str, Any]
    ) -> bool:
        """Check if user can approve tasks of the given risk level."""
        env_id = environment.get("id", "").lower()

        # Get required roles for the risk level
        if risk_level in self.approval_requirements:
            required_roles = self.approval_requirements[risk_level]["required_roles"]
        else:
            required_roles = ["admin"]

        # Check environment-specific requirements
        if env_id in self.environment_approval:
            env_config = self.environment_approval[env_id]
            if "required_roles" in env_config:
                required_roles = env_config["required_roles"]

        return user_role in required_roles

    def _is_emergency_override_available(self, user_id: str, user_role: str) -> bool:
        """Check if emergency override is available for the user."""
        if not self.emergency_override["enabled"]:
            return False

        if user_role not in self.emergency_override["required_roles"]:
            return False

        # Check frequency limits
        today = datetime.now().date()
        user_history = self.approval_history.get(user_id, [])
        today_overrides = [
            h
            for h in user_history
            if h.get("date") == today and h.get("type") == "emergency_override"
        ]

        if len(today_overrides) >= self.emergency_override["max_frequency_per_day"]:
            return False

        # Check cooldown
        if user_history:
            last_override = max(
                (h for h in user_history if h.get("type") == "emergency_override"),
                key=lambda x: x.get("timestamp", datetime.min),
                default=None,
            )

            if last_override:
                last_time = last_override.get("timestamp", datetime.min)
                cooldown_end = last_time + timedelta(
                    hours=self.emergency_override["cooldown_hours"]
                )
                if datetime.now() < cooldown_end:
                    return False

        return True

    def _get_approval_requirements(
        self, risk_level: str, environment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get approval requirements for the risk level and environment."""
        env_id = environment.get("id", "").lower()

        # Start with risk-level requirements
        requirements = self.approval_requirements.get(
            risk_level, self.approval_requirements["low"]
        ).copy()

        # Override with environment-specific requirements
        if env_id in self.environment_approval:
            env_config = self.environment_approval[env_id]
            for key, value in env_config.items():
                if key in requirements:
                    requirements[key] = value

        return requirements

    def _is_high_risk_command(self, command: str) -> bool:
        """Check if command is considered high-risk."""
        if not command:
            return False

        command_lower = command.lower()
        high_risk_patterns = [
            "delete",
            "remove",
            "destroy",
            "drop",
            "kill",
            "stop",
            "restart",
            "reboot",
            "shutdown",
            "halt",
            "poweroff",
            "rm -rf",
            "dd if=",
            "mkfs",
            "fdisk",
            "parted",
            "terraform destroy",
            "kubectl delete",
            "docker rm -f",
        ]

        return any(pattern in command_lower for pattern in high_risk_patterns)

    async def record_approval(
        self, task_id: str, user_id: str, approved: bool, reason: str = ""
    ) -> None:
        """Record an approval decision."""
        if user_id not in self.approval_history:
            self.approval_history[user_id] = []

        self.approval_history[user_id].append(
            {
                "task_id": task_id,
                "approved": approved,
                "reason": reason,
                "timestamp": datetime.now(),
                "date": datetime.now().date(),
                "type": "approval",
            }
        )

    async def record_emergency_override(
        self, task_id: str, user_id: str, reason: str = ""
    ) -> None:
        """Record an emergency override."""
        if user_id not in self.approval_history:
            self.approval_history[user_id] = []

        self.approval_history[user_id].append(
            {
                "task_id": task_id,
                "reason": reason,
                "timestamp": datetime.now(),
                "date": datetime.now().date(),
                "type": "emergency_override",
            }
        )

    async def health_check(self) -> bool:
        """Check if approval policy engine is healthy."""
        try:
            # Test with a low-risk scenario
            test_context = {
                "task_id": "test-task",
                "command": "kubectl get pods",
                "environment": {"id": "dev", "type": "development"},
                "user_id": "test",
                "user_role": "developer",
                "risk_level": "low",
                "time_of_day": 12,
            }

            result = await self.evaluate(test_context)
            return result.result in [PolicyResult.ALLOW, PolicyResult.REQUIRE_APPROVAL]
        except Exception:
            return False



