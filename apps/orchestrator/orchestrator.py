"""Main orchestrator for coordinating agents."""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .llm_router import LLMRouter
from .agents import PlannerAgent, ExecutorAgent, VerifierAgent, AgentRequest, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationRequest:
    """Request for orchestration."""
    task: str
    context: Dict[str, Any]
    environment_profile: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
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


class Orchestrator:
    """Main orchestrator for coordinating agent workflows."""
    
    def __init__(self, config: Dict[str, Any], llm_router: LLMRouter):
        self.config = config
        self.llm_router = llm_router
        
        # Initialize agents
        self.planner = PlannerAgent(config.get("planner", {}), llm_router)
        self.executor = ExecutorAgent(config.get("executor", {}), llm_router)
        self.verifier = VerifierAgent(config.get("verifier", {}), llm_router)
        
        # Task tracking
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
    
    async def process_request(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """Process a complete orchestration request."""
        task_id = str(uuid.uuid4())
        
        try:
            logger.info(f"Starting orchestration for task {task_id}: {request.task}")
            
            # Initialize task tracking
            self.active_tasks[task_id] = {
                "request": request,
                "status": TaskStatus.IN_PROGRESS,
                "results": [],
                "current_step": "planning"
            }
            
            # Step 1: Planning
            plan_result = await self._plan_task(request, task_id)
            if plan_result["status"] != TaskStatus.COMPLETED:
                return self._create_response(task_id, plan_result["status"], plan_result["message"], [plan_result])
            
            # Check if approval is required
            if plan_result.get("requires_approval", False) and not request.auto_approve:
                self.active_tasks[task_id]["current_step"] = "awaiting_approval"
                return self._create_response(
                    task_id, 
                    TaskStatus.PENDING, 
                    "Task requires approval before execution",
                    [plan_result],
                    requires_approval=True,
                    risk_level=plan_result.get("risk_level", "medium")
                )
            
            # Step 2: Execution
            execution_results = await self._execute_plan(request, task_id, plan_result)
            
            # Step 3: Verification
            verification_result = await self._verify_execution(request, task_id, execution_results)
            
            # Compile final results
            all_results = [plan_result] + execution_results + [verification_result]
            
            # Determine final status
            final_status = self._determine_final_status(all_results)
            
            # Update task tracking
            self.active_tasks[task_id]["status"] = final_status
            self.active_tasks[task_id]["results"] = all_results
            self.active_tasks[task_id]["current_step"] = "completed"
            
            return self._create_response(
                task_id,
                final_status,
                f"Task completed with status: {final_status.value}",
                all_results,
                risk_level=plan_result.get("risk_level", "low")
            )
            
        except Exception as e:
            logger.error(f"Orchestration failed for task {task_id}: {str(e)}")
            self.active_tasks[task_id]["status"] = TaskStatus.FAILED
            self.active_tasks[task_id]["error"] = str(e)
            
            return self._create_response(
                task_id,
                TaskStatus.FAILED,
                f"Orchestration failed: {str(e)}",
                []
            )
    
    async def _plan_task(self, request: OrchestrationRequest, task_id: str) -> Dict[str, Any]:
        """Plan the task using the planner agent."""
        logger.info(f"Planning task {task_id}")
        
        agent_request = AgentRequest(
            task=request.task,
            context=request.context,
            environment_profile=request.environment_profile,
            session_id=request.session_id,
            user_id=request.user_id,
            metadata=request.metadata
        )
        
        response = await self.planner.process(agent_request)
        
        return {
            "agent": "planner",
            "status": response.status,
            "message": response.content,
            "requires_approval": response.requires_approval,
            "risk_level": response.risk_level,
            "metadata": response.metadata,
            "error": response.error
        }
    
    async def _execute_plan(self, request: OrchestrationRequest, task_id: str, plan_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the planned steps."""
        logger.info(f"Executing plan for task {task_id}")
        
        if plan_result["status"] != TaskStatus.COMPLETED:
            return [plan_result]
        
        plan_data = plan_result.get("metadata", {}).get("plan", {})
        steps = plan_data.get("steps", [])
        
        execution_results = []
        
        for step in steps:
            logger.info(f"Executing step {step['id']}: {step['description']}")
            
            agent_request = AgentRequest(
                task=f"Execute step: {step['description']}",
                context={
                    "step": step,
                    "approved": request.auto_approve or not step.get("requires_approval", False)
                },
                environment_profile=request.environment_profile,
                session_id=request.session_id,
                user_id=request.user_id
            )
            
            response = await self.executor.process(agent_request)
            
            execution_results.append({
                "agent": "executor",
                "step_id": step["id"],
                "status": response.status,
                "message": response.content,
                "metadata": response.metadata,
                "error": response.error
            })
            
            # Stop execution if a step fails
            if response.status == TaskStatus.FAILED:
                logger.error(f"Step {step['id']} failed, stopping execution")
                break
        
        return execution_results
    
    async def _verify_execution(self, request: OrchestrationRequest, task_id: str, execution_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify the execution results."""
        logger.info(f"Verifying execution for task {task_id}")
        
        # Prepare execution results for verification
        execution_data = {
            "steps": execution_results,
            "overall_success": all(r["status"] == TaskStatus.COMPLETED for r in execution_results),
            "failed_steps": [r for r in execution_results if r["status"] == TaskStatus.FAILED]
        }
        
        agent_request = AgentRequest(
            task="Verify execution results",
            context={
                "execution_results": execution_data,
                "expected_outcomes": request.context.get("expected_outcomes", {})
            },
            environment_profile=request.environment_profile,
            session_id=request.session_id,
            user_id=request.user_id
        )
        
        response = await self.verifier.process(agent_request)
        
        return {
            "agent": "verifier",
            "status": response.status,
            "message": response.content,
            "metadata": response.metadata,
            "error": response.error
        }
    
    def _determine_final_status(self, results: List[Dict[str, Any]]) -> TaskStatus:
        """Determine the final status based on all results."""
        if not results:
            return TaskStatus.FAILED
        
        # Check if any step failed
        for result in results:
            if result["status"] == TaskStatus.FAILED:
                return TaskStatus.FAILED
        
        # Check if any step is still pending
        for result in results:
            if result["status"] in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]:
                return TaskStatus.IN_PROGRESS
        
        # Check if all steps completed successfully
        if all(result["status"] == TaskStatus.COMPLETED for result in results):
            return TaskStatus.COMPLETED
        
        # Check if any step was cancelled
        if any(result["status"] == TaskStatus.CANCELLED for result in results):
            return TaskStatus.CANCELLED
        
        # Default to failed if we can't determine status
        return TaskStatus.FAILED
    
    def _create_response(
        self,
        task_id: str,
        status: TaskStatus,
        message: str,
        results: List[Dict[str, Any]],
        requires_approval: bool = False,
        risk_level: str = "low",
        metadata: Optional[Dict[str, Any]] = None
    ) -> OrchestrationResponse:
        """Create a standardized orchestration response."""
        return OrchestrationResponse(
            task_id=task_id,
            status=status,
            message=message,
            results=results,
            requires_approval=requires_approval,
            risk_level=risk_level,
            metadata=metadata
        )
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task."""
        return self.active_tasks.get(task_id)
    
    async def approve_task(self, task_id: str, approved: bool = True) -> bool:
        """Approve or reject a pending task."""
        if task_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        if task["status"] != TaskStatus.PENDING:
            return False
        
        if approved:
            # Continue with execution
            task["status"] = TaskStatus.IN_PROGRESS
            task["current_step"] = "execution"
            
            # Re-process the request with auto-approve
            request = task["request"]
            request.auto_approve = True
            
            # Continue execution in background
            asyncio.create_task(self._continue_execution(request, task_id))
        else:
            # Reject the task
            task["status"] = TaskStatus.CANCELLED
            task["current_step"] = "rejected"
        
        return True
    
    async def _continue_execution(self, request: OrchestrationRequest, task_id: str):
        """Continue execution after approval."""
        try:
            # Get the plan from the previous results
            task = self.active_tasks[task_id]
            plan_result = task["results"][0] if task["results"] else None
            
            if not plan_result:
                return
            
            # Execute the plan
            execution_results = await self._execute_plan(request, task_id, plan_result)
            
            # Verify execution
            verification_result = await self._verify_execution(request, task_id, execution_results)
            
            # Update results
            all_results = [plan_result] + execution_results + [verification_result]
            final_status = self._determine_final_status(all_results)
            
            task["status"] = final_status
            task["results"] = all_results
            task["current_step"] = "completed"
            
        except Exception as e:
            logger.error(f"Failed to continue execution for task {task_id}: {str(e)}")
            task["status"] = TaskStatus.FAILED
            task["error"] = str(e)
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all components."""
        return {
            "planner": await self.planner.health_check(),
            "executor": await self.executor.health_check(),
            "verifier": await self.verifier.health_check(),
            "llm_router": await self.llm_router.health_check_all()
        }

