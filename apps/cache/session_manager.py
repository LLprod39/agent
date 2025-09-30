"""Session management using Redis."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Any

from .redis_manager import RedisManager

logger = logging.getLogger(__name__)


class SessionManager:
    """Session manager using Redis."""

    def __init__(self, redis_manager: RedisManager, ttl: int = 3600):
        """
        Initialize session manager.

        Args:
            redis_manager: Redis manager instance
            ttl: Session TTL in seconds (default 1 hour)
        """
        self.redis = redis_manager
        self.ttl = ttl
        self.prefix = "session:"

    def _make_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"{self.prefix}{session_id}"

    async def create_session(
        self, user_id: Optional[str] = None, metadata: Optional[dict] = None
    ) -> str:
        """
        Create new session.

        Args:
            user_id: Optional user ID
            metadata: Optional session metadata

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": user_id or "anonymous",
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        key = self._make_key(session_id)
        await self.redis.set_json(key, session_data, expire=self.ttl)

        logger.info(f"Created session: {session_id} for user: {user_id}")
        return session_id

    async def get_session(self, session_id: str) -> Optional[dict]:
        """
        Get session data.

        Args:
            session_id: Session ID

        Returns:
            Session data or None if not found
        """
        key = self._make_key(session_id)
        session_data = await self.redis.get_json(key)

        if session_data:
            # Update last activity
            session_data["last_activity"] = datetime.utcnow().isoformat()
            await self.redis.set_json(key, session_data, expire=self.ttl)

        return session_data

    async def update_session(
        self, session_id: str, updates: dict[str, Any]
    ) -> bool:
        """
        Update session data.

        Args:
            session_id: Session ID
            updates: Updates to apply

        Returns:
            True if successful, False otherwise
        """
        key = self._make_key(session_id)
        session_data = await self.redis.get_json(key)

        if not session_data:
            logger.warning(f"Session not found: {session_id}")
            return False

        # Apply updates
        session_data.update(updates)
        session_data["last_activity"] = datetime.utcnow().isoformat()

        await self.redis.set_json(key, session_data, expire=self.ttl)
        logger.info(f"Updated session: {session_id}")
        return True

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session.

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False otherwise
        """
        key = self._make_key(session_id)
        deleted = await self.redis.delete(key)

        if deleted:
            logger.info(f"Deleted session: {session_id}")
            return True

        logger.warning(f"Session not found for deletion: {session_id}")
        return False

    async def refresh_session(self, session_id: str) -> bool:
        """
        Refresh session TTL.

        Args:
            session_id: Session ID

        Returns:
            True if refreshed, False otherwise
        """
        key = self._make_key(session_id)
        exists = await self.redis.exists(key)

        if not exists:
            logger.warning(f"Session not found for refresh: {session_id}")
            return False

        await self.redis.expire(key, self.ttl)
        logger.debug(f"Refreshed session: {session_id}")
        return True

    async def get_user_sessions(self, user_id: str) -> list[dict]:
        """
        Get all sessions for a user.

        Args:
            user_id: User ID

        Returns:
            List of session data
        """
        # Scan all session keys
        cursor = 0
        sessions = []

        while True:
            cursor, keys = await self.redis.scan(
                cursor, match=f"{self.prefix}*", count=100
            )

            for key in keys:
                session_data = await self.redis.get_json(key)
                if session_data and session_data.get("user_id") == user_id:
                    sessions.append(session_data)

            if cursor == 0:
                break

        return sessions

    async def cleanup_expired_sessions(self) -> int:
        """
        Cleanup expired sessions (Redis handles this automatically with TTL).

        Returns:
            Number of sessions cleaned (always 0 with Redis TTL)
        """
        # Redis automatically removes expired keys
        logger.info("Redis TTL handles session expiration automatically")
        return 0

    async def get_session_count(self) -> int:
        """
        Get total session count.

        Returns:
            Number of active sessions
        """
        cursor = 0
        count = 0

        while True:
            cursor, keys = await self.redis.scan(
                cursor, match=f"{self.prefix}*", count=100
            )
            count += len(keys)

            if cursor == 0:
                break

        return count

    async def set_session_data(
        self, session_id: str, key: str, value: Any
    ) -> bool:
        """
        Set specific session data field.

        Args:
            session_id: Session ID
            key: Data key
            value: Data value

        Returns:
            True if successful
        """
        session_data = await self.get_session(session_id)
        if not session_data:
            return False

        if "data" not in session_data:
            session_data["data"] = {}

        session_data["data"][key] = value
        return await self.update_session(session_id, session_data)

    async def get_session_data(
        self, session_id: str, key: str
    ) -> Optional[Any]:
        """
        Get specific session data field.

        Args:
            session_id: Session ID
            key: Data key

        Returns:
            Data value or None
        """
        session_data = await self.get_session(session_id)
        if not session_data:
            return None

        return session_data.get("data", {}).get(key)
