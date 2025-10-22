"""Session repository for conversation management."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Session, Message

logger = logging.getLogger(__name__)


class SessionRepository:
    """Repository for Session and Message operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(
        self,
        session_id: str,
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """Create a new conversation session."""
        session_obj = Session(
            id=session_id,
            user_id=user_id,
            context=context or {},
            last_activity_at=datetime.utcnow(),
        )

        self.session.add(session_obj)
        await self.session.commit()
        await self.session.refresh(session_obj)

        logger.info(f"Created session {session_id} for user {user_id}")
        return session_obj

    async def get_session(self, session_id: str, include_messages: bool = True) -> Optional[Session]:
        """Get session by ID with optional messages."""
        query = select(Session).where(Session.id == session_id)

        if include_messages:
            query = query.options(selectinload(Session.messages))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_activity(self, session_id: str) -> None:
        """Update last activity timestamp."""
        stmt = (
            update(Session)
            .where(Session.id == session_id)
            .values(last_activity_at=datetime.utcnow())
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_context(self, session_id: str, context: Dict[str, Any]) -> None:
        """Update session context."""
        stmt = update(Session).where(Session.id == session_id).values(context=context)
        await self.session.execute(stmt)
        await self.session.commit()

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Add a message to a session."""
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )

        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)

        # Update session activity
        await self.update_activity(session_id)

        return message

    async def get_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Message]:
        """Get messages for a session."""
        query = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at)
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_recent_sessions(
        self,
        user_id: Optional[int] = None,
        hours: int = 24,
        limit: int = 10,
    ) -> List[Session]:
        """Get recent active sessions."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = select(Session).where(Session.last_activity_at >= cutoff)

        if user_id:
            query = query.where(Session.user_id == user_id)

        query = query.order_by(Session.last_activity_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """Delete sessions older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = delete(Session).where(Session.last_activity_at < cutoff)

        result = await self.session.execute(stmt)
        await self.session.commit()

        deleted = result.rowcount
        logger.info(f"Deleted {deleted} old sessions (older than {days} days)")
        return deleted
