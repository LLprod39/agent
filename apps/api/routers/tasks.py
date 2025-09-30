"""Tasks router for task management."""

import logging
from typing import Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status

from ..models import TaskRequest, TaskResponse, TaskStatusResponse, TaskApprovalRequest
from ..dependencies import (
    get_orchestrator,
    get_current_user,
    get_request_context,
    get_task_repository,
    get_task_step_repository,
    get_audit_log_repository,
)
from ...orchestrator import Orchestrator, OrchestrationRequest
from ...database.repositories import TaskRepository, TaskStepRepository, AuditLogRepository
from ...database.models import TaskStatus as DBTaskStatus, MessageRole

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=TaskResponse)
async def create_task(
    request: TaskRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    task_repo: TaskRepository = Depends(get_task_repository),
    audit_repo: AuditLogRepository = Depends(get_audit_log_repository),
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
        
        # Save task to database
        db_task = await task_repo.create(
            user_id=user_id,
            title=request.task[:500] if request.task else "Unnamed task",
            description=request.task,
            environment_profile=request.environment_profile,
            metadata={
                "orchestration_response": response.metadata,
                "request_context": context,
                "auto_approve": request.auto_approve,
            },
        )
        
        # Update task with orchestration results
        status_mapping = {
            "completed": DBTaskStatus.COMPLETED,
            "failed": DBTaskStatus.FAILED,
            "pending": DBTaskStatus.PENDING,
            "in_progress": DBTaskStatus.IN_PROGRESS,
            "cancelled": DBTaskStatus.CANCELLED,
        }
        await task_repo.update_status(
            str(db_task.id),
            status_mapping.get(response.status, DBTaskStatus.PENDING),
        )
        
        # Create audit log
        await audit_repo.create(
            action="task_created",
            resource_type="task",
            resource_id=str(db_task.id),
            user_id=user_id,
            task_id=str(db_task.id),
            details={
                "task_description": request.task[:200],
                "environment_profile": request.environment_profile,
                "risk_level": response.risk_level,
                "requires_approval": response.requires_approval,
            },
        )

        # Create task response
        return TaskResponse(
            task_id=str(db_task.id),  # Use DB task ID
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
    task_id: str,
    task_repo: TaskRepository = Depends(get_task_repository),
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """Get task status and results."""
    try:
        # Get task from database
        db_task = await task_repo.get_by_id(task_id)
        
        if not db_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )
        
        # Try to get from orchestrator for real-time updates
        orchestrator_status = await orchestrator.get_task_status(task_id)
        
        # Use orchestrator status if available, otherwise use DB
        if orchestrator_status:
            return TaskStatusResponse(
                task_id=task_id,
                status=orchestrator_status["status"],
                current_step=orchestrator_status.get("current_step", "unknown"),
                results=orchestrator_status.get("results", []),
                error=orchestrator_status.get("error"),
                metadata=orchestrator_status.get("metadata"),
            )
        else:
            # Fall back to database status
            return TaskStatusResponse(
                task_id=task_id,
                status=db_task.status.value,
                current_step="completed" if db_task.status == DBTaskStatus.COMPLETED else "unknown",
                results=[],
                error=db_task.error_message,
                metadata=db_task.metadata or {},
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
    task_repo: TaskRepository = Depends(get_task_repository),
    audit_repo: AuditLogRepository = Depends(get_audit_log_repository),
    orchestrator: Orchestrator = Depends(get_orchestrator),
    user_id: str = Depends(get_current_user),
):
    """Approve or reject a pending task."""
    try:
        # Check if task exists in DB
        db_task = await task_repo.get_by_id(task_id)
        if not db_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )
        
        # Approve/reject the task in orchestrator
        success = await orchestrator.approve_task(task_id, request.approved)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found or not pending approval",
            )
        
        # Update in database
        if request.approved:
            await task_repo.approve(task_id, user_id)
        else:
            await task_repo.update_status(task_id, DBTaskStatus.CANCELLED)
        
        # Create audit log
        action = "task_approved" if request.approved else "task_rejected"
        await audit_repo.create(
            action=action,
            resource_type="task",
            resource_id=task_id,
            user_id=user_id,
            task_id=task_id,
            details={
                "approved": request.approved,
                "reason": request.reason,
                "approver": user_id,
            },
        )

        action_text = "approved" if request.approved else "rejected"
        return {
            "message": f"Task {task_id} {action_text}",
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
    task_id: str,
    task_repo: TaskRepository = Depends(get_task_repository),
    audit_repo: AuditLogRepository = Depends(get_audit_log_repository),
    orchestrator: Orchestrator = Depends(get_orchestrator),
    user_id: str = Depends(get_current_user),
):
    """Cancel a running task."""
    try:
        # Check if task exists in DB
        db_task = await task_repo.get_by_id(task_id)
        if not db_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )
        
        # Get task status from orchestrator
        task_status = await orchestrator.get_task_status(task_id)

        if task_status:
            # Cancel the task in orchestrator
            task_status["status"] = "cancelled"
            task_status["current_step"] = "cancelled"
        
        # Update in database
        await task_repo.update_status(task_id, DBTaskStatus.CANCELLED)
        
        # Create audit log
        await audit_repo.create(
            action="task_cancelled",
            resource_type="task",
            resource_id=task_id,
            user_id=user_id,
            task_id=task_id,
            details={
                "cancelled_by": user_id,
                "previous_status": db_task.status.value,
            },
        )

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
    task_repo: TaskRepository = Depends(get_task_repository),
    user_id: str = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
    status_filter: str = None,
):
    """List tasks for the current user."""
    try:
        # Get tasks from database
        status_enum = None
        if status_filter:
            status_mapping = {
                "pending": DBTaskStatus.PENDING,
                "in_progress": DBTaskStatus.IN_PROGRESS,
                "completed": DBTaskStatus.COMPLETED,
                "failed": DBTaskStatus.FAILED,
                "cancelled": DBTaskStatus.CANCELLED,
            }
            status_enum = status_mapping.get(status_filter.lower())
        
        db_tasks = await task_repo.get_user_tasks(
            user_id=user_id,
            status=status_enum,
            limit=limit,
        )

        # Format response
        tasks = []
        for db_task in db_tasks:
            tasks.append(
                {
                    "task_id": str(db_task.id),
                    "title": db_task.title,
                    "status": db_task.status.value,
                    "risk_level": db_task.risk_level,
                    "requires_approval": db_task.requires_approval,
                    "environment_profile": db_task.environment_profile,
                    "created_at": db_task.created_at.isoformat() if db_task.created_at else None,
                    "updated_at": db_task.updated_at.isoformat() if db_task.updated_at else None,
                    "started_at": db_task.started_at.isoformat() if db_task.started_at else None,
                    "completed_at": db_task.completed_at.isoformat() if db_task.completed_at else None,
                }
            )

        return {
            "tasks": tasks,
            "total": len(tasks),
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"List tasks error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}",
        )
