"""Audit log repository."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLog

logger = logging.getLogger(__name__)


class AuditRepository:
    """Repository for Audit Log operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        action: str,
        resource_type: str,
        user_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
    ) -> AuditLog:
        """Create an audit log entry."""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
        )

        self.session.add(audit_log)
        await self.session.commit()

        return audit_log

    async def get_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs with filters."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = select(AuditLog).where(AuditLog.created_at >= cutoff)

        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)

        query = query.order_by(desc(AuditLog.created_at)).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())


class AuditLogRepository(AuditRepository):
    """Extended audit log repository with task helpers."""

    async def get_task_logs(
        self, task_id: str, limit: Optional[int] = None
    ) -> List[AuditLog]:
        """Get audit logs associated with a specific task."""
        query = select(AuditLog).where(AuditLog.task_id == task_id).order_by(AuditLog.created_at)
        if limit:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
