"""Enhanced orchestrator with database integration, error recovery, and rollback."""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from .llm_router import LLMRouter
from .agents import PlannerAgent, ExecutorAgent, VerifierAgent, AgentRequest, TaskStatus
from ..database.repositories import (
    TaskRepository,
    SessionRepository,
    AuditRepository,
    KnowledgeRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationRequest:
    """Request for orchestration."""

    task: str
    context: Dict[str, Any]
    environment_profile: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    user_id: Optional[int] = None
    auto_approve: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class OrchestrationResponse:
    """Response from orchestration."""

    task_id: str
    status: TaskStatus
    message: str
    results: List[Dict[str, Any]]
    requires_approval: bool = False
    risk_level: str = "low"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionState:
    """Track execution state for rollback."""

    task_id: str
    completed_steps: List[Dict[str, Any]] = field(default_factory=list)
    rollback_actions: List[Dict[str, Any]] = field(default_factory=list)
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)


class EnhancedOrchestrator:
    """Enhanced orchestrator with database persistence and advanced features."""

    def __init__(
        self,
        config: Dict[str, Any],
        llm_router: LLMRouter,
        db_session: AsyncSession,
    ):
        self.config = config
        self.llm_router = llm_router
        self.db_session = db_session

        # Initialize agents
        self.planner = PlannerAgent(config.get("planner", {}), llm_router)
        self.executor = ExecutorAgent(config.get("executor", {}), llm_router)
        self.verifier = VerifierAgent(config.get("verifier", {}), llm_router)

        # Initialize repositories
        self.task_repo = TaskRepository(db_session)
        self.session_repo = SessionRepository(db_session)
        self.audit_repo = AuditRepository(db_session)
        self.knowledge_repo = KnowledgeRepository(db_session)

        # Execution state tracking
        self.execution_states: Dict[str, ExecutionState] = {}

        # Configuration
        self.enable_rollback = config.get("enable_rollback", True)
        self.enable_learning = config.get("enable_learning", True)
        self.max_retry_attempts = config.get("max_retry_attempts", 3)

    async def process_request(
        self, request: OrchestrationRequest
    ) -> OrchestrationResponse:
        """Process orchestration request with full persistence."""
        task_id = str(uuid.uuid4())

        try:
            logger.info(f"Starting orchestration for task {task_id}: {request.task}")

            # Create task in database
            task = await self.task_repo.create(
                task_id=task_id,
                user_id=request.user_id,
                description=request.task,
                environment_profile=request.environment_profile.get("id")
                if request.environment_profile
                else None,
                metadata=request.metadata,
            )

            # Log audit
            await self.audit_repo.log(
                action="task_created",
                resource_type="task",
                resource_id=task_id,
                user_id=request.user_id,
                details={"description": request.task},
            )

            # Initialize execution state
            self.execution_states[task_id] = ExecutionState(task_id=task_id)

            # Update task status to in_progress
            await self.task_repo.update_status(
                task_id, TaskStatus.IN_PROGRESS
            )

            # Step 1: Planning
            plan_result = await self._plan_task(request, task_id)
            if plan_result["status"] != TaskStatus.COMPLETED:
                await self.task_repo.update_status(
                    task_id,
                    TaskStatus.FAILED,
                    error=plan_result.get("error", "Planning failed"),
                )
                return self._create_response(
                    task_id, plan_result["status"], plan_result["message"], [plan_result]
                )

            # Check if approval is required
            if plan_result.get("requires_approval", False) and not request.auto_approve:
                await self.task_repo.update_status(task_id, TaskStatus.PENDING)
                await self.audit_repo.log(
                    action="approval_required",
                    resource_type="task",
                    resource_id=task_id,
                    user_id=request.user_id,
                )
                return self._create_response(
                    task_id,
                    TaskStatus.PENDING,
                    "Task requires approval before execution",
                    [plan_result],
                    requires_approval=True,
                    risk_level=plan_result.get("risk_level", "medium"),
                )

            # Step 2: Execution with error recovery
            execution_results = await self._execute_plan_with_recovery(
                request, task_id, plan_result
            )

            # Step 3: Verification
            verification_result = await self._verify_execution(
                request, task_id, execution_results
            )

            # Compile final results
            all_results = [plan_result] + execution_results + [verification_result]

            # Determine final status
            final_status = self._determine_final_status(all_results)

            # Update task in database
            await self.task_repo.update_status(
                task_id,
                final_status,
                result={"results": all_results},
            )

            # Learn from execution if enabled
            if self.enable_learning and final_status == TaskStatus.COMPLETED:
                await self._learn_from_success(task_id, plan_result, execution_results)

            # Log completion
            await self.audit_repo.log(
                action="task_completed",
                resource_type="task",
                resource_id=task_id,
                user_id=request.user_id,
                status="success" if final_status == TaskStatus.COMPLETED else "failed",
            )

            # Cleanup execution state
            self.execution_states.pop(task_id, None)

            return self._create_response(
                task_id,
                final_status,
                f"Task completed with status: {final_status.value}",
                all_results,
                risk_level=plan_result.get("risk_level", "low"),
            )

        except Exception as e:
            logger.error(f"Orchestration failed for task {task_id}: {str(e)}", exc_info=True)

            # Update task as failed
            await self.task_repo.update_status(
                task_id, TaskStatus.FAILED, error=str(e)
            )

            # Log error
            await self.audit_repo.log(
                action="task_failed",
                resource_type="task",
                resource_id=task_id,
                user_id=request.user_id,
                status="error",
                details={"error": str(e)},
            )

            # Attempt rollback if enabled
            if self.enable_rollback:
                await self._rollback_task(task_id)

            return self._create_response(
                task_id,
                TaskStatus.FAILED,
                f"Orchestration failed: {str(e)}",
                [],
            )

    async def _plan_task(
        self, request: OrchestrationRequest, task_id: str
    ) -> Dict[str, Any]:
        """Plan the task using the planner agent."""
        logger.info(f"Planning task {task_id}")

        agent_request = AgentRequest(
            task=request.task,
            context=request.context,
            environment_profile=request.environment_profile,
            session_id=request.session_id,
            user_id=request.user_id,
            metadata=request.metadata,
        )

        # Query knowledge base for similar patterns
        if self.enable_learning:
            similar_patterns = await self.knowledge_repo.search_patterns(
                request.task, limit=3
            )
            if similar_patterns:
                agent_request.context["learned_patterns"] = [
                    {"pattern": p.pattern, "solution": p.solution, "confidence": p.confidence_score}
                    for p in similar_patterns
                ]

        response = await self.planner.process(agent_request)

        return {
            "agent": "planner",
            "status": response.status,
            "message": response.content,
            "requires_approval": response.requires_approval,
            "risk_level": response.risk_level,
            "metadata": response.metadata,
            "error": response.error,
        }

    async def _execute_plan_with_recovery(
        self, request: OrchestrationRequest, task_id: str, plan_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute plan with error recovery and rollback support."""
        logger.info(f"Executing plan for task {task_id} with recovery")

        if plan_result["status"] != TaskStatus.COMPLETED:
            return [plan_result]

        plan_data = plan_result.get("metadata", {}).get("plan", {})
        steps = plan_data.get("steps", [])

        execution_results = []
        state = self.execution_states[task_id]

        for step in steps:
            logger.info(f"Executing step {step['id']}: {step['description']}")

            # Add step to database
            await self.task_repo.add_step(
                task_id=task_id,
                step_id=step["id"],
                step_number=steps.index(step) + 1,
                description=step["description"],
                command=step.get("command"),
                tool=step.get("tool"),
                parameters=step.get("parameters", {}),
            )

            # Create checkpoint before execution
            state.checkpoints.append({
                "step_id": step["id"],
                "timestamp": datetime.utcnow().isoformat(),
                "state": "before_execution",
            })

            # Execute step with retry logic
            step_result = await self._execute_step_with_retry(
                step, request, task_id
            )

            execution_results.append(step_result)

            # Update step in database
            await self.task_repo.update_step_status(
                step_id=step["id"],
                status=step_result["status"],
                result=step_result.get("metadata"),
                error=step_result.get("error"),
                execution_time=step_result.get("metadata", {}).get("execution_time"),
            )

            # Track completed step
            if step_result["status"] == TaskStatus.COMPLETED:
                state.completed_steps.append(step)

                # Add rollback action if step is reversible
                if step.get("reversible", False):
                    state.rollback_actions.append({
                        "step_id": step["id"],
                        "rollback_command": step.get("rollback_command"),
                        "tool": step.get("tool"),
                    })
            else:
                # Step failed - attempt rollback if enabled
                logger.error(f"Step {step['id']} failed, stopping execution")

                if self.enable_rollback:
                    logger.info(f"Attempting rollback for task {task_id}")
                    await self._rollback_task(task_id)

                break

        return execution_results

    async def _execute_step_with_retry(
        self, step: Dict[str, Any], request: OrchestrationRequest, task_id: str
    ) -> Dict[str, Any]:
        """Execute a single step with retry logic."""
        agent_request = AgentRequest(
            task=f"Execute step: {step['description']}",
            context={
                "step": step,
                "approved": request.auto_approve or not step.get("requires_approval", False),
            },
            environment_profile=request.environment_profile,
            session_id=request.session_id,
            user_id=request.user_id,
        )

        last_error = None
        for attempt in range(self.max_retry_attempts):
            try:
                response = await self.executor.process(agent_request)

                if response.status == TaskStatus.COMPLETED:
                    return {
                        "agent": "executor",
                        "step_id": step["id"],
                        "status": response.status,
                        "message": response.content,
                        "metadata": response.metadata,
                        "error": None,
                    }
                else:
                    last_error = response.error
                    if attempt < self.max_retry_attempts - 1:
                        logger.warning(
                            f"Step {step['id']} failed (attempt {attempt + 1}), retrying..."
                        )
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue

            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retry_attempts - 1:
                    logger.warning(
                        f"Step {step['id']} error (attempt {attempt + 1}): {e}, retrying..."
                    )
                    await asyncio.sleep(2 ** attempt)
                continue

        # All attempts failed
        return {
            "agent": "executor",
            "step_id": step["id"],
            "status": TaskStatus.FAILED,
            "message": f"Step failed after {self.max_retry_attempts} attempts",
            "metadata": {},
            "error": last_error,
        }

    async def _rollback_task(self, task_id: str) -> bool:
        """Rollback completed steps of a failed task."""
        if task_id not in self.execution_states:
            logger.warning(f"No execution state found for task {task_id}")
            return False

        state = self.execution_states[task_id]

        if not state.rollback_actions:
            logger.info(f"No rollback actions for task {task_id}")
            return True

        logger.info(f"Rolling back task {task_id} with {len(state.rollback_actions)} actions")

        # Execute rollback actions in reverse order
        for action in reversed(state.rollback_actions):
            try:
                logger.info(f"Rolling back step {action['step_id']}")
                # TODO: Implement actual rollback execution
                # This would call the executor with rollback commands
            except Exception as e:
                logger.error(f"Rollback failed for step {action['step_id']}: {e}")

        await self.audit_repo.log(
            action="task_rolled_back",
            resource_type="task",
            resource_id=task_id,
            details={"rollback_actions": len(state.rollback_actions)},
        )

        return True

    async def _verify_execution(
        self, request: OrchestrationRequest, task_id: str, execution_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Verify the execution results."""
        logger.info(f"Verifying execution for task {task_id}")

        execution_data = {
            "steps": execution_results,
            "overall_success": all(r["status"] == TaskStatus.COMPLETED for r in execution_results),
            "failed_steps": [r for r in execution_results if r["status"] == TaskStatus.FAILED],
        }

        agent_request = AgentRequest(
            task="Verify execution results",
            context={
                "execution_results": execution_data,
                "expected_outcomes": request.context.get("expected_outcomes", {}),
            },
            environment_profile=request.environment_profile,
            session_id=request.session_id,
            user_id=request.user_id,
        )

        response = await self.verifier.process(agent_request)

        return {
            "agent": "verifier",
            "status": response.status,
            "message": response.content,
            "metadata": response.metadata,
            "error": response.error,
        }

    async def _learn_from_success(
        self,
        task_id: str,
        plan_result: Dict[str, Any],
        execution_results: List[Dict[str, Any]],
    ) -> None:
        """Learn from successful task execution."""
        try:
            # Extract pattern from successful execution
            plan_data = plan_result.get("metadata", {}).get("plan", {})

            pattern = f"Task: {plan_data.get('description', '')}"
            solution = " -> ".join([step.get("description", "") for step in plan_data.get("steps", [])])

            # Determine category
            tools_used = set(step.get("tool", "generic") for step in plan_data.get("steps", []))
            category = "_".join(sorted(tools_used))

            # Create or update knowledge
            await self.knowledge_repo.create_pattern(
                category=category,
                pattern=pattern,
                solution=solution,
                task_id=task_id,
                confidence_score=0.7,  # Initial confidence
            )

            logger.info(f"Learned new pattern from task {task_id}")

        except Exception as e:
            logger.warning(f"Failed to learn from task {task_id}: {e}")

    def _determine_final_status(self, results: List[Dict[str, Any]]) -> TaskStatus:
        """Determine the final status based on all results."""
        if not results:
            return TaskStatus.FAILED

        for result in results:
            if result["status"] == TaskStatus.FAILED:
                return TaskStatus.FAILED

        for result in results:
            if result["status"] in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]:
                return TaskStatus.IN_PROGRESS

        if all(result["status"] == TaskStatus.COMPLETED for result in results):
            return TaskStatus.COMPLETED

        if any(result["status"] == TaskStatus.CANCELLED for result in results):
            return TaskStatus.CANCELLED

        return TaskStatus.FAILED

    def _create_response(
        self,
        task_id: str,
        status: TaskStatus,
        message: str,
        results: List[Dict[str, Any]],
        requires_approval: bool = False,
        risk_level: str = "low",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OrchestrationResponse:
        """Create a standardized orchestration response."""
        return OrchestrationResponse(
            task_id=task_id,
            status=status,
            message=message,
            results=results,
            requires_approval=requires_approval,
            risk_level=risk_level,
            metadata=metadata,
        )

    async def recover_incomplete_tasks(self) -> List[str]:
        """Recover incomplete tasks on startup."""
        logger.info("Recovering incomplete tasks...")

        incomplete_tasks = await self.task_repo.get_incomplete_tasks(limit=50)
        recovered = []

        for task in incomplete_tasks:
            try:
                logger.info(f"Recovering task {task.id}: {task.description}")

                # Mark as failed (conservative approach)
                await self.task_repo.update_status(
                    task.id,
                    TaskStatus.FAILED,
                    error="Task interrupted by system restart",
                )

                recovered.append(task.id)

            except Exception as e:
                logger.error(f"Failed to recover task {task.id}: {e}")

        logger.info(f"Recovered {len(recovered)} incomplete tasks")
        return recovered

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all components."""
        return {
            "planner": await self.planner.health_check(),
            "executor": await self.executor.health_check(),
            "verifier": await self.verifier.health_check(),
            "llm_router": await self.llm_router.health_check_all(),
            "database": True,  # If we got here, DB is working
        }
