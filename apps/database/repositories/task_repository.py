"""Task repository for database operations compatible with the current schema."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import and_, delete, desc, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import AgentType, Task, TaskStatus as DBTaskStatus, TaskStep
from ...orchestrator.agents.base import TaskStatus

logger = logging.getLogger(__name__)

StatusInput = Union[TaskStatus, DBTaskStatus, str]


class TaskRepository:
    """Repository for Task database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: Optional[str],
        description: Optional[str] = None,
        environment_profile: Optional[str] = None,
        risk_level: str = "low",
        requires_approval: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        title: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Task:
        """Create a new task."""
        if not user_id:
            raise ValueError("user_id is required to create a task")

        resolved_title = (title or description or "Untitled task")[:500]

        task = Task(
            id=task_id,
            user_id=user_id,
            session_id=session_id,
            title=resolved_title,
            description=description,
            status=DBTaskStatus.PENDING,
            environment_profile=environment_profile,
            risk_level=risk_level,
            requires_approval=requires_approval,
            extra_metadata=metadata or {},
        )

        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)

        logger.info("Created task %s for user %s", task.id, user_id)
        return task

    async def get_by_id(
        self,
        task_id: str,
        include_steps: bool = True,
    ) -> Optional[Task]:
        """Get task by ID with optional steps."""
        query = select(Task).where(Task.id == task_id)
        if include_steps:
            query = query.options(selectinload(Task.steps))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_tasks(
        self,
        user_id: str,
        status: Optional[StatusInput] = None,
        limit: int = 50,
        offset: int = 0,
        include_steps: bool = False,
    ) -> List[Task]:
        """Get tasks for a specific user with optional status filtering."""
        query = select(Task).where(Task.user_id == user_id)

        normalized_status = self._normalize_status(status)
        if normalized_status is not None:
            query = query.where(Task.status == normalized_status)

        if include_steps:
            query = query.options(selectinload(Task.steps))

        query = query.order_by(desc(Task.created_at)).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_user(
        self,
        user_id: str,
        status: Optional[StatusInput] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """Backward-compatible wrapper for get_user_tasks."""
        return await self.get_user_tasks(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset,
            include_steps=False,
        )

    async def update_status(
        self,
        task_id: str,
        status: StatusInput,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Task]:
        """Update task status and optionally attach metadata or error information."""
        normalized_status = self._normalize_status(status)
        if normalized_status is None:
            raise ValueError(f"Invalid task status: {status}")

        update_data: Dict[str, Any] = {
            "status": normalized_status,
            "updated_at": datetime.utcnow(),
        }

        if normalized_status == DBTaskStatus.IN_PROGRESS and not await self._has_started(task_id):
            update_data["started_at"] = datetime.utcnow()

        if normalized_status in {
            DBTaskStatus.COMPLETED,
            DBTaskStatus.FAILED,
            DBTaskStatus.CANCELLED,
        }:
            update_data["completed_at"] = datetime.utcnow()

        if error is not None:
            update_data["error_message"] = error

        if result is not None or metadata is not None:
            merged_metadata = await self._get_task_metadata(task_id)
            if metadata:
                merged_metadata.update(metadata)
            if result is not None:
                merged_metadata["result"] = result
            update_data["extra_metadata"] = merged_metadata

        await self.session.execute(
            update(Task).where(Task.id == task_id).values(**update_data)
        )
        await self.session.commit()

        logger.info("Updated task %s status to %s", task_id, normalized_status.value)
        return await self.get_by_id(task_id, include_steps=False)

    async def approve(
        self,
        task_id: str,
        approved_by: str,
    ) -> Optional[Task]:
        """Approve a task."""
        await self.session.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(
                requires_approval=False,
                approved_by=approved_by,
                approved_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        await self.session.commit()

        logger.info("Task %s approved by user %s", task_id, approved_by)
        return await self.get_by_id(task_id, include_steps=False)

    async def add_step(
        self,
        task_id: str,
        step_id: str,
        step_number: int,
        description: str,
        command: Optional[str] = None,
        tool: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        agent_type: Optional[str] = None,
        risk_level: str = "low",
        requires_approval: bool = False,
    ) -> TaskStep:
        """Add a step to a task."""
        step = TaskStep(
            task_id=task_id,
            step_id=step_id,
            description=description,
            command=command,
            tool=tool,
            parameters=parameters or {},
            status=DBTaskStatus.PENDING,
            agent_type=self._normalize_agent_type(agent_type),
            risk_level=risk_level,
            requires_approval=requires_approval,
            extra_metadata={"step_number": step_number},
        )

        self.session.add(step)
        await self.session.commit()
        await self.session.refresh(step)

        logger.debug("Added step %s to task %s", step_id, task_id)
        return step

    async def update_step_status(
        self,
        step_id: str,
        status: StatusInput,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        execution_time: Optional[float] = None,
    ) -> Optional[TaskStep]:
        """Update a task step status."""
        normalized_status = self._normalize_status(status)
        if normalized_status is None:
            raise ValueError(f"Invalid step status: {status}")

        update_data: Dict[str, Any] = {
            "status": normalized_status,
            "updated_at": datetime.utcnow(),
        }

        if normalized_status == DBTaskStatus.IN_PROGRESS:
            update_data["started_at"] = datetime.utcnow()

        if normalized_status in {
            DBTaskStatus.COMPLETED,
            DBTaskStatus.FAILED,
            DBTaskStatus.CANCELLED,
        }:
            update_data["completed_at"] = datetime.utcnow()

        if result is not None:
            merged_metadata = await self._get_step_metadata(step_id)
            merged_metadata["result"] = result
            update_data["extra_metadata"] = merged_metadata

        if error is not None:
            update_data["error_message"] = error

        if execution_time is not None:
            update_data["execution_time"] = execution_time

        await self.session.execute(
            update(TaskStep).where(TaskStep.id == step_id).values(**update_data)
        )
        await self.session.commit()

        logger.debug("Updated step %s status to %s", step_id, normalized_status.value)

        result_row = await self.session.execute(select(TaskStep).where(TaskStep.id == step_id))
        return result_row.scalar_one_or_none()

    async def get_pending_tasks(self, limit: int = 100) -> List[Task]:
        """Get all pending tasks that require approval or are waiting."""
        query = (
            select(Task)
            .where(
                or_(
                    and_(
                        Task.status == DBTaskStatus.PENDING,
                        Task.requires_approval.is_(True),
                    ),
                    Task.status == DBTaskStatus.IN_PROGRESS,
                )
            )
            .order_by(Task.created_at)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_incomplete_tasks(self, limit: int = 50) -> List[Task]:
        """Get tasks that are not completed (for recovery on restart)."""
        query = (
            select(Task)
            .where(
                Task.status.in_(
                    [
                        DBTaskStatus.PENDING,
                        DBTaskStatus.IN_PROGRESS,
                    ]
                )
            )
            .options(selectinload(Task.steps))
            .order_by(Task.created_at)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search_tasks(
        self,
        query_text: Optional[str] = None,
        status: Optional[StatusInput] = None,
        user_id: Optional[str] = None,
        environment: Optional[str] = None,
        limit: int = 50,
    ) -> List[Task]:
        """Search tasks with filters."""
        query = select(Task)
        conditions = []

        if query_text:
            conditions.append(
                or_(
                    Task.description.ilike(f"%{query_text}%"),
                    Task.error_message.ilike(f"%{query_text}%"),
                )
            )

        normalized_status = self._normalize_status(status)
        if normalized_status is not None:
            conditions.append(Task.status == normalized_status)

        if user_id:
            conditions.append(Task.user_id == user_id)

        if environment:
            conditions.append(Task.environment_profile == environment)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(Task.created_at)).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete(self, task_id: str) -> bool:
        """Delete a task."""
        result = await self.session.execute(delete(Task).where(Task.id == task_id))
        await self.session.commit()

        deleted = result.rowcount > 0
        if deleted:
            logger.info("Deleted task %s", task_id)

        return deleted

    async def get_task_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get task statistics."""
        query = select(Task)
        if user_id:
            query = query.where(Task.user_id == user_id)

        result = await self.session.execute(query)
        all_tasks = result.scalars().all()

        stats: Dict[str, Dict[str, int]] = {
            "total": len(all_tasks),
            "by_status": {},
            "by_risk_level": {},
        }  # type: ignore[assignment]

        for task in all_tasks:
            status_value = task.status.value if isinstance(task.status, DBTaskStatus) else str(task.status)
            stats["by_status"][status_value] = stats["by_status"].get(status_value, 0) + 1  # type: ignore[index]
            stats["by_risk_level"][task.risk_level] = stats["by_risk_level"].get(task.risk_level, 0) + 1  # type: ignore[index]

        return stats  # type: ignore[return-value]

    async def _has_started(self, task_id: str) -> bool:
        """Check if task has started_at timestamp."""
        result = await self.session.execute(
            select(Task.started_at).where(Task.id == task_id)
        )
        return result.scalar_one_or_none() is not None

    async def _get_task_metadata(self, task_id: str) -> Dict[str, Any]:
        """Fetch current extra metadata for a task."""
        result = await self.session.execute(
            select(Task.extra_metadata).where(Task.id == task_id)
        )
        return result.scalar_one_or_none() or {}

    async def _get_step_metadata(self, step_id: str) -> Dict[str, Any]:
        """Fetch current extra metadata for a task step."""
        result = await self.session.execute(
            select(TaskStep.extra_metadata).where(TaskStep.id == step_id)
        )
        return result.scalar_one_or_none() or {}

    def _normalize_status(self, status: Optional[StatusInput]) -> Optional[DBTaskStatus]:
        """Normalize mixed status inputs to the database enum."""
        if status is None:
            return None

        if isinstance(status, DBTaskStatus):
            return status

        if isinstance(status, TaskStatus):
            return DBTaskStatus(status.value)

        try:
            return DBTaskStatus(str(status))
        except ValueError:
            logger.warning("Unknown task status value: %s", status)
            return None

    def _normalize_agent_type(self, agent_type: Optional[str]) -> Optional[AgentType]:
        """Convert agent type strings to the enum the model expects."""
        if agent_type is None:
            return None
        try:
            return AgentType(agent_type)
        except ValueError:
            logger.debug("Unknown agent type '%s' for task step", agent_type)
            return None
