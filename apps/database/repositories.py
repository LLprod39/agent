"""Repository pattern for database operations."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, desc, func
from sqlalchemy.orm import selectinload

from .models import (
    User,
    Session,
    Message,
    Task,
    TaskStep,
    EnvironmentProfile,
    AuditLog,
    LLMUsage,
    SystemMetrics,
    TaskStatus,
    MessageRole,
    AgentType,
)

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class."""

    def __init__(self, session: AsyncSession):
        self.session = session


class UserRepository(BaseRepository):
    """User repository."""

    async def create(self, username: str, email: str, hashed_password: str) -> User:
        """Create a new user."""
        user = User(username=username, email=email, hashed_password=hashed_password)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def update(self, user_id: str, **kwargs) -> Optional[User]:
        """Update user."""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(**kwargs, updated_at=datetime.utcnow())
        )
        await self.session.commit()
        return await self.get_by_id(user_id)

    async def delete(self, user_id: str) -> bool:
        """Delete user."""
        result = await self.session.execute(delete(User).where(User.id == user_id))
        await self.session.commit()
        return result.rowcount > 0


class SessionRepository(BaseRepository):
    """Session repository."""

    async def create(
        self,
        user_id: str,
        name: Optional[str] = None,
        environment_profile: Optional[str] = None,
    ) -> Session:
        """Create a new session."""
        session = Session(
            user_id=user_id, name=name, environment_profile=environment_profile
        )
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def get_by_id(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        result = await self.session.execute(
            select(Session)
            .options(selectinload(Session.user))
            .where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_user_sessions(
        self, user_id: str, active_only: bool = True
    ) -> List[Session]:
        """Get user sessions."""
        query = select(Session).where(Session.user_id == user_id)
        if active_only:
            query = query.where(Session.is_active)
        query = query.order_by(desc(Session.updated_at))

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update(self, session_id: str, **kwargs) -> Optional[Session]:
        """Update session."""
        await self.session.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(**kwargs, updated_at=datetime.utcnow())
        )
        await self.session.commit()
        return await self.get_by_id(session_id)

    async def deactivate(self, session_id: str) -> bool:
        """Deactivate session."""
        return await self.update(session_id, is_active=False) is not None


class MessageRepository(BaseRepository):
    """Message repository."""

    async def create(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Create a new message."""
        message = Message(
            session_id=session_id, role=role, content=content, metadata=metadata
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_session_messages(
        self, session_id: str, limit: int = 100
    ) -> List[Message]:
        """Get session messages."""
        result = await self.session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_recent_messages(
        self, session_id: str, count: int = 10
    ) -> List[Message]:
        """Get recent messages for context."""
        result = await self.session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(desc(Message.created_at))
            .limit(count)
        )
        return list(reversed(result.scalars().all()))


class TaskRepository(BaseRepository):
    """Task repository."""

    async def create(
        self,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        session_id: Optional[str] = None,
        environment_profile: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Create a new task."""
        task = Task(
            user_id=user_id,
            session_id=session_id,
            title=title,
            description=description,
            environment_profile=environment_profile,
            metadata=metadata,
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_by_id(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        result = await self.session.execute(
            select(Task)
            .options(selectinload(Task.user), selectinload(Task.session))
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_user_tasks(
        self, user_id: str, status: Optional[TaskStatus] = None, limit: int = 50
    ) -> List[Task]:
        """Get user tasks."""
        query = select(Task).where(Task.user_id == user_id)
        if status:
            query = query.where(Task.status == status)
        query = query.order_by(desc(Task.created_at)).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_status(
        self, task_id: str, status: TaskStatus, error_message: Optional[str] = None
    ) -> Optional[Task]:
        """Update task status."""
        update_data = {"status": status, "updated_at": datetime.utcnow()}

        if status == TaskStatus.IN_PROGRESS and not error_message:
            update_data["started_at"] = datetime.utcnow()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            update_data["completed_at"] = datetime.utcnow()

        if error_message:
            update_data["error_message"] = error_message

        await self.session.execute(
            update(Task).where(Task.id == task_id).values(**update_data)
        )
        await self.session.commit()
        return await self.get_by_id(task_id)

    async def approve(self, task_id: str, approved_by: str) -> Optional[Task]:
        """Approve task."""
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
        return await self.get_by_id(task_id)


class TaskStepRepository(BaseRepository):
    """Task step repository."""

    async def create(
        self,
        task_id: str,
        step_id: str,
        description: str,
        command: Optional[str] = None,
        tool: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        agent_type: Optional[AgentType] = None,
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
        )
        self.session.add(step)
        await self.session.commit()
        await self.session.refresh(step)
        return step

    async def get_task_steps(self, task_id: str) -> List[TaskStep]:
        """Get task steps."""
        result = await self.session.execute(
            select(TaskStep)
            .where(TaskStep.task_id == task_id)
            .order_by(TaskStep.created_at)
        )
        return result.scalars().all()

    async def update_status(
        self,
        step_id: str,
        status: TaskStatus,
        output: Optional[str] = None,
        error_message: Optional[str] = None,
        execution_time: Optional[float] = None,
    ) -> Optional[TaskStep]:
        """Update step status."""
        update_data = {"status": status, "updated_at": datetime.utcnow()}

        if status == TaskStatus.IN_PROGRESS:
            update_data["started_at"] = datetime.utcnow()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            update_data["completed_at"] = datetime.utcnow()

        if output is not None:
            update_data["output"] = output
        if error_message is not None:
            update_data["error_message"] = error_message
        if execution_time is not None:
            update_data["execution_time"] = execution_time

        await self.session.execute(
            update(TaskStep).where(TaskStep.id == step_id).values(**update_data)
        )
        await self.session.commit()

        result = await self.session.execute(
            select(TaskStep).where(TaskStep.id == step_id)
        )
        return result.scalar_one_or_none()


class EnvironmentProfileRepository(BaseRepository):
    """Environment profile repository."""

    async def create(
        self,
        name: str,
        profile_data: Dict[str, Any],
        description: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> EnvironmentProfile:
        """Create environment profile."""
        profile = EnvironmentProfile(
            name=name,
            description=description,
            profile_data=profile_data,
            created_by=created_by,
        )
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def get_by_name(self, name: str) -> Optional[EnvironmentProfile]:
        """Get profile by name."""
        result = await self.session.execute(
            select(EnvironmentProfile).where(EnvironmentProfile.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all(self, active_only: bool = True) -> List[EnvironmentProfile]:
        """Get all profiles."""
        query = select(EnvironmentProfile)
        if active_only:
            query = query.where(EnvironmentProfile.is_active)
        query = query.order_by(EnvironmentProfile.name)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update(self, name: str, **kwargs) -> Optional[EnvironmentProfile]:
        """Update profile."""
        await self.session.execute(
            update(EnvironmentProfile)
            .where(EnvironmentProfile.name == name)
            .values(**kwargs, updated_at=datetime.utcnow())
        )
        await self.session.commit()
        return await self.get_by_name(name)


class AuditLogRepository(BaseRepository):
    """Audit log repository."""

    async def create(
        self,
        action: str,
        resource_type: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Create audit log entry."""
        log_entry = AuditLog(
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(log_entry)
        await self.session.commit()
        await self.session.refresh(log_entry)
        return log_entry

    async def get_user_logs(self, user_id: str, limit: int = 100) -> List[AuditLog]:
        """Get user audit logs."""
        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_recent_logs(self, limit: int = 100) -> List[AuditLog]:
        """Get recent audit logs."""
        result = await self.session.execute(
            select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
        )
        return result.scalars().all()


class LLMUsageRepository(BaseRepository):
    """LLM usage repository."""

    async def create(
        self,
        provider: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        cost: Optional[float] = None,
        response_time: Optional[float] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_type: Optional[AgentType] = None,
    ) -> LLMUsage:
        """Create LLM usage record."""
        usage = LLMUsage(
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            provider=provider,
            model=model,
            agent_type=agent_type,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            response_time=response_time,
        )
        self.session.add(usage)
        await self.session.commit()
        await self.session.refresh(usage)
        return usage

    async def get_usage_stats(
        self, user_id: Optional[str] = None, days: int = 30
    ) -> Dict[str, Any]:
        """Get usage statistics."""
        query = select(
            LLMUsage.provider,
            func.sum(LLMUsage.prompt_tokens).label("total_prompt_tokens"),
            func.sum(LLMUsage.completion_tokens).label("total_completion_tokens"),
            func.sum(LLMUsage.total_tokens).label("total_tokens"),
            func.sum(LLMUsage.cost).label("total_cost"),
            func.count(LLMUsage.id).label("request_count"),
        ).where(
            LLMUsage.created_at >= datetime.utcnow().replace(day=1)  # This month
        )

        if user_id:
            query = query.where(LLMUsage.user_id == user_id)

        query = query.group_by(LLMUsage.provider)

        result = await self.session.execute(query)
        return {
            "by_provider": [
                {
                    "provider": row.provider,
                    "total_prompt_tokens": row.total_prompt_tokens or 0,
                    "total_completion_tokens": row.total_completion_tokens or 0,
                    "total_tokens": row.total_tokens or 0,
                    "total_cost": row.total_cost or 0.0,
                    "request_count": row.request_count,
                }
                for row in result
            ]
        }


class SystemMetricsRepository(BaseRepository):
    """System metrics repository."""

    async def create(
        self,
        metric_name: str,
        metric_value: float,
        metric_type: str,
        labels: Optional[Dict[str, Any]] = None,
    ) -> SystemMetrics:
        """Create system metric."""
        metric = SystemMetrics(
            metric_name=metric_name,
            metric_value=metric_value,
            metric_type=metric_type,
            labels=labels,
        )
        self.session.add(metric)
        await self.session.commit()
        await self.session.refresh(metric)
        return metric

    async def get_metrics(
        self, metric_name: str, hours: int = 24
    ) -> List[SystemMetrics]:
        """Get metrics for a specific name."""
        from datetime import timedelta

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        result = await self.session.execute(
            select(SystemMetrics)
            .where(
                and_(
                    SystemMetrics.metric_name == metric_name,
                    SystemMetrics.timestamp >= cutoff_time,
                )
            )
            .order_by(SystemMetrics.timestamp)
        )
        return result.scalars().all()
