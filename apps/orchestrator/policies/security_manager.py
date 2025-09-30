"""Security manager for coordinating all security policies."""

import logging
from typing import Any, Dict, List
from datetime import datetime

from .base import PolicyResult, PolicyEvaluation
from .command_policies import CommandPolicyEngine
from .risk_assessment import RiskAssessmentEngine
from .approval_policies import ApprovalPolicyEngine

logger = logging.getLogger(__name__)


class SecurityManager:
    """Manages all security policies and provides unified security evaluation."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Initialize policy engines
        self.command_policy = CommandPolicyEngine(config.get("command_policies", {}))
        self.risk_assessment = RiskAssessmentEngine(config.get("risk_assessment", {}))
        self.approval_policy = ApprovalPolicyEngine(config.get("approval_policies", {}))

        # Security settings
        self.enabled = config.get("enabled", True)
        self.strict_mode = config.get("strict_mode", False)
        self.audit_logging = config.get("audit_logging", True)

        # Audit log
        self.audit_log: List[Dict[str, Any]] = []

    async def evaluate_security(self, context: Dict[str, Any]) -> PolicyEvaluation:
        """Evaluate security policies for the given context."""
        if not self.enabled:
            return PolicyEvaluation(
                result=PolicyResult.ALLOW,
                violations=[],
                risk_level="low",
                requires_approval=False,
                metadata={"security_disabled": True},
            )

        try:
            # Add timestamp to context
            context["timestamp"] = datetime.now().isoformat()

            # Evaluate command policies
            command_evaluation = await self.command_policy.evaluate(context)

            # If command is blocked, return immediately
            if command_evaluation.result == PolicyResult.DENY:
                await self._log_audit_event(
                    "command_blocked", context, command_evaluation
                )
                return command_evaluation

            # Evaluate risk assessment
            risk_evaluation = await self.risk_assessment.evaluate(context)

            # Update context with risk information
            context["risk_level"] = risk_evaluation.risk_level

            # Evaluate approval policies
            approval_evaluation = await self.approval_policy.evaluate(context)

            # Combine evaluations
            combined_evaluation = self._combine_evaluations(
                command_evaluation, risk_evaluation, approval_evaluation
            )

            # Log audit event
            await self._log_audit_event(
                "security_evaluation", context, combined_evaluation
            )

            return combined_evaluation

        except Exception as e:
            logger.error(f"Security evaluation failed: {str(e)}")

            # In strict mode, deny on error
            if self.strict_mode:
                return PolicyEvaluation(
                    result=PolicyResult.DENY,
                    violations=[],
                    risk_level="high",
                    requires_approval=True,
                    metadata={"error": str(e), "strict_mode": True},
                )
            else:
                # In non-strict mode, allow with warning
                return PolicyEvaluation(
                    result=PolicyResult.WARN,
                    violations=[],
                    risk_level="medium",
                    requires_approval=False,
                    metadata={"error": str(e), "strict_mode": False},
                )

    def _combine_evaluations(
        self,
        command_eval: PolicyEvaluation,
        risk_eval: PolicyEvaluation,
        approval_eval: PolicyEvaluation,
    ) -> PolicyEvaluation:
        """Combine multiple policy evaluations into a single result."""

        # Collect all violations
        all_violations = []
        all_violations.extend(command_eval.violations)
        all_violations.extend(risk_eval.violations)
        all_violations.extend(approval_eval.violations)

        # Determine overall result
        if command_eval.result == PolicyResult.DENY:
            result = PolicyResult.DENY
        elif any(
            eval.result == PolicyResult.DENY for eval in [risk_eval, approval_eval]
        ):
            result = PolicyResult.DENY
        elif any(
            eval.result == PolicyResult.REQUIRE_APPROVAL
            for eval in [command_eval, risk_eval, approval_eval]
        ):
            result = PolicyResult.REQUIRE_APPROVAL
        elif any(
            eval.result == PolicyResult.WARN
            for eval in [command_eval, risk_eval, approval_eval]
        ):
            result = PolicyResult.WARN
        else:
            result = PolicyResult.ALLOW

        # Determine overall risk level
        risk_levels = [
            command_eval.risk_level,
            risk_eval.risk_level,
            approval_eval.risk_level,
        ]
        if "high" in risk_levels:
            overall_risk = "high"
        elif "medium" in risk_levels:
            overall_risk = "medium"
        else:
            overall_risk = "low"

        # Determine if approval is required
        requires_approval = any(
            eval.requires_approval for eval in [command_eval, risk_eval, approval_eval]
        )

        # Combine metadata
        combined_metadata = {
            "command_evaluation": command_eval.metadata,
            "risk_evaluation": risk_eval.metadata,
            "approval_evaluation": approval_eval.metadata,
            "combined_at": datetime.now().isoformat(),
        }

        return PolicyEvaluation(
            result=result,
            violations=all_violations,
            risk_level=overall_risk,
            requires_approval=requires_approval,
            metadata=combined_metadata,
        )

    async def _log_audit_event(
        self, event_type: str, context: Dict[str, Any], evaluation: PolicyEvaluation
    ) -> None:
        """Log security audit event."""
        if not self.audit_logging:
            return

        audit_event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "context": {
                "command": context.get("command", ""),
                "environment": context.get("environment", {}),
                "user_id": context.get("user_id", "unknown"),
                "user_role": context.get("user_role", "unknown"),
                "task_id": context.get("task_id", "unknown"),
            },
            "evaluation": {
                "result": evaluation.result.value,
                "risk_level": evaluation.risk_level,
                "requires_approval": evaluation.requires_approval,
                "violations": [
                    {
                        "type": v.violation_type.value,
                        "message": v.message,
                        "severity": v.severity,
                    }
                    for v in evaluation.violations
                ],
            },
        }

        self.audit_log.append(audit_event)

        # Keep only last 1000 events
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]

        logger.info(
            f"Security audit: {event_type} - {evaluation.result.value} - {evaluation.risk_level}"
        )

    async def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries."""
        return self.audit_log[-limit:]

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all security components."""
        return {
            "security_manager": True,
            "command_policy": await self.command_policy.health_check(),
            "risk_assessment": await self.risk_assessment.health_check(),
            "approval_policy": await self.approval_policy.health_check(),
        }

    async def record_approval(
        self, task_id: str, user_id: str, approved: bool, reason: str = ""
    ) -> None:
        """Record an approval decision."""
        await self.approval_policy.record_approval(task_id, user_id, approved, reason)

    async def record_emergency_override(
        self, task_id: str, user_id: str, reason: str = ""
    ) -> None:
        """Record an emergency override."""
        await self.approval_policy.record_emergency_override(task_id, user_id, reason)




