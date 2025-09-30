"""Tasks router for task management."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from ..models import TaskRequest, TaskResponse, TaskStatusResponse, TaskApprovalRequest
from ..dependencies import get_orchestrator, get_current_user, get_request_context
from ...orchestrator import Orchestrator, OrchestrationRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=TaskResponse)
async def create_task(
    request: TaskRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    user_id: str = Depends(get_current_user),
    context: Dict[str, Any] = Depends(get_request_context),
):
    """Create and execute a new task."""
    try:
        # Prepare orchestration request
        orchestration_request = OrchestrationRequest(
            task=request.task,
            context=request.context or {},
            environment_profile=request.environment_profile,
            user_id=user_id,
            auto_approve=request.auto_approve,
            metadata={**(request.metadata or {}), **context},
        )

        # Process the request
        response = await orchestrator.process_request(orchestration_request)

        # Create task response
        return TaskResponse(
            task_id=response.task_id,
            status=response.status,
            message=response.message,
            results=response.results,
            requires_approval=response.requires_approval,
            risk_level=response.risk_level,
            metadata=response.metadata,
        )

    except Exception as e:
        logger.error(f"Create task error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task creation failed: {str(e)}",
        )


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str, orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Get task status and results."""
    try:
        # Get task status from orchestrator
        task_status = await orchestrator.get_task_status(task_id)

        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        return TaskStatusResponse(
            task_id=task_id,
            status=task_status["status"],
            current_step=task_status.get("current_step", "unknown"),
            results=task_status.get("results", []),
            error=task_status.get("error"),
            metadata=task_status.get("metadata"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task status error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}",
        )


@router.post("/{task_id}/approve")
async def approve_task(
    task_id: str,
    request: TaskApprovalRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """Approve or reject a pending task."""
    try:
        # Approve/reject the task
        success = await orchestrator.approve_task(task_id, request.approved)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found or not pending approval",
            )

        action = "approved" if request.approved else "rejected"
        return {
            "message": f"Task {task_id} {action}",
            "task_id": task_id,
            "approved": request.approved,
            "reason": request.reason,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Approve task error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve task: {str(e)}",
        )


@router.delete("/{task_id}")
async def cancel_task(
    task_id: str, orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Cancel a running task."""
    try:
        # Get task status
        task_status = await orchestrator.get_task_status(task_id)

        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        # Cancel the task
        task_status["status"] = "cancelled"
        task_status["current_step"] = "cancelled"

        return {"message": f"Task {task_id} cancelled", "task_id": task_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel task error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {str(e)}",
        )


@router.get("/")
async def list_tasks(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    limit: int = 50,
    offset: int = 0,
):
    """List active tasks."""
    try:
        # Get active tasks from orchestrator
        active_tasks = orchestrator.active_tasks

        # Apply pagination
        task_items = list(active_tasks.items())
        total = len(task_items)
        paginated_items = task_items[offset : offset + limit]

        # Format response
        tasks = []
        for task_id, task_data in paginated_items:
            tasks.append(
                {
                    "task_id": task_id,
                    "status": task_data["status"],
                    "current_step": task_data.get("current_step", "unknown"),
                    "created_at": task_data.get("created_at"),
                    "updated_at": task_data.get("updated_at"),
                }
            )

        return {"tasks": tasks, "total": total, "limit": limit, "offset": offset}

    except Exception as e:
        logger.error(f"List tasks error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}",
        )
