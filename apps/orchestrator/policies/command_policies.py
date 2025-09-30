"""Command-level security policies."""

import re
from typing import Any, Dict, List
from .base import (
    PolicyEngine,
    PolicyResult,
    PolicyViolation,
    PolicyViolationType,
    PolicyEvaluation,
)


class CommandPolicyEngine(PolicyEngine):
    """Policy engine for command-level security."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Dangerous commands that should be blocked
        self.blocked_commands = set(
            config.get(
                "blocked_commands",
                [
                    "rm -rf /",
                    "rm -rf /*",
                    "dd if=/dev/zero",
                    "mkfs",
                    "fdisk",
                    "parted",
                    "shutdown",
                    "reboot",
                    "halt",
                    "poweroff",
                    "init 0",
                    "init 6",
                ],
            )
        )

        # Commands that require approval
        self.approval_required_commands = set(
            config.get(
                "approval_required_commands",
                [
                    "kubectl delete",
                    "kubectl apply -f",
                    "kubectl create",
                    "kubectl patch",
                    "kubectl replace",
                    "docker rm -f",
                    "docker rmi",
                    "docker system prune",
                    "terraform destroy",
                    "terraform apply",
                ],
            )
        )

        # Commands that are read-only (always allowed)
        self.readonly_commands = set(
            config.get(
                "readonly_commands",
                [
                    "kubectl get",
                    "kubectl describe",
                    "kubectl logs",
                    "kubectl top",
                    "docker ps",
                    "docker images",
                    "docker logs",
                    "docker inspect",
                    "terraform plan",
                    "terraform show",
                    "terraform output",
                ],
            )
        )

        # Dangerous patterns
        self.dangerous_patterns = [
            r"rm\s+-rf\s+/",
            r"dd\s+if=/dev/zero",
            r"mkfs\.",
            r"fdisk\s+/dev/",
            r"shutdown|reboot|halt|poweroff",
            r"init\s+[06]",
            r"kill\s+-9\s+-1",
            r"killall\s+-9",
        ]

        # Environment-specific restrictions
        self.environment_restrictions = config.get("environment_restrictions", {})

    async def evaluate(self, context: Dict[str, Any]) -> PolicyEvaluation:
        """Evaluate command against security policies."""
        violations = []
        command = context.get("command", "")
        environment = context.get("environment", {})
        user_id = context.get("user_id", "unknown")

        if not command:
            return self._create_evaluation(
                PolicyResult.DENY,
                [
                    self._create_violation(
                        PolicyViolationType.COMMAND_BLOCKED, "Empty command not allowed"
                    )
                ],
            )

        # Check for blocked commands
        if self._is_blocked_command(command):
            violations.append(
                self._create_violation(
                    PolicyViolationType.COMMAND_BLOCKED,
                    f"Dangerous command blocked: {command}",
                    severity="high",
                )
            )
            return self._create_evaluation(
                PolicyResult.DENY, violations, risk_level="high"
            )

        # Check for dangerous patterns
        if self._matches_dangerous_pattern(command):
            violations.append(
                self._create_violation(
                    PolicyViolationType.COMMAND_BLOCKED,
                    f"Command matches dangerous pattern: {command}",
                    severity="high",
                )
            )
            return self._create_evaluation(
                PolicyResult.DENY, violations, risk_level="high"
            )

        # Check for approval-required commands
        requires_approval = self._requires_approval(command)
        if requires_approval:
            violations.append(
                self._create_violation(
                    PolicyViolationType.APPROVAL_REQUIRED,
                    f"Command requires approval: {command}",
                    severity="medium",
                )
            )

        # Check environment-specific restrictions
        env_violations = self._check_environment_restrictions(command, environment)
        violations.extend(env_violations)

        # Determine risk level
        risk_level = self._assess_risk_level(command, violations)

        # Determine result
        if any(v.severity == "high" for v in violations):
            result = PolicyResult.DENY
        elif requires_approval or any(v.severity == "medium" for v in violations):
            result = PolicyResult.REQUIRE_APPROVAL
        elif any(v.severity == "low" for v in violations):
            result = PolicyResult.WARN
        else:
            result = PolicyResult.ALLOW

        return self._create_evaluation(
            result,
            violations,
            risk_level=risk_level,
            requires_approval=requires_approval,
            metadata={
                "command": command,
                "user_id": user_id,
                "environment": environment.get("id", "unknown"),
            },
        )

    def _is_blocked_command(self, command: str) -> bool:
        """Check if command is in the blocked list."""
        command_lower = command.lower().strip()
        return any(blocked in command_lower for blocked in self.blocked_commands)

    def _matches_dangerous_pattern(self, command: str) -> bool:
        """Check if command matches dangerous patterns."""
        for pattern in self.dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        return False

    def _requires_approval(self, command: str) -> bool:
        """Check if command requires approval."""
        command_lower = command.lower().strip()
        return any(
            required in command_lower for required in self.approval_required_commands
        )

    def _check_environment_restrictions(
        self, command: str, environment: Dict[str, Any]
    ) -> List[PolicyViolation]:
        """Check environment-specific restrictions."""
        violations = []
        env_id = environment.get("id", "unknown")

        if env_id in self.environment_restrictions:
            restrictions = self.environment_restrictions[env_id]

            # Check if command is allowed in this environment
            allowed_commands = restrictions.get("allowed_commands", [])
            if allowed_commands and not any(
                allowed in command.lower() for allowed in allowed_commands
            ):
                violations.append(
                    self._create_violation(
                        PolicyViolationType.ENVIRONMENT_MISMATCH,
                        f"Command not allowed in environment {env_id}: {command}",
                        severity="medium",
                    )
                )

            # Check if command is blocked in this environment
            blocked_commands = restrictions.get("blocked_commands", [])
            if any(blocked in command.lower() for blocked in blocked_commands):
                violations.append(
                    self._create_violation(
                        PolicyViolationType.COMMAND_BLOCKED,
                        f"Command blocked in environment {env_id}: {command}",
                        severity="high",
                    )
                )

        return violations

    def _assess_risk_level(
        self, command: str, violations: List[PolicyViolation]
    ) -> str:
        """Assess the overall risk level of the command."""
        if any(v.severity == "high" for v in violations):
            return "high"
        elif any(v.severity == "medium" for v in violations):
            return "medium"
        else:
            return "low"

    async def health_check(self) -> bool:
        """Check if policy engine is healthy."""
        try:
            # Test with a safe command
            test_context = {
                "command": "kubectl get pods",
                "environment": {"id": "test"},
                "user_id": "test",
            }

            result = await self.evaluate(test_context)
            return result.result == PolicyResult.ALLOW
        except Exception:
            return False



