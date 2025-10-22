"""Risk assessment engine for evaluating task risks."""

from typing import Any, Dict
from .base import PolicyEngine, PolicyResult, PolicyViolationType, PolicyEvaluation


class RiskAssessmentEngine(PolicyEngine):
    """Engine for assessing risks of tasks and operations."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Risk factors and their weights
        self.risk_factors = {
            "command_danger": 0.3,
            "environment_sensitivity": 0.25,
            "user_permissions": 0.2,
            "time_of_day": 0.1,
            "resource_impact": 0.15,
        }

        # Environment sensitivity levels
        self.environment_sensitivity = {
            "prod": 0.9,
            "production": 0.9,
            "staging": 0.6,
            "stage": 0.6,
            "dev": 0.3,
            "development": 0.3,
            "test": 0.2,
            "testing": 0.2,
        }

        # User permission levels
        self.user_permissions = {
            "admin": 0.1,
            "root": 0.1,
            "operator": 0.3,
            "developer": 0.5,
            "viewer": 0.8,
            "readonly": 0.9,
        }

        # High-risk time periods (24-hour format)
        self.high_risk_hours = config.get(
            "high_risk_hours", [22, 23, 0, 1, 2, 3, 4, 5, 6]
        )

        # Resource impact levels
        self.resource_impact = {
            "critical": 0.9,
            "high": 0.7,
            "medium": 0.5,
            "low": 0.3,
            "minimal": 0.1,
        }

    async def evaluate(self, context: Dict[str, Any]) -> PolicyEvaluation:
        """Evaluate risk level of the task."""
        violations = []

        # Extract context information
        command = context.get("command", "")
        environment = context.get("environment", {})
        user_id = context.get("user_id", "unknown")
        user_role = context.get("user_role", "developer")
        time_of_day = context.get("time_of_day", 12)  # Default to noon

        # Calculate individual risk scores
        command_risk = self._assess_command_risk(command)
        environment_risk = self._assess_environment_risk(environment)
        user_risk = self._assess_user_risk(user_role)
        time_risk = self._assess_time_risk(time_of_day)
        resource_risk = self._assess_resource_risk(command, environment)

        # Calculate weighted risk score
        total_risk = (
            command_risk * self.risk_factors["command_danger"]
            + environment_risk * self.risk_factors["environment_sensitivity"]
            + user_risk * self.risk_factors["user_permissions"]
            + time_risk * self.risk_factors["time_of_day"]
            + resource_risk * self.risk_factors["resource_impact"]
        )

        # Determine risk level
        if total_risk >= 0.8:
            risk_level = "high"
            result = PolicyResult.REQUIRE_APPROVAL
        elif total_risk >= 0.5:
            risk_level = "medium"
            result = PolicyResult.REQUIRE_APPROVAL
        elif total_risk >= 0.3:
            risk_level = "low"
            result = PolicyResult.WARN
        else:
            risk_level = "low"
            result = PolicyResult.ALLOW

        # Add violations based on risk factors
        if command_risk >= 0.7:
            violations.append(
                self._create_violation(
                    PolicyViolationType.RISK_TOO_HIGH,
                    f"High-risk command detected: {command}",
                    severity="high",
                )
            )

        if environment_risk >= 0.8:
            violations.append(
                self._create_violation(
                    PolicyViolationType.RISK_TOO_HIGH,
                    f"High-risk environment: {environment.get('id', 'unknown')}",
                    severity="high",
                )
            )

        if user_risk >= 0.7:
            violations.append(
                self._create_violation(
                    PolicyViolationType.PERMISSION_DENIED,
                    f"Insufficient permissions for user role: {user_role}",
                    severity="medium",
                )
            )

        if time_risk >= 0.8:
            violations.append(
                self._create_violation(
                    PolicyViolationType.RISK_TOO_HIGH,
                    f"High-risk time period: {time_of_day}:00",
                    severity="medium",
                )
            )

        return self._create_evaluation(
            result,
            violations,
            risk_level=risk_level,
            requires_approval=total_risk >= 0.5,
            metadata={
                "total_risk_score": total_risk,
                "risk_breakdown": {
                    "command_risk": command_risk,
                    "environment_risk": environment_risk,
                    "user_risk": user_risk,
                    "time_risk": time_risk,
                    "resource_risk": resource_risk,
                },
                "command": command,
                "environment": environment.get("id", "unknown"),
                "user_id": user_id,
                "user_role": user_role,
            },
        )

    def _assess_command_risk(self, command: str) -> float:
        """Assess risk level of the command."""
        if not command:
            return 0.0

        command_lower = command.lower()

        # High-risk commands
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

        # Medium-risk commands
        medium_risk_patterns = [
            "apply",
            "create",
            "update",
            "patch",
            "replace",
            "kubectl apply",
            "kubectl create",
            "kubectl patch",
            "docker run",
            "docker start",
            "docker stop",
            "terraform apply",
            "terraform plan",
        ]

        # Check for high-risk patterns
        for pattern in high_risk_patterns:
            if pattern in command_lower:
                return 0.8

        # Check for medium-risk patterns
        for pattern in medium_risk_patterns:
            if pattern in command_lower:
                return 0.5

        # Read-only commands are low risk
        readonly_patterns = [
            "get",
            "describe",
            "logs",
            "inspect",
            "show",
            "list",
            "kubectl get",
            "kubectl describe",
            "kubectl logs",
            "docker ps",
            "docker images",
            "docker logs",
            "terraform show",
            "terraform output",
        ]

        for pattern in readonly_patterns:
            if pattern in command_lower:
                return 0.1

        # Default risk for unknown commands
        return 0.3

    def _assess_environment_risk(self, environment: Dict[str, Any]) -> float:
        """Assess risk level of the environment."""
        env_id = environment.get("id", "").lower()
        env_type = environment.get("type", "").lower()

        # Check environment ID
        for env_name, risk in self.environment_sensitivity.items():
            if env_name in env_id:
                return risk

        # Check environment type
        if env_type == "prod" or env_type == "production":
            return 0.9
        elif env_type == "staging" or env_type == "stage":
            return 0.6
        elif env_type == "dev" or env_type == "development":
            return 0.3
        elif env_type == "test" or env_type == "testing":
            return 0.2

        # Default risk for unknown environments
        return 0.5

    def _assess_user_risk(self, user_role: str) -> float:
        """Assess risk level based on user role."""
        role_lower = user_role.lower()
        return self.user_permissions.get(role_lower, 0.5)

    def _assess_time_risk(self, hour: int) -> float:
        """Assess risk level based on time of day."""
        if hour in self.high_risk_hours:
            return 0.8
        else:
            return 0.1

    def _assess_resource_impact(
        self, command: str, environment: Dict[str, Any]
    ) -> float:
        """Assess potential resource impact of the command."""
        if not command:
            return 0.0

        command_lower = command.lower()

        # Critical resource impact
        if any(
            pattern in command_lower
            for pattern in [
                "kubectl delete",
                "terraform destroy",
                "docker system prune",
                "rm -rf",
                "dd if=",
                "mkfs",
                "fdisk",
            ]
        ):
            return 0.9

        # High resource impact
        if any(
            pattern in command_lower
            for pattern in [
                "kubectl apply",
                "kubectl create",
                "kubectl patch",
                "docker run",
                "terraform apply",
                "terraform plan",
            ]
        ):
            return 0.7

        # Medium resource impact
        if any(
            pattern in command_lower
            for pattern in [
                "kubectl scale",
                "kubectl rollout",
                "docker start",
                "docker stop",
            ]
        ):
            return 0.5

        # Low resource impact
        if any(
            pattern in command_lower
            for pattern in [
                "kubectl get",
                "kubectl describe",
                "kubectl logs",
                "docker ps",
                "docker images",
                "docker logs",
            ]
        ):
            return 0.1

        # Default resource impact
        return 0.3

    async def health_check(self) -> bool:
        """Check if risk assessment engine is healthy."""
        try:
            # Test with a low-risk scenario
            test_context = {
                "command": "kubectl get pods",
                "environment": {"id": "dev", "type": "development"},
                "user_id": "test",
                "user_role": "developer",
                "time_of_day": 12,
            }

            result = await self.evaluate(test_context)
            return result.result == PolicyResult.ALLOW
        except Exception:
            return False





