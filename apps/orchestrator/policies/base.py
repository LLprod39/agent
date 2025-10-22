"""Base classes for security policies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum


class PolicyViolationType(Enum):
    """Types of policy violations."""

    COMMAND_BLOCKED = "command_blocked"
    RISK_TOO_HIGH = "risk_too_high"
    APPROVAL_REQUIRED = "approval_required"
    ENVIRONMENT_MISMATCH = "environment_mismatch"
    PERMISSION_DENIED = "permission_denied"


class PolicyResult(Enum):
    """Policy evaluation results."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    WARN = "warn"


@dataclass
class PolicyViolation:
    """Represents a policy violation."""

    violation_type: PolicyViolationType
    message: str
    severity: str = "medium"
    details: Optional[Dict[str, Any]] = None


@dataclass
class PolicyEvaluation:
    """Result of policy evaluation."""

    result: PolicyResult
    violations: List[PolicyViolation]
    risk_level: str = "low"
    requires_approval: bool = False
    metadata: Optional[Dict[str, Any]] = None


class PolicyEngine(ABC):
    """Abstract base class for policy engines."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", "unknown")

    @abstractmethod
    async def evaluate(self, context: Dict[str, Any]) -> PolicyEvaluation:
        """Evaluate policy against the given context."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if policy engine is healthy."""
        pass

    def _create_violation(
        self,
        violation_type: PolicyViolationType,
        message: str,
        severity: str = "medium",
        details: Optional[Dict[str, Any]] = None,
    ) -> PolicyViolation:
        """Create a policy violation."""
        return PolicyViolation(
            violation_type=violation_type,
            message=message,
            severity=severity,
            details=details,
        )

    def _create_evaluation(
        self,
        result: PolicyResult,
        violations: List[PolicyViolation],
        risk_level: str = "low",
        requires_approval: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PolicyEvaluation:
        """Create a policy evaluation result."""
        return PolicyEvaluation(
            result=result,
            violations=violations,
            risk_level=risk_level,
            requires_approval=requires_approval,
            metadata=metadata,
        )





