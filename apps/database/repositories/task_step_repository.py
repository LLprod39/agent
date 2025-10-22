"""Task step repository for task step operations."""

import logging
from typing import List, Optional
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import TaskStep, TaskStatus

logger = logging.getLogger(__name__)


class TaskStepRepository:
    """Repository for Task Step operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_step(
        self,
        task_id: str,
        step_id: str,
        description: str,
        command: Optional[str] = None,
        tool: Optional[str] = None,
        parameters: Optional[dict] = None,
        agent_type: Optional[str] = None,
        risk_level: str = "low",
        requires_approval: bool = False,
    ) -> TaskStep:
        """Create a new task step."""
        step = TaskStep(
            task_id=task_id,
            step_id=step_id,
            description=description,
            command=command,
            tool=tool,
            parameters=parameters,
            agent_type=agent_type,
            risk_level=risk_level,
            requires_approval=requires_approval,
        )

        self.session.add(step)
        await self.session.commit()
        await self.session.refresh(step)

        logger.info(f"Created task step {step_id} for task {task_id}")
        return step

    async def get_by_task_id(self, task_id: str) -> List[TaskStep]:
        """Get all steps for a task."""
        query = select(TaskStep).where(TaskStep.task_id == task_id).order_by(TaskStep.created_at)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, step_id: str) -> Optional[TaskStep]:
        """Get a step by ID."""
        query = select(TaskStep).where(TaskStep.id == step_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        step_id: str,
        status: TaskStatus,
        output: Optional[str] = None,
        error_message: Optional[str] = None,
        execution_time: Optional[float] = None,
    ) -> Optional[TaskStep]:
        """Update step status."""
        from datetime import datetime

        update_data = {
            "status": status,
            "output": output,
            "error_message": error_message,
            "execution_time": execution_time,
            "updated_at": datetime.utcnow(),
        }

        if status == TaskStatus.IN_PROGRESS:
            update_data.setdefault("started_at", datetime.utcnow())
        elif status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ):
            update_data.setdefault("completed_at", datetime.utcnow())

        stmt = update(TaskStep).where(TaskStep.id == step_id).values(**update_data)
        await self.session.execute(stmt)
        await self.session.commit()

        # Return updated step
        return await self.get_by_id(step_id)

    async def start_step(self, step_id: str) -> Optional[TaskStep]:
        """Mark step as started."""
        from datetime import datetime
        
        stmt = (
            update(TaskStep)
            .where(TaskStep.id == step_id)
            .values(
                status=TaskStatus.IN_PROGRESS,
                started_at=datetime.utcnow(),
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

        return await self.get_by_id(step_id)

    async def complete_step(
        self,
        step_id: str,
        output: Optional[str] = None,
        execution_time: Optional[float] = None,
    ) -> Optional[TaskStep]:
        """Mark step as completed."""
        from datetime import datetime
        
        stmt = (
            update(TaskStep)
            .where(TaskStep.id == step_id)
            .values(
                status=TaskStatus.COMPLETED,
                completed_at=datetime.utcnow(),
                output=output,
                execution_time=execution_time,
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

        return await self.get_by_id(step_id)

    async def fail_step(
        self,
        step_id: str,
        error_message: str,
        execution_time: Optional[float] = None,
    ) -> Optional[TaskStep]:
        """Mark step as failed."""
        from datetime import datetime
        
        stmt = (
            update(TaskStep)
            .where(TaskStep.id == step_id)
            .values(
                status=TaskStatus.FAILED,
                completed_at=datetime.utcnow(),
                error_message=error_message,
                execution_time=execution_time,
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

        return await self.get_by_id(step_id)
